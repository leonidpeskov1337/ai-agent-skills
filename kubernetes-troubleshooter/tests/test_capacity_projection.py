"""Projection coverage for scaling, disruption and node-provisioning evidence."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import RESOURCES, projection

class CapacityProjectionTests(unittest.TestCase):
    def test_new_resources_allowed(self):
        for name in ("poddisruptionbudgets", "nodeclaims.karpenter.sh", "nodepools.karpenter.sh"):
            self.assertIn(name, RESOURCES)

    def test_probes_and_placement_kept_env_dropped(self):
        probe = {"httpGet": {"path": "/-/readiness", "port": 8080}, "periodSeconds": 10}
        item = {"kind": "Deployment", "metadata": {"name": "web"}, "spec": {"template": {"spec": {
            "containers": [{"name": "web", "readinessProbe": probe,
                            "env": [{"name": "TOKEN", "value": "x"}]}],
            "topologySpreadConstraints": [{"maxSkew": 1}], "nodeSelector": {"pool": "web"}}}}}
        result = projection(item)
        self.assertEqual(result["containers"][0]["readinessProbe"], probe)
        self.assertNotIn("env", result["containers"][0])
        self.assertEqual(result["nodeSelector"], {"pool": "web"})
        self.assertEqual(result["topologySpreadConstraints"], [{"maxSkew": 1}])

    def test_hpa_behavior_and_metrics(self):
        behavior = {"scaleDown": {"stabilizationWindowSeconds": 900}}
        result = projection({"kind": "HorizontalPodAutoscaler", "metadata": {"name": "web"},
                             "spec": {"behavior": behavior, "metrics": [{"type": "Resource"}],
                                      "maxReplicas": 8},
                             "status": {"desiredReplicas": 8, "currentReplicas": 8,
                                        "lastScaleTime": "2024-01-01T00:00:00Z"}})
        self.assertEqual(result["behavior"], behavior)
        self.assertEqual(result["status"]["desiredReplicas"], 8)
        self.assertIn("lastScaleTime", result["status"])

    def test_pdb(self):
        result = projection({"kind": "PodDisruptionBudget", "metadata": {"name": "web"},
                             "spec": {"maxUnavailable": 1},
                             "status": {"disruptionsAllowed": 0, "currentHealthy": 2}})
        self.assertEqual(result["maxUnavailable"], 1)
        self.assertEqual(result["status"]["disruptionsAllowed"], 0)

    def test_node_placement_labels_only(self):
        result = projection({"kind": "Node", "metadata": {"name": "n1", "labels": {
            "node.kubernetes.io/instance-type": "m7i.2xlarge", "secret-ish": "x"}}})
        self.assertEqual(result["placement"], {"node.kubernetes.io/instance-type": "m7i.2xlarge"})

    def test_karpenter_nodepool_and_nodeclaim(self):
        pool = projection({"kind": "NodePool", "metadata": {"name": "web"}, "spec": {
            "disruption": {"consolidationPolicy": "WhenEmpty", "consolidateAfter": "30m"},
            "limits": {"cpu": "200"},
            "template": {"spec": {"requirements": [{"key": "karpenter.k8s.aws/instance-cpu"}]}}}})
        self.assertEqual(pool["disruption"]["consolidationPolicy"], "WhenEmpty")
        self.assertEqual(pool["limits"], {"cpu": "200"})
        claim = projection({"kind": "NodeClaim", "metadata": {
            "name": "web-abc", "labels": {"karpenter.sh/nodepool": "web"},
            "deletionTimestamp": "2024-01-01T00:00:00Z"},
            "status": {"nodeName": "ip-1", "conditions": [{"type": "Launched",
                                                          "reason": "VcpuLimitExceeded"}]}})
        self.assertEqual(claim["labels"], {"karpenter.sh/nodepool": "web"})
        self.assertEqual(claim["status"]["conditions"][0]["reason"], "VcpuLimitExceeded")
        self.assertIsNotNone(claim["deletion"])

    def test_probe_credentials_and_exec_commands_never_emitted(self):
        item = {"kind": "Pod", "spec": {"containers": [{"name": "app",
            "readinessProbe": {"httpGet": {"path": "/ready?key=private-value",
                "port": 8080, "httpHeaders": [{"name": "Authorization", "value": "private-value"}]},
                "periodSeconds": 7},
            "livenessProbe": {"exec": {"command": ["sh", "-c", "check private-value"]},
                              "timeoutSeconds": 3}}]}}
        result = projection(item)
        import json
        self.assertNotIn("private-value", json.dumps(result))
        readiness = result["containers"][0]["readinessProbe"]
        self.assertEqual(readiness["httpGet"]["path"], "/ready")
        self.assertEqual(readiness["httpGet"]["header_names"], ["Authorization"])
        self.assertEqual(readiness["periodSeconds"], 7)
        self.assertEqual(result["containers"][0]["livenessProbe"]["exec"], {"configured": True})

    def test_capacity_collection_remains_read_only_and_scoped(self):
        from unittest.mock import patch
        from common import get_resources
        import json
        with patch("common.kubectl", return_value={"ok": True, "output": json.dumps({
                "kind": "NodeClaim", "metadata": {"name": "claim"},
                "status": {"conditions": [{"type": "Launched", "status": "False"}]}})}) as mocked:
            result = get_resources("prod-eu", "workloads", "nodeclaims.karpenter.sh", name="claim")
        self.assertEqual(mocked.call_args.args[:2], ("prod-eu", "workloads"))
        self.assertEqual(mocked.call_args.args[2][:3], ["get", "nodeclaims.karpenter.sh", "claim"])
        self.assertEqual(result["items"][0]["status"]["conditions"][0]["status"], "False")

if __name__ == "__main__":
    unittest.main()
