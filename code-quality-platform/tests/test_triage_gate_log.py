import pathlib
import sys
import unittest


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))


from triage_gate_log import classify  # noqa: E402




class TriageGateLogTest(unittest.TestCase):
   def signatures(self, text):
       return {item["signature"] for item in classify(text)["findings"]}


   def test_below_threshold(self):
       text = "Quality Gate FAILED (block mode)\n - minimum_new_code_coverage: 0.0 is below 80.0\n"
       result = classify(text)
       self.assertEqual(result["verdict"], {"status": "FAILED", "mode": "block"})
       self.assertEqual(result["findings"][0]["signature"], "threshold_below")
       self.assertEqual(result["findings"][0]["metric"], "minimum_new_code_coverage")


   def test_exceeds_threshold(self):
       self.assertEqual(self.signatures(" - max_new_major: 14 exceeds 0"), {"threshold_exceeded"})


   def test_unavailable_and_no_merge_base(self):
       text = (
           "changed_lines_status=unavailable:no_merge_base\n"
           "- maximum_new_code_duplication_percent: metric is unavailable\n"
       )
       self.assertEqual(self.signatures(text), {"metric_unavailable", "no_merge_base"})


   def test_skipped_passes(self):
       text = "Quality Gate PASSED (block mode)\n - SKIPPED minimum_new_code_coverage: not_applicable\n"
       result = classify(text)
       self.assertEqual(result["verdict"]["status"], "PASSED")
       self.assertEqual(self.signatures(text), {"skipped_not_applicable"})


   def test_config_invalid(self):
       text = "Quality Gate configuration or analyzer health is invalid; fix the reported problem"
       self.assertEqual(self.signatures(text), {"config_or_health_invalid"})


   def test_baseline_missing_and_configuration_error(self):
       text = (
           " - SKIPPED max_new_major: baseline_missing\n"
           " - CONFIGURATION ERROR analyzer health: detekt no_health_evidence\n"
           "Quality Gate configuration or analyzer health is invalid; fix the reported problem\n"
       )
       result = classify(text)
       self.assertEqual(
           self.signatures(text),
           {"skipped_baseline_missing", "configuration_error", "config_or_health_invalid"},
       )
       detail = next(item for item in result["findings"] if item["signature"] == "configuration_error")
       self.assertEqual(detail["detail"], "analyzer health: detekt no_health_evidence")


   def test_unknown_log_has_no_findings(self):
       self.assertEqual(classify("nothing here"), {"verdict": None, "findings": []})




if __name__ == "__main__":
   unittest.main()
