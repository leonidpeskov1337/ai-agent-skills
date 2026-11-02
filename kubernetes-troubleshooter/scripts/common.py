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


PLACEMENT_LABELS = ("node.kubernetes.io/instance-type", "topology.kubernetes.io/zone",
                    "karpenter.sh/nodepool", "karpenter.sh/capacity-type",
                    "eks.amazonaws.com/nodegroup")


def project_karpenter(item):
    meta = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})
    safe = {"kind": item.get("kind"), "name": meta.get("name"), "uid": meta.get("uid"),
            "created": meta.get("creationTimestamp"),
            "deletion": meta.get("deletionTimestamp"),
            "labels": {k: v for k, v in (meta.get("labels") or {}).items()
                       if k in PLACEMENT_LABELS}}
    if item.get("kind") == "NodePool":
        template = spec.get("template", {}).get("spec", {})
        safe.update({"disruption": spec.get("disruption"), "limits": spec.get("limits"),
                     "weight": spec.get("weight"),
                     "requirements": template.get("requirements"),
                     "expireAfter": template.get("expireAfter"),
                     "taints": template.get("taints")})
        safe["status"] = {k: status[k] for k in ("resources", "conditions") if k in status}
    else:
        safe.update({"requirements": spec.get("requirements"),
                     "resources": spec.get("resources")})
        safe["status"] = {k: status[k] for k in (
            "nodeName", "providerID", "capacity", "allocatable", "conditions") if k in status}
    return redact_values(safe)


def project_probe(probe):
    """Keep timing and target shape, never exec commands or HTTP header values."""
    safe = {key: probe[key] for key in (
        "initialDelaySeconds", "periodSeconds", "timeoutSeconds", "successThreshold",
        "failureThreshold", "terminationGracePeriodSeconds") if key in probe}
    http = probe.get("httpGet")
    if isinstance(http, dict):
        safe["httpGet"] = {key: http[key] for key in ("port", "scheme") if key in http}
        if isinstance(http.get("path"), str):
            safe["httpGet"]["path"] = http["path"].split("?", 1)[0].split("#", 1)[0]
        if http.get("httpHeaders"):
            safe["httpGet"]["header_names"] = [header.get("name") for header in http["httpHeaders"]]
    for kind, keys in (("tcpSocket", ("port",)), ("grpc", ("port", "service"))):
        if isinstance(probe.get(kind), dict):
            safe[kind] = {key: probe[kind][key] for key in keys if key in probe[kind]}
    if "exec" in probe:
        safe["exec"] = {"configured": True}
    return safe


def projection(item):
    """Whitelist fields; omit arbitrary annotations, env, Secret refs and config bodies."""
    if item.get("kind") in ("Application", "ApplicationSet"):
        return redact_values(project_argo(item) | tracking_metadata(item.get("metadata") or {}))
    if item.get("kind") in ("NodeClaim", "NodePool"):
        return project_karpenter(item)
    meta = item.get("metadata", {})
    spec = item.get("spec", {})
    workload = spec.get("jobTemplate", {}).get("spec", spec)
    template = workload.get("template", {}).get("spec", workload)
    containers = [{k: c[k] for k in ("name", "image", "resources", "ports") if k in c} |
                  {key: project_probe(c[key]) for key in ("readinessProbe", "livenessProbe", "startupProbe")
                   if isinstance(c.get(key), dict)}
                  for c in template.get("containers", [])]
    safe = {"kind": item.get("kind"), "name": meta.get("name"),
            "namespace": meta.get("namespace"), "uid": meta.get("uid"),
            "created": meta.get("creationTimestamp"), "owners": meta.get("ownerReferences", []),
            "containers": containers}
    safe.update(tracking_metadata(meta))
    safe["initContainers"] = [
        {k: c[k] for k in ("name", "image", "resources", "restartPolicy") if k in c}
        for c in template.get("initContainers", [])]
    for key in ("overhead", "affinity", "topologySpreadConstraints", "nodeSelector",
                "tolerations", "priorityClassName", "terminationGracePeriodSeconds"):
        if key in template:
            safe[key] = template[key]
    labels = meta.get("labels") or {}
    if item.get("kind") == "Node":
        safe["placement"] = {k: labels[k] for k in PLACEMENT_LABELS if k in labels}
    safe["deletion"] = meta.get("deletionTimestamp")
    for key in ("nodeName", "replicas", "selector", "type", "clusterIP", "ports",
                "providerID", "taints", "unschedulable", "storageClassName", "volumeName",
                "accessModes", "resources", "scaleTargetRef", "minReplicas", "maxReplicas",
                "metrics", "behavior", "minAvailable", "maxUnavailable",
                "unhealthyPodEvictionPolicy", "strategy"):
        if key in spec:
            safe[key] = spec[key]
    status = item.get("status", {})
    safe["status"] = {k: status[k] for k in (
        "phase", "conditions", "containerStatuses", "initContainerStatuses",
        "allocatable", "capacity", "nodeInfo", "readyReplicas", "availableReplicas",
        "currentReplicas", "desiredReplicas", "currentMetrics", "lastScaleTime",
        "updatedReplicas", "unavailableReplicas", "startTime", "qosClass",
        "disruptionsAllowed", "currentHealthy", "desiredHealthy", "expectedPods",
        "reason", "message") if k in status}
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
             "applications.argoproj.io", "applicationsets.argoproj.io",
             "poddisruptionbudgets", "nodeclaims.karpenter.sh", "nodepools.karpenter.sh"}


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
