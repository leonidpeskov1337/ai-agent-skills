"""Argo evidence preservation and sensitive-field exclusion with offline fixtures."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import get_resources, projection
from argocd_projection import safe_url


class ArgoEvidenceTests(unittest.TestCase):
    def test_multi_source_revision_order_without_inline_values(self):
        raw = {"kind": "Application", "metadata": {"name": "api", "namespace": "gitops",
            "ownerReferences": [{"kind": "ApplicationSet", "name": "services"}]}, "spec": {
            "sources": [{"repoURL": "https://user:private@example.com/charts?token=private",
                         "chart": "api", "targetRevision": "1.2.3", "helm": {"values": "private"}},
                        {"repoURL": "ssh://git@example.com/values", "ref": "values", "targetRevision": "main",
                         "plugin": {"env": [{"name": "TOKEN", "value": "private"}]}}],
            "destination": {"server": "https://user:private@cluster:6443?token=private", "namespace": "payments"},
            "syncPolicy": {"automated": {"prune": True, "selfHeal": True}}}, "status": {
            "sync": {"status": "Synced", "revisions": ["1.2.3", "abc123"], "comparedTo": {"secret": "private"}},
            "health": {"status": "Healthy"}, "reconciledAt": "2026-10-31T09:00:00Z",
            "history": [{"revision": "abc123", "deployedAt": "2026-10-31T09:00:00Z", "source": {"helm": {"values": "private"}}}]}}
        result = projection(raw)
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(result["spec"]["sources"][0]["repoURL"], "https://example.com/charts")
        self.assertEqual(result["spec"]["sources"][1]["ref"], "values")
        self.assertEqual(result["status"]["sync"]["revisions"], ["1.2.3", "abc123"])
        self.assertEqual(result["spec"]["destination"]["server"], "https://cluster:6443")
        self.assertTrue(result["spec"]["automated"]["selfHeal"])
        self.assertEqual(result["owners"][0]["kind"], "ApplicationSet")

    def test_operation_results_without_manifests_or_applied_source(self):
        raw = {"kind": "Application", "status": {"operationState": {"phase": "Failed",
            "message": "token=private", "operation": {"sync": {"manifests": ["private"]}},
            "syncResult": {"revision": "sha1", "source": {"helm": {"values": "private"}},
                           "resources": [{"kind": "Job", "name": "migrate", "hookPhase": "Failed",
                                          "message": "quota exceeded", "manifest": "private"}]}}}}
        result = projection(raw)
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(result["status"]["operationState"]["phase"], "Failed")
        self.assertEqual(result["status"]["operationState"]["syncResult"]["resources"][0]["hookPhase"], "Failed")

    def test_applicationset_generator_secrets_omitted(self):
        raw = {"kind": "ApplicationSet", "spec": {"generators": [
            {"scmProvider": {"tokenRef": {"secretName": "private"}, "values": {"password": "private"}}}],
            "template": {"spec": {"source": {"repoURL": "https://example.com/config", "path": "apps/api",
                                                "helm": {"valuesObject": {"password": "private"}}}}}},
               "status": {"conditions": [{"type": "ErrorOccurred", "message": "render failed"}]}}
        result = projection(raw)
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(result["generator_types"], [["scmProvider"]])
        self.assertEqual(result["template"]["source"]["path"], "apps/api")
        self.assertEqual(result["status"]["conditions"][0]["type"], "ErrorOccurred")

    def test_tracking_preserved_but_other_annotations_not_emitted(self):
        raw = {"kind": "Deployment", "metadata": {"annotations": {
            "argocd.argoproj.io/tracking-id": "api:apps/Deployment:payments/api",
            "argocd.argoproj.io/installation-id": "remote-eu", "private": "private"},
            "labels": {"app.kubernetes.io/instance": "api", "password": "private"}}}
        for kind in ("Deployment", "Application"):
            with self.subTest(kind=kind):
                raw["kind"] = kind
                result = projection(raw)
                self.assertEqual(result["argocd_tracking"]["argocd.argoproj.io/installation-id"], "remote-eu")
                self.assertEqual(result["instance_label_hint"], "api")
                self.assertNotIn("private", json.dumps(result))
                # Preserve app-of-apps tracking too, without inferring management.
                self.assertNotIn("managed_by_argocd", result)

    @patch("common.kubectl")
    def test_application_read_pins_control_plane_and_namespace(self, mocked):
        mocked.return_value = {"ok": True, "output": json.dumps({"kind": "Application", "metadata": {"name": "api"}})}
        result = get_resources("management-eu", "team-gitops", "applications.argoproj.io", name="api")
        context, namespace, command = mocked.call_args.args
        self.assertEqual((context, namespace), ("management-eu", "team-gitops"))
        self.assertEqual(command[:3], ["get", "applications.argoproj.io", "api"])
        self.assertNotIn("--refresh", command)
        self.assertTrue(result["ok"])

    @patch("common.kubectl", return_value={"ok": False, "error": "forbidden"})
    def test_denied_applications_are_not_proof_argocd_is_off(self, mocked):
        result = get_resources("management", "gitops", "applications.argoproj.io")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "forbidden")
        self.assertNotIn("items", result)

    def test_url_credentials_and_query_removed(self):
        self.assertEqual(safe_url("https://user:private@[::1]:443/repo?token=private#private"), "https://[::1]:443/repo")
        self.assertEqual(safe_url("git@example.com:team/repo.git"), "git@example.com:team/repo.git")
        self.assertEqual(safe_url("https://example.com:invalid/repo"), "[INVALID_URL]")

    def test_nullable_optional_fields_preserve_usable_application_evidence(self):
        result = projection({"kind": "Application", "spec": {"source": None,
            "sources": [{"repoURL": "https://example.com/repo", "targetRevision": "main"}],
            "syncPolicy": None}, "status": {"sync": None, "health": None,
            "operationState": None, "resources": None, "history": None}})
        self.assertEqual(result["spec"]["sources"][0]["targetRevision"], "main")
        self.assertEqual(result["status"]["resources"], [])


if __name__ == "__main__":
    unittest.main()
