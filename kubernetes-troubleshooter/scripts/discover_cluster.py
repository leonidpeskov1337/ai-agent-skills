"""Verify explicit context identity and scoped access without reading kubeconfig secrets."""
import argparse
from common import emit, kubectl


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--context", required=True)
    p.add_argument("--namespace", required=True)
    a = p.parse_args()
    identity = kubectl(a.context, None, ["config", "view", "--minify", "-o",
        'jsonpath={.current-context}{"\\n"}{.clusters[0].name}{"\\n"}{.clusters[0].cluster.server}'])
    if not identity["ok"]:
        emit({"identity": identity, "limitation": "Stop: cluster identity unavailable"})
        return
    version = kubectl(a.context, None, ["version", "-o", "json"])
    permissions = {r: kubectl(a.context, a.namespace, ["auth", "can-i", "list", r])
                   for r in ("pods", "events", "services", "deployments")}
    permissions["pods/log"] = kubectl(a.context, a.namespace,
                                      ["auth", "can-i", "get", "pods/log"])
    emit({"context": a.context, "namespace": a.namespace, "identity": identity,
          "version": version, "permissions": permissions,
          "next": "Inspect identity and denied capabilities before scoped collection"})


if __name__ == "__main__":
    main()
