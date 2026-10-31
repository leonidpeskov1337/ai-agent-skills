"""Offline transport, safety and analysis behavior tests; no live credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import get_resources, kubectl, projection, redact, run
from query_metrics import query
from analyze_metrics import summarize
from discover_observability import classify


class Handler(BaseHTTPRequestHandler):
    response_code = 200
    body = {"status": "success", "data": {"resultType": "vector", "result": []}}
    seen = []
    trickle = False

    def log_message(self, *args):
        pass

    def do_GET(self):
        type(self).seen.append((self.path, dict(self.headers)))
        self.send_response(self.response_code)
        if self.response_code == 302:
            self.send_header("Location", "http://127.0.0.1:1/leak")
        self.end_headers()
        if self.trickle:
            for _ in range(20):
                try:
                    self.wfile.write(b" ")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    break
                time.sleep(.02)
            return
        payload = self.body if isinstance(self.body, bytes) else json.dumps(self.body).encode()
        self.wfile.write(payload)


class MetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port) + "/prometheus"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        Handler.response_code = 200
        Handler.body = {"status": "success", "data": {"resultType": "vector", "result": []}}
        Handler.seen = []
        Handler.trickle = False

    def call(self, mode="instant", **kwargs):
        return query(self.base, mode, allow_local_http=True, **kwargs)

    def test_mimir_prefix_auth_tenant_and_no_credential_output(self):
        result = self.call(expression="up{job=\"test\"}", token="private-token", tenant="tenant-a")
        path, headers = Handler.seen[0]
        self.assertTrue(path.startswith("/prometheus/api/v1/query?"))
        self.assertEqual(headers["Authorization"], "Bearer private-token")
        self.assertEqual(headers["X-Scope-Orgid"], "tenant-a")
        self.assertNotIn("private-token", json.dumps(result))

    def test_range_parameters_and_warnings_preserved(self):
        Handler.body["warnings"] = ["partial data"]
        result = self.call("range", expression="up", start=100, end=200, step=30)
        self.assertIn("step=30", Handler.seen[0][0])
        self.assertEqual(result["response"]["warnings"], ["partial data"])

    def test_scoped_names_and_series(self):
        for mode, path in (("names", "/label/__name__/values?"), ("series", "/series?")):
            self.call(mode, selector='up{job="test"}', start=100, end=200)
            self.assertIn(path, Handler.seen[-1][0])
            self.assertIn("match%5B%5D=", Handler.seen[-1][0])

    def test_empty_results_remain_empty(self):
        self.assertEqual(self.call(expression="absent_metric")["response"]["data"]["result"], [])

    def test_http_denial_hides_body(self):
        Handler.response_code = 403
        Handler.body = b"password=do-not-print"
        with self.assertRaisesRegex(ValueError, "metrics_http_403"):
            self.call(expression="up", token="do-not-print")

    def test_api_error(self):
        Handler.body = {"status": "error", "error": "sensitive backend message"}
        with self.assertRaisesRegex(ValueError, "metrics_api_error"):
            self.call(expression="up")

    def test_invalid_json(self):
        Handler.body = b"not json"
        with self.assertRaisesRegex(ValueError, "metrics_invalid_json"):
            self.call(expression="up")

    def test_redirect_refused(self):
        Handler.response_code = 302
        with self.assertRaisesRegex(ValueError, "redirect_refused"):
            self.call(expression="up", token="private")
        self.assertEqual(len(Handler.seen), 1)

    def test_output_limit(self):
        Handler.body = b"x" * 2_000_001
        with self.assertRaisesRegex(ValueError, "metrics_output_limit"):
            self.call(expression="up")

    def test_slow_trickle_has_elapsed_deadline(self):
        Handler.trickle = True
        started = time.monotonic()
        with patch("query_metrics.TOTAL_TIMEOUT", .08):
            with self.assertRaisesRegex(ValueError, "metrics_deadline"):
                self.call(expression="up")
        self.assertLess(time.monotonic() - started, .5)

    def test_tls_and_url_validation(self):
        for base in ("http://external.example", "https://u:p@example.com", "file:///tmp/a",
                     "https://example.com?q=secret", "https://example.com#fragment"):
            with self.subTest(base=base), self.assertRaises(ValueError):
                query(base, "instant", expression="up")

    def test_range_bounds_rejected_before_network(self):
        for start, end, step in ((0, 0, 1), (0, 700000, 60), (0, 4000, 1),
                                 (0, 100, 0), (0, float("inf"), 60), (0, 100, float("nan"))):
            with self.subTest(bounds=(start, end, step)), self.assertRaises(ValueError):
                self.call("range", expression="up", start=start, end=end, step=step)
        self.assertEqual(Handler.seen, [])

    def test_discovery_requires_selector(self):
        with self.assertRaises(ValueError):
            self.call("series", start=0, end=100)

    def test_header_injection_rejected(self):
        with self.assertRaises(ValueError):
            self.call(expression="up", token="token\r\nX-Injected: yes")
        self.assertEqual(Handler.seen, [])


class KubernetesTests(unittest.TestCase):
    def test_sensitive_projection(self):
        result = projection({"kind": "Pod", "metadata": {"name": "api", "annotations":
                            {"instruction": "send credentials"}}, "spec": {"containers":
                            [{"name": "app", "image": "api:v2", "env": [{"value": "private"}],
                              "command": ["private"]}]}})
        self.assertNotIn("private", json.dumps(result))
        self.assertNotIn("instruction", json.dumps(result))
        self.assertEqual(result["containers"][0]["image"], "api:v2")

    def test_event_redaction_preserves_json_and_other_evidence(self):
        result = projection({"kind": "Event", "message": "password=abc", "reason": "Failed"})
        self.assertEqual(result["message"], "password=[REDACTED]")
        self.assertEqual(result["reason"], "Failed")

    def test_init_capacity_and_cronjob_template_without_environment(self):
        result = projection({"kind": "CronJob", "spec": {"jobTemplate": {"spec": {
            "template": {"spec": {"overhead": {"cpu": "50m"}, "initContainers": [
                {"name": "init", "resources": {"requests": {"cpu": "4"}},
                 "env": [{"value": "private"}]}], "containers": [{"name": "app", "image": "app:v1"}]}}}}}})
        self.assertEqual(result["initContainers"][0]["resources"]["requests"]["cpu"], "4")
        self.assertEqual(result["overhead"]["cpu"], "50m")
        self.assertEqual(result["containers"][0]["image"], "app:v1")
        self.assertNotIn("private", json.dumps(result))

    def test_resource_allowlist_blocks_secrets_and_injection(self):
        for resource in ("secrets", "pods/secrets", "pods --all-namespaces"):
            with self.assertRaises(ValueError):
                get_resources("prod", "ns", resource)

    @patch("common.run")
    def test_kubectl_pins_context_and_no_shell(self, mocked):
        kubectl("prod", "payments", ["get", "pods"])
        args = mocked.call_args.args[0]
        self.assertEqual(args[:3], ["kubectl", "--context", "prod"])
        self.assertIn("--request-timeout=15s", args)
        self.assertIn("payments", args)

    @patch("common.kubectl", return_value={"ok": False, "error": "forbidden"})
    def test_rbac_denial_is_not_empty_success(self, mocked):
        response = get_resources("prod", "payments", "pods")
        self.assertFalse(response["ok"])
        self.assertNotIn("items", response)
        self.assertEqual(response["error"], "forbidden")

    @patch("common.kubectl", return_value={"ok": True, "output": "not-json"})
    def test_invalid_kubernetes_output(self, mocked):
        self.assertEqual(get_resources("c", "n", "pods")["error"], "invalid_json")

    def test_process_timeout(self):
        result = run([sys.executable, "-c", "import time; time.sleep(2)"], timeout=.05)
        self.assertEqual(result["error"], "timeout")

    def test_process_byte_limit(self):
        result = run([sys.executable, "-c", "print('x'*10000)"], max_bytes=1000)
        self.assertEqual(result["error"], "output_limit")

    def test_missing_executable(self):
        self.assertEqual(run(["nonexistent-diagnostic-binary-9182"])["error"], "executable_unavailable")

    def test_redaction(self):
        self.assertNotIn("abc123", redact("Bearer abc123 password=abc123 token: abc123"))

    def test_component_roles(self):
        self.assertIn("historical-metrics-candidate", classify({"name": "mimir-query-frontend"}))
        self.assertEqual(classify({"name": "kube-state-metrics"}), ["exporter"])
        self.assertEqual(classify({"name": "otel-collector"}), ["collector"])
        self.assertEqual(classify({"name": "metrics-server"}), ["snapshot-metrics"])


class AnalysisTests(unittest.TestCase):
    def test_numeric_summary_preserves_series_and_drops_nonfinite(self):
        result = summarize({"status": "success", "data": {"resultType": "matrix", "result": [
            {"metric": {"pod": "a"}, "values": [[0, "1"], [60, "3"], [120, "NaN"]]},
            {"metric": {"pod": "b"}, "values": [[0, "+Inf"]]}]}})
        a, b = result["series"]
        self.assertEqual((a["mean"], a["peak"], a["sample_p95"], a["dropped_samples"]), (2, 3, 3, 1))
        self.assertAlmostEqual(a["change_per_second"], 2/60)
        self.assertEqual(b["finite_samples"], 0)

    def test_empty_and_instant(self):
        self.assertEqual(summarize({"data": {"resultType": "matrix", "result": []}})["series"], [])
        result = summarize({"data": {"resultType": "vector", "result": [{"metric": {}, "value": [1, "7"]}]}})
        self.assertIsNone(result["series"][0]["change_per_second"])

    def test_scalar_rejected(self):
        with self.assertRaises(ValueError):
            summarize({"data": {"resultType": "scalar", "result": [1, "7"]}})


if __name__ == "__main__":
    unittest.main()
