import contextlib
import io
import copy
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


import lint_policy  # noqa: E402


GOOD = json.loads((ROOT / "tests" / "fixtures" / "good_policy.json").read_text())




def lint(doc, require_tags=True, max_per_type=5):
   return lint_policy.Linter(require_tags, max_per_type).lint(doc)




def errors(findings):
   return [f for f in findings if f["severity"] == "error"]




def messages(findings, severity=None):
   return " | ".join(f["message"] for f in findings if severity in (None, f["severity"]))




class LintPolicyTest(unittest.TestCase):
   def setUp(self):
       self.doc = copy.deepcopy(GOOD)
       self.sep = self.doc["scan_execution_policy"][0]
       self.action = self.sep["actions"][0]
       self.gate = self.doc["approval_policy"][0]


   def test_good_policy_has_no_errors_or_warnings(self):
       findings = lint(self.doc)
       self.assertEqual([f for f in findings if f["severity"] != "info"], [], findings)


   def test_unknown_top_level_key_rejects_document(self):
       self.doc["scan_policy"] = []
       self.assertIn("unknown top-level key", messages(errors(lint(self.doc))))


   def test_legacy_scan_result_policy_key(self):
       self.doc["scan_result_policy"] = self.doc.pop("approval_policy")
       self.assertIn("use approval_policy", messages(errors(lint(self.doc))))


   def test_per_type_limit(self):
       self.doc["scan_execution_policy"] = [copy.deepcopy(self.sep) for _ in range(6)]
       for i, p in enumerate(self.doc["scan_execution_policy"]):
           p["name"] = f"p{i}"
       self.assertIn("exceed the limit of 5", messages(errors(lint(self.doc))))
       self.assertEqual(errors(lint(self.doc, max_per_type=10)), [])


   def test_action_max_properties(self):
       self.action["scanner_profile"] = "x"
       self.assertIn("maxProperties 5", messages(errors(lint(self.doc))))


   def test_uncapped_scan_type_not_flagged(self):
       self.action["scan"] = "container_scanning"
       self.action["scanner_profile"] = "x"
       self.assertNotIn("maxProperties", messages(lint(self.doc)))


   def test_empty_including_is_error(self):
       self.sep["policy_scope"] = {"projects": {"including": []}}
       self.assertIn("treated as no filter", messages(errors(lint(self.doc))))


   def test_string_id_in_scope(self):
       self.sep["policy_scope"] = {"projects": {"excluding": [{"id": "42"}]}}
       self.assertIn("must be an integer", messages(errors(lint(self.doc))))


   def test_missing_tags_only_when_required(self):
       del self.action["tags"]
       self.assertIn("no tags", messages(errors(lint(self.doc))))
       self.assertEqual(errors(lint(self.doc, require_tags=False)), [])


   def test_variable_must_be_string(self):
       self.action["variables"]["AST_ENABLE_MR_PIPELINES"] = True
       self.assertIn("must be strings", messages(errors(lint(self.doc))))


   def test_before_script_and_mr_variable_warnings(self):
       del self.action["scan_settings"]
       del self.action["variables"]
       warnings = messages(lint(self.doc), "warning")
       self.assertIn("ignore_default_before_after_script", warnings)
       self.assertIn("AST_ENABLE_MR_PIPELINES", warnings)


   def test_missing_mr_rule(self):
       self.sep["rules"] = [self.sep["rules"][1]]
       self.assertIn("merge_request_event", messages(lint(self.doc), "warning"))


   def test_invalid_branch_type(self):
       self.sep["rules"][0]["branch_type"] = "feature"
       self.assertIn("invalid branch_type", messages(errors(lint(self.doc))))


   def test_pipeline_sources_list_is_error(self):
       self.sep["rules"][0]["pipeline_sources"] = ["merge_request_event"]
       self.assertIn("pipeline_sources must be a mapping", messages(errors(lint(self.doc))))


   def test_target_default_warns(self):
       self.sep["rules"][0]["branch_type"] = "target_default"
       self.assertIn("target_default", messages(lint(self.doc), "warning"))


   def test_newly_detected_is_error(self):
       self.gate["rules"][0]["vulnerability_states"] = ["newly_detected"]
       self.assertIn("newly_detected", messages(errors(lint(self.doc))))


   def test_no_pipeline_allowed_warns(self):
       self.sep["no_pipeline"] = {"allowed": True}
       self.assertIn("no_pipeline", messages(lint(self.doc), "warning"))


   def test_dast_requires_site_profile(self):
       self.action.clear()
       self.action.update({"scan": "dast", "tags": ["t"], "scanner_profile": "p"})
       self.assertIn("site_profile", messages(errors(lint(self.doc))))


   def test_gate_fail_open_and_developer_approvers(self):
       self.gate["fallback_behavior"] = {"fail": "open"}
       self.gate["actions"][0] = {"type": "require_approval", "approvals_required": 1, "role_approvers": ["developer"]}
       warnings = messages(lint(self.doc), "warning")
       self.assertIn("fail is not 'closed'", warnings)
       self.assertIn("any developer can approve", warnings)


   def test_gate_without_approvers(self):
       self.gate["actions"][0] = {"type": "require_approval", "approvals_required": 1}
       self.assertIn("without approvers", messages(errors(lint(self.doc))))


   def test_gate_branch_type(self):
       self.gate["rules"][0]["branch_type"] = "all"
       self.assertIn("default|protected", messages(errors(lint(self.doc))))


   def test_gate_weak_approval_settings(self):
       self.gate["approval_settings"]["prevent_approval_by_author"] = False
       self.assertIn("prevent_approval_by_author", messages(lint(self.doc), "warning"))


   def test_vmp_without_scope(self):
       self.doc["vulnerability_management_policy"] = [
           {"name": "dismiss", "enabled": True, "rules": [{"type": "detected"}], "actions": [{"type": "auto_dismiss"}]}
       ]
       self.assertIn("every linked project", messages(lint(self.doc), "warning"))


   def test_pep_required_fields_and_override(self):
       self.doc["pipeline_execution_policy"] = [{"name": "pep", "enabled": True, "variables_override": {}}]
       findings = lint(self.doc)
       self.assertIn("'content'", messages(errors(findings)))
       self.assertIn("'pipeline_config_strategy'", messages(errors(findings)))
       self.assertIn("requires 'allowed'", messages(errors(findings)))


   def test_cli_exit_code(self):
       path = ROOT / "tests" / "fixtures" / "good_policy.json"
       with contextlib.redirect_stdout(io.StringIO()):
           self.assertEqual(lint_policy.main([str(path), "--require-tags"]), 0)




if __name__ == "__main__":
   unittest.main()
