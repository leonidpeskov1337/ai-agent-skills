import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


import survey_failed_jobs as s  # noqa: E402


CASES = {
   "Gradle requires at least JVM runtime version 21. You are currently using 17": ("jvm_runtime", "project"),
   "Cannot find a Java installation on your machine matching: {languageVersion=25}": ("toolchain_missing", "platform"),
   "Project with path ':app' could not be found in root project": ("nested_build", "project"),
   "java.io.FileNotFoundException: /builds/x/local.properties": ("missing_file", "project"),
   "Could not GET 'https://repo.maven.apache.org/maven2/x.pom'. Received status code 429": ("maven_central_429", "project"),
   "ERROR: No matching distribution found for acme-internal-lib==1.2": ("pip_private_index", "platform"),
   "error: expected pip-compile lock file but found plain manifest": ("plain_manifest", "project"),
   ".gitlab_ds/dependency_resolution.sh was not found after 60 seconds": ("ds_sidecar_timeout", "infra"),
   "/bin/sh: shopt: not found": ("before_script", "platform"),
   "WARNING: gl-container-scanning-report.json: no matching files": ("cs_no_image", "project"),
   "ERROR: Job failed (system failure): prepare environment: waiting for pod running": ("runner_infra", "infra"),
   "Uploading artifacts... 413 Payload Too Large": ("artifact_413", "admin"),
   "x509: certificate signed by unknown authority": ("tls_ca", "platform"),
   "toomanyrequests: You have reached your pull rate limit": ("registry_429", "platform"),
   "Container was OOMKilled": ("oom", "infra"),
   "fork/exec /builds/acme/app/gradlew: permission denied": ("gradlew_not_executable", "project"),
   "Unsupported class file major version 61": ("old_gradle", "project"),
   "java.lang.OutOfMemoryError: Java heap space": ("gradle_heap", "project"),
   "WARN expected pip-compile lock file\nERROR: No matching distribution found for x": ("pip_private_index", "platform"),
   "Could not resolve plugin artifact 'com.acme.conventions:com.acme.conventions.gradle.plugin:1.0'": ("plugin_not_found", "project"),
}




class SurveyTransportTest(unittest.TestCase):
   def test_retries_share_call_budget(self):
       api = s.Api("https://gitlab.example.com", "test-token", max_calls=1)
       error = urllib.error.HTTPError(api.base, 503, "unavailable", {}, None)
       with patch.object(api.opener, "open", side_effect=error) as request:
           with self.assertRaisesRegex(RuntimeError, "budget exhausted"):
               api._request("/projects")
       self.assertEqual(request.call_count, 1)


class ClassifierTest(unittest.TestCase):
   def test_signatures(self):
       for log, expected in CASES.items():
           with self.subTest(log=log):
               self.assertEqual(s.classify("noise\n" + log + "\nmore noise"), expected)


   def test_specific_beats_generic(self):
       log = "No such file or directory\nUploading artifacts 413 Payload Too Large"
       self.assertEqual(s.classify(log)[0], "artifact_413")


   def test_oom_beats_incidental_missing_file(self):
       log = ("open scan_metrics.csv: no such file or directory\n"
              "Executing Lightz /lightz-core -max_memory 4096\n"
              "ERROR: Job failed: exit code: 137, reason: 'OOMKilled'")
       self.assertEqual(s.classify(log), ("advanced_sast_oom", "platform"))
       self.assertEqual(s.classify(log.replace("Lightz", "x").replace("lightz", "x")), ("oom", "infra"))


   def test_kics_oom_routes_before_generic_oom(self):
       log = ("[INFO] [kics] [2026-11-04T11:17:18Z] Inspector initialized, number of queries=1240\n"
              "ERROR: Job failed: exit code: 137, reason: 'OOMKilled'")
       self.assertEqual(s.classify(log), ("kics_resolver_oom", "platform"))
       self.assertEqual(s.classify(log.replace("[kics]", "[x]")), ("oom", "infra"))
       self.assertEqual(s.classify(log.split("\n")[0]), ("unclassified", "unknown"))
       self.assertEqual(s.classify(log.replace("[kics]", "[mykicswrapper]")), ("oom", "infra"))


   def test_failure_reason_fallback(self):
       self.assertEqual(s.classify(None, "runner_system_failure"), ("runner_infra", "infra"))


   def test_unclassified_and_no_log(self):
       self.assertEqual(s.classify("something new"), ("unclassified", "unknown"))
       self.assertEqual(s.classify(None), ("no_log", "unknown"))


   def test_default_job_regex(self):
       import re
       rx = re.compile(s.DEFAULT_JOB_REGEX)
       for name in ("semgrep-sast", "gitlab-advanced-sast-0", "dependency-scanning:gradle-resolution",
                    "secret-detection", "container-scanning", "kics-iac-sast"):
           self.assertTrue(rx.search(name), name)
       for name in ("build", "unit-test", "deploy-prod"):
           self.assertFalse(rx.search(name), name)


   def test_summarise_and_reclassify(self):
       data = {"since": "x", "jobs": [
           {"project": "a/b", "job": "dependency-scanning", "web_url": "u1", "failure_reason": "script_failure",
            "log_tail": "No matching distribution found for z", "class": "unclassified", "owner": "unknown"},
           {"project": "a/c", "job": "dependency-scanning", "web_url": "u2", "failure_reason": "script_failure",
            "log_tail": "No matching distribution found for y", "class": "unclassified", "owner": "unknown"},
       ]}
       data = s.reclassify(data)
       summary = s.summarise(data)
       self.assertEqual(summary["by_class"]["pip_private_index"]["projects"], 2)
       self.assertEqual(summary["by_owner"], {"platform": 2})


   def test_cli_summarise(self):
       with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
           json.dump({"since": "x", "jobs": []}, f)
       with contextlib.redirect_stdout(io.StringIO()):
           self.assertEqual(s.main(["--summarise", f.name]), 0)
       pathlib.Path(f.name).unlink()




if __name__ == "__main__":
   unittest.main()
