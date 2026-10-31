"""Bounded read-only transport primitives. No third-party runtime dependencies."""
import datetime as dt
import json
import re
import subprocess
import os
import signal
import threading
import time
from argocd_projection import project_argo

MAX_BYTES = 2_000_000


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def redact(text):
    text = re.sub(r'(?i)(bearer\s+)[\w.~/+\-=]+', r'\1[REDACTED]', text)
    return re.sub(r'(?i)((?:password|token|secret|api[_-]?key)\s*[=:]\s*)[^\s,;]+',
                  r'\1[REDACTED]', text)


def emit(value):
    print(json.dumps(value, indent=2, ensure_ascii=True))


def run(argv, timeout=20, max_bytes=MAX_BYTES):
    """Read bounded pipes in memory; stop the child at timeout/byte budget."""
    started = time.monotonic()
    try:
        child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 shell=False, start_new_session=os.name != "nt")
    except OSError:
        return {"ok": False, "error": "executable_unavailable", "collected_at": now()}
    buffers = [bytearray(), bytearray()]
    lock = threading.Lock()
    exceeded = threading.Event()

    def read_stream(stream, index):
        try:
            while chunk := stream.read1(4096):
                with lock:
                    room = max_bytes - sum(map(len, buffers))
                    buffers[index].extend(chunk[:room])
                    if len(chunk) > room:
                        exceeded.set()
                        return
        finally:
            stream.close()

    readers = [threading.Thread(target=read_stream, args=(stream, index), daemon=True)
               for index, stream in enumerate((child.stdout, child.stderr))]
    for reader in readers:
        reader.start()
    failure = None
    while child.poll() is None or any(reader.is_alive() for reader in readers):
        if exceeded.is_set():
            failure = "output_limit"
        elif time.monotonic() - started > timeout:
            failure = "timeout"
        if failure:
            if os.name == "nt" and child.poll() is None:
                # Best effort for attached credential helpers; detached plugins need host supervision.
                try:
                    subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            elif os.name != "nt":
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if child.poll() is None:
                child.kill()
            break
        time.sleep(0.01)
    child.wait(timeout=2)
    for reader in readers:
        reader.join(timeout=.1)
    if exceeded.is_set():
        failure = "output_limit"
    if failure:
        return {"ok": False, "error": failure, "collected_at": now()}
    output, error = (bytes(value).decode("utf-8", errors="replace") for value in buffers)
    return {"ok": child.returncode == 0, "collected_at": now(),
            "output": output if child.returncode == 0 else "",
            "error": ("forbidden" if "forbidden" in error.lower() else
                      "command_failed") if child.returncode else None}


def redact_values(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_values(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_values(item) for key, item in value.items()}
    return value


def kubectl(context, namespace, args):
    if not context or context.startswith("-") or (namespace and namespace.startswith("-")):
        raise ValueError("explicit context and valid namespace required")
    command = ["kubectl", "--context", context, "--request-timeout=15s"]
    if namespace:
        command += ["--namespace", namespace]
    return run(command + args)


def tracking_metadata(meta):
    annotations = meta.get("annotations") or {}
    safe = {"argocd_tracking": {key: annotations[key] for key in (
        "argocd.argoproj.io/tracking-id", "argocd.argoproj.io/installation-id",
        "argocd.argoproj.io/hook", "argocd.argoproj.io/sync-wave") if key in annotations}}
    labels = meta.get("labels") or {}
    if "app.kubernetes.io/instance" in labels:
        safe["instance_label_hint"] = labels["app.kubernetes.io/instance"]
    return safe


def projection(item):
    """Whitelist fields; omit arbitrary annotations, env, Secret refs and config bodies."""
    if item.get("kind") in ("Application", "ApplicationSet"):
        return redact_values(project_argo(item) | tracking_metadata(item.get("metadata") or {}))
    meta = item.get("metadata", {})
    spec = item.get("spec", {})
    workload = spec.get("jobTemplate", {}).get("spec", spec)
    template = workload.get("template", {}).get("spec", workload)
    containers = [{k: c[k] for k in ("name", "image", "resources", "ports") if k in c}
                  for c in template.get("containers", [])]
    safe = {"kind": item.get("kind"), "name": meta.get("name"),
            "namespace": meta.get("namespace"), "uid": meta.get("uid"),
            "created": meta.get("creationTimestamp"), "owners": meta.get("ownerReferences", []),
            "containers": containers}
    safe.update(tracking_metadata(meta))
    safe["initContainers"] = [
        {k: c[k] for k in ("name", "image", "resources", "restartPolicy") if k in c}
        for c in template.get("initContainers", [])]
    if "overhead" in template:
        safe["overhead"] = template["overhead"]
    for key in ("nodeName", "replicas", "selector", "type", "clusterIP", "ports",
                "providerID", "taints", "storageClassName", "volumeName",
                "accessModes", "resources", "scaleTargetRef", "minReplicas", "maxReplicas"):
        if key in spec:
            safe[key] = spec[key]
    status = item.get("status", {})
    safe["status"] = {k: status[k] for k in (
        "phase", "conditions", "containerStatuses", "initContainerStatuses",
        "allocatable", "capacity", "nodeInfo", "readyReplicas", "availableReplicas",
        "currentReplicas", "desiredReplicas", "currentMetrics") if k in status}
    if item.get("kind") == "Event":
        for key in ("reason", "message", "type", "firstTimestamp", "lastTimestamp",
                    "eventTime", "count", "involvedObject"):
            if key in item:
                safe[key] = item[key]
    if item.get("kind") == "EndpointSlice":
        safe.update({k: item[k] for k in ("addressType", "endpoints", "ports") if k in item})
    return redact_values(safe)


RESOURCES = {"pods", "deployments", "statefulsets", "daemonsets", "replicasets",
             "jobs", "cronjobs", "services", "endpointslices", "events", "nodes",
             "persistentvolumeclaims", "storageclasses", "csidrivers",
             "horizontalpodautoscalers", "ingresses", "networkpolicies",
             "gateways.gateway.networking.k8s.io", "httproutes.gateway.networking.k8s.io",
             "servicemonitors.monitoring.coreos.com", "podmonitors.monitoring.coreos.com",
             "applications.argoproj.io", "applicationsets.argoproj.io"}


def get_resources(context, namespace, resource, selector=None, name=None, field_selector=None):
    if resource not in RESOURCES:
        raise ValueError("resource not allowed")
    if name and (name.startswith("-") or "/" in name):
        raise ValueError("invalid resource name")
    args = ["get", resource] + ([name] if name else []) + ["-o", "json", "--chunk-size=100"]
    if selector:
        args += ["--selector", selector]
    if field_selector:
        args += ["--field-selector", field_selector]
    response = kubectl(context, namespace, args)
    if response["ok"]:
        try:
            raw = json.loads(response.pop("output"))
            response["items"] = [projection(i) for i in raw.get("items", [raw])]
        except (ValueError, TypeError):
            response = {"ok": False, "error": "invalid_json", "collected_at": now()}
    response["source"] = {"context": context, "namespace": namespace, "resource": resource,
                          "name": name, "selector": selector, "field_selector": field_selector}
    return response
