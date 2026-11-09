#!/usr/bin/env python3
"""Classify a quality-gate job log into known failure signatures (read-only, stdlib only)."""


import argparse
import json
import re
import sys


SIGNATURES = [
   (
       "metric_unavailable",
       re.compile(r"^\s*-?\s*(?P<metric>[\w.]+): metric is unavailable", re.M),
       "A required metric could not be measured; check diff status, coverage excludes, baseline.",
       "playbooks/metric-unavailable.md",
   ),
   (
       "threshold_below",
       re.compile(r"^\s*-?\s*(?P<metric>[\w.]+): (?P<actual>[\d.]+) is below (?P<limit>[\d.]+)", re.M),
       "Value under threshold; on a push to a protected branch compare baseline ref first.",
       "playbooks/gate-fails-after-merge.md",
   ),
   (
       "threshold_exceeded",
       re.compile(r"^\s*-?\s*(?P<metric>[\w.]+): (?P<actual>[\d.]+) exceeds (?P<limit>[\d.]+)", re.M),
       "Value over threshold; on a push to a protected branch compare baseline ref first.",
       "playbooks/gate-fails-after-merge.md",
   ),
   (
       "skipped_not_applicable",
       re.compile(r"SKIPPED (?P<metric>[\w.]+): not_applicable"),
       "No analyzable production source changed; usually expected for config/version-only MRs.",
       "playbooks/gate-skipped.md",
   ),
   (
       "skipped_baseline_missing",
       re.compile(r"SKIPPED (?P<metric>[\w.]+): baseline_missing"),
       "No baseline summary for the reference branch; the next successful branch pipeline creates it.",
       "playbooks/gate-skipped.md",
   ),
   (
       "configuration_error",
       re.compile(r"CONFIGURATION ERROR (?P<detail>.+)$", re.M),
       "Exception file or analyzer health problem; read the detail, then the summary analyzer_errors.",
       "playbooks/analyzer-missing.md",
   ),
   (
       "config_or_health_invalid",
       re.compile(r"configuration or analyzer health is invalid"),
       "Invalid exception/threshold or an analyzer health failure; fails in every mode.",
       "playbooks/analyzer-missing.md",
   ),
]


VERDICT = re.compile(r"Quality Gate (?P<status>PASSED|FAILED) \((?P<mode>\w+) mode\)")
NO_MERGE_BASE = re.compile(r"unavailable:no_merge_base")




def classify(text):
   verdict = VERDICT.search(text)
   findings = []
   for name, pattern, hint, playbook in SIGNATURES:
       for match in pattern.finditer(text):
           entry = {"signature": name, "hint": hint, "playbook": playbook}
           entry.update(match.groupdict())
           findings.append(entry)
   if NO_MERGE_BASE.search(text):
       findings.append(
           {
               "signature": "no_merge_base",
               "hint": "MR net diff is empty (commits cancel out) or the diff base is missing.",
               "playbook": "playbooks/metric-unavailable.md",
           }
       )
   return {
       "verdict": verdict.groupdict() if verdict else None,
       "findings": findings,
   }




def main(argv=None):
   parser = argparse.ArgumentParser(description=__doc__)
   parser.add_argument("log", nargs="?", help="path to a job log file")
   parser.add_argument("--stdin", action="store_true", help="read the log from stdin")
   args = parser.parse_args(argv)
   if args.stdin:
       text = sys.stdin.read()
   elif args.log:
       with open(args.log, encoding="utf-8", errors="replace") as handle:
           text = handle.read()
   else:
       parser.error("provide a log path or --stdin")
   json.dump(classify(text), sys.stdout, indent=2)
   sys.stdout.write("\n")
   return 0




if __name__ == "__main__":
   raise SystemExit(main())
