"""Find candidates in a known namespace; never connect to discovered endpoints."""
import argparse
import re
from common import emit, get_resources

PATTERNS = {
    "historical-metrics-candidate": r"prometheus|mimir|thanos|victoria|vmselect|vmsingle",
    "logs-candidate": r"loki",
    "traces-candidate": r"tempo|jaeger",
    "collector": r"otel|opentelemetry|alloy|grafana-agent",
    "snapshot-metrics": r"metrics-server",
    "exporter": r"kube-state-metrics|node-exporter|cadvisor|cilium|calico",
}


def classify(item):
    text = str(item.get("name", "")) + " " + " ".join(
        c.get("image", "") for c in item.get("containers", []))
    return [role for role, pattern in PATTERNS.items() if re.search(pattern, text, re.I)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--context", required=True)
    p.add_argument("--namespace", required=True, help="Known workload or monitoring namespace")
    p.add_argument("--selector")
    p.add_argument("--monitors", action="store_true", help="Also inspect monitor CRs if permitted")
    a = p.parse_args()
    resources = ["services", "deployments", "statefulsets", "daemonsets"]
    if a.monitors:
        resources += ["servicemonitors.monitoring.coreos.com", "podmonitors.monitoring.coreos.com"]
    results = []
    for resource in resources:
        response = get_resources(a.context, a.namespace, resource, a.selector)
        for item in response.get("items", []):
            item["candidate_roles"] = classify(item)
        results.append(response)
    emit({"discovery": results, "warning": "Names/images are hints, not validated query endpoints. "
          "Use approved routing configuration; exporters and collectors are not historical APIs."})


if __name__ == "__main__":
    main()
