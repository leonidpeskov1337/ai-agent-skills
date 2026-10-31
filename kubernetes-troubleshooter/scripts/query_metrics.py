"""Bounded Prometheus-compatible read API client (Prometheus, Mimir, Thanos, VM)."""
import argparse
import json
import math
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from common import MAX_BYTES, emit, now

TOTAL_TIMEOUT = 20


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_refused")


def query(base, mode, expression=None, start=None, end=None, step=60, at=None,
          token=None, tenant=None, ca=None, cert=None, key=None,
          allow_local_http=False, selector=None):
    url = urllib.parse.urlsplit(base)
    if (url.username or url.password or url.query or url.fragment or not url.hostname
            or url.scheme not in ("https", "http")):
        raise ValueError("invalid endpoint: use an approved API base without credentials/query")
    if url.scheme != "https" and not (allow_local_http and url.hostname in
                                                     ("localhost", "127.0.0.1", "::1")):
        raise ValueError("TLS required (HTTP only for explicitly allowed loopback)")
    if mode not in ("instant", "range", "series", "names"):
        raise ValueError("unsupported read mode")
    params = {"timeout": "15s"}
    endpoint = {"instant": "query", "range": "query_range", "series": "series",
                "names": "label/__name__/values"}[mode]
    if mode in ("instant", "range"):
        if not expression or len(expression) > 16000:
            raise ValueError("bounded --query required")
        params["query"] = expression
    if mode == "instant" and at is not None:
        if not math.isfinite(at):
            raise ValueError("finite evaluation timestamp required")
        params["time"] = at
    if mode in ("range", "series", "names"):
        if start is None or end is None or not all(map(math.isfinite, (start, end, step))):
            raise ValueError("finite start/end/step required")
        if not (0 < end - start <= 7 * 86400 and step > 0):
            raise ValueError("window must be positive and at most 7 days")
        if mode == "range" and (end - start) / step + 1 > 2000:
            raise ValueError("at most 2000 evaluation points per series")
        params.update(start=start, end=end)
        if mode == "range":
            params["step"] = step
    if mode in ("series", "names"):
        if not selector or len(selector) > 2000:
            raise ValueError("scoped --selector required for discovery")
        params["match[]"] = selector
    # Older compatible APIs may ignore limit; byte budget still applies.
    params["limit"] = 200
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if tenant:
        headers["X-Scope-OrgID"] = tenant
    if any("\n" in v or "\r" in v for v in headers.values()):
        raise ValueError("invalid authentication configuration")
    tls = ssl.create_default_context(cafile=ca)
    if cert:
        tls.load_cert_chain(cert, key)
    handlers = [NoRedirect(), urllib.request.HTTPSHandler(context=tls)]
    if allow_local_http and url.hostname in ("localhost", "127.0.0.1", "::1"):
        # A configured system proxy must not receive local fixture/forwarded auth.
        handlers.append(urllib.request.ProxyHandler({}))
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(base.rstrip("/") + "/api/v1/" + endpoint + "?" +
                                     urllib.parse.urlencode(params), headers=headers)
    deadline = time.monotonic() + TOTAL_TIMEOUT
    try:
        with opener.open(request, timeout=TOTAL_TIMEOUT) as response:
            chunks = []
            size = 0
            while True:
                if time.monotonic() >= deadline:
                    raise ValueError("metrics_deadline")
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if time.monotonic() >= deadline:
                    raise ValueError("metrics_deadline")
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("metrics_output_limit")
            payload = b"".join(chunks)
    except urllib.error.HTTPError as exc:
        # Never return response bodies or URLs that might include credentials/data.
        code = exc.code
        exc.close()
        raise ValueError("metrics_http_" + str(code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ValueError("metrics_transport_failed") from None
    if len(payload) > MAX_BYTES:
        raise ValueError("metrics_output_limit")
    try:
        envelope = json.loads(payload)
    except (ValueError, UnicodeError):
        raise ValueError("metrics_invalid_json") from None
    if not isinstance(envelope, dict) or envelope.get("status") != "success":
        raise ValueError("metrics_api_error")
    return {"collected_at": now(), "source": {"endpoint": base, "mode": mode,
            "query": expression, "selector": selector, "start": start, "end": end,
            "step": step if mode == "range" else None, "time": at},
            "response": envelope,
            "limitations": "Review warnings/infos and coverage; results may be limited to 200 series. "
            "Labels can contain sensitive data. Empty results do not prove health."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", required=True, help="Approved API base, e.g. https://mimir/prometheus")
    p.add_argument("--mode", choices=("instant", "range", "series", "names"), default="instant")
    p.add_argument("--query")
    p.add_argument("--selector")
    p.add_argument("--start", type=float, help="UTC Unix seconds")
    p.add_argument("--end", type=float)
    p.add_argument("--step", type=float, default=60)
    p.add_argument("--at", type=float)
    p.add_argument("--token-env", help="Name of existing approved bearer-token environment variable")
    p.add_argument("--tenant-env", help="Name of existing approved Mimir tenant environment variable")
    p.add_argument("--ca", help="Approved CA bundle")
    p.add_argument("--cert", help="Approved mTLS client certificate")
    p.add_argument("--key", help="mTLS private key file; never printed")
    p.add_argument("--allow-local-http", action="store_true")
    a = p.parse_args()
    if any(name and not os.environ.get(name) for name in (a.token_env, a.tenant_env)):
        p.error("configured auth environment variable is missing or empty")
    try:
        result = query(a.base_url, a.mode, a.query, a.start, a.end, a.step, a.at,
                       os.environ.get(a.token_env) if a.token_env else None,
                       os.environ.get(a.tenant_env) if a.tenant_env else None,
                       a.ca, a.cert, a.key, a.allow_local_http, a.selector)
        emit(result)
    except (ValueError, OSError):
        # Keep CLI failures free of endpoints, header values and private key paths.
        emit({"ok": False, "error": "metrics_request_failed",
              "hint": "Check approved endpoint/auth, TLS, bounds and backend status; no automatic retry"})
        raise SystemExit(1)


if __name__ == "__main__":
    main()
