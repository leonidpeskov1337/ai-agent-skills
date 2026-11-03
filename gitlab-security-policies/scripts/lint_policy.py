#!/usr/bin/env python3
"""Lint a GitLab security policy document (policy.yml) for silent-rejection traps and weak settings.


This complements, not replaces, validation against the JSON schema at the instance's version tag.
Accepts YAML (requires PyYAML) or JSON. Prints JSON findings; exits 1 if any error is found.


 lint_policy.py policy.yml [--require-tags] [--max-per-type 5]
"""


from __future__ import annotations


import argparse
import json
import sys
from typing import Any


KNOWN_TOP_LEVEL = {
   "scan_execution_policy",
   "approval_policy",
   "pipeline_execution_policy",
   "pipeline_execution_schedule_policy",
   "vulnerability_management_policy",
   "dependency_firewall_policy",
   "experiments",
}
SCHEDULE_POLICY_MAX = 5
APPROVAL_RULES_MAX = 5
VMP_RULES_MAX = 5
ACTION_MAX_PROPERTIES = {
   "dast": 7,
   "sast": 5,
   "secret_detection": 5,
   "dependency_scanning": 5,
   "cluster_image_scanning": 5,
}
SAST_LIKE = {"sast", "sast_iac", "secret_detection", "dependency_scanning"}
APPROVAL_BRANCH_TYPES = {"default", "protected"}
SEP_BRANCH_TYPES = {"all", "default", "protected", "target_default", "target_protected"}
APPROVAL_SETTINGS_EXPECTED = (
   "prevent_approval_by_author",
   "prevent_approval_by_commit_author",
   "remove_approvals_with_new_commit",
   "block_branch_modification",
   "prevent_pushing_and_force_pushing",
)




class Linter:
   def __init__(self, require_tags: bool, max_per_type: int) -> None:
       self.findings: list[dict[str, str]] = []
       self.require_tags = require_tags
       self.max_per_type = max_per_type


   def add(self, severity: str, where: str, message: str) -> None:
       self.findings.append({"severity": severity, "where": where, "message": message})


   def lint(self, doc: Any) -> list[dict[str, str]]:
       if not isinstance(doc, dict):
           self.add("error", "$", "document must be a mapping")
           return self.findings
       for key in doc:
           if key not in KNOWN_TOP_LEVEL:
               hint = " (use approval_policy)" if key == "scan_result_policy" else ""
               self.add("error", key, f"unknown top-level key{hint}; GitLab ignores the whole document")
       for key, policies in doc.items():
           if key not in KNOWN_TOP_LEVEL or key == "experiments":
               continue
           if not isinstance(policies, list):
               self.add("error", key, "must be a list")
               continue
           cap = SCHEDULE_POLICY_MAX if key == "pipeline_execution_schedule_policy" else self.max_per_type
           if len(policies) > cap:
               self.add("error", key, f"{len(policies)} policies exceed the limit of {cap}; extra policies are not applied")
           names = [p.get("name") for p in policies if isinstance(p, dict)]
           for dup in {n for n in names if names.count(n) > 1}:
               self.add("warning", key, f"duplicate policy name {dup!r}")
           for i, p in enumerate(policies):
               where = f"{key}[{i}]({p.get('name', '?') if isinstance(p, dict) else '?'})"
               if not isinstance(p, dict):
                   self.add("error", where, "policy must be a mapping")
                   continue
               self._common(where, p)
               getattr(self, f"_{key}", lambda *_: None)(where, p)
       return self.findings


   def _common(self, where: str, p: dict) -> None:
       for field in ("name", "enabled"):
           if field not in p:
               self.add("error", where, f"missing required {field!r}")
       if "policy_scope" in p:
           self._scope(f"{where}.policy_scope", p["policy_scope"])


   def _scope(self, where: str, scope: Any) -> None:
       if not isinstance(scope, dict):
           self.add("error", where, "must be a mapping")
           return
       for kind in ("projects", "groups", "compliance_frameworks"):
           block = scope.get(kind)
           if block is None:
               continue
           items = block if isinstance(block, list) else None
           if isinstance(block, dict):
               for direction in ("including", "excluding"):
                   if direction in block:
                       lst = block[direction]
                       if isinstance(lst, list) and not lst and direction == "including":
                           self.add("error", f"{where}.{kind}.{direction}", "empty 'including' is treated as no filter (applies everywhere); omit it")
                       elif isinstance(lst, list) and not lst:
                           self.add("warning", f"{where}.{kind}.{direction}", "empty list; omit the key")
                       for e in lst or []:
                           self._scope_entry(f"{where}.{kind}.{direction}", e)
           elif items is not None:
               for e in items:
                   self._scope_entry(f"{where}.{kind}", e)


   def _scope_entry(self, where: str, entry: Any) -> None:
       if isinstance(entry, dict) and "id" in entry and not isinstance(entry["id"], int):
           self.add("error", where, f"id {entry['id']!r} must be an integer, not a string")


   def _scan_execution_policy(self, where: str, p: dict) -> None:
       rules = p.get("rules") or []
       actions = p.get("actions") or []
       if not rules:
           self.add("error", where, "no rules")
       if not actions:
           self.add("error", where, "no actions")
       if (p.get("no_pipeline") or {}).get("allowed") is True:
           self.add("warning", where, "no_pipeline.allowed: true lets projects avoid policy pipelines")
       if (p.get("skip_ci") or {}).get("allowed") is True:
           self.add("info", where, "skip_ci.allowed: true; '[skip ci]' commits skip these scans")


       pipeline_rules = [r for r in rules if isinstance(r, dict) and r.get("type") == "pipeline"]
       for j, r in enumerate(rules):
           if isinstance(r, dict) and "pipeline_sources" in r and not isinstance(r["pipeline_sources"], dict):
               self.add("error", f"{where}.rules[{j}]", "pipeline_sources must be a mapping with 'including', not a list")
           if isinstance(r, dict) and r.get("branch_type") == "target_default":
               self.add("warning", f"{where}.rules[{j}]", "branch_type target_default can leave MRs into non-default branches unscanned; prefer all")
           if isinstance(r, dict) and r.get("branch_type") and r["branch_type"] not in SEP_BRANCH_TYPES:
               self.add("error", f"{where}.rules[{j}]", f"invalid branch_type {r['branch_type']!r}")
           if isinstance(r, dict) and r.get("type") == "schedule" and "cadence" not in r:
               self.add("error", f"{where}.rules[{j}]", "schedule rule requires cadence")
       if pipeline_rules:
           def sources(r: dict) -> set[str]:
               ps = r.get("pipeline_sources")
               return set((ps.get("including") if isinstance(ps, dict) else None) or [])
           has_mr = any(
               "merge_request_event" in sources(r)
               or (not sources(r) and r.get("branch_type") in ("all", "target_default", "target_protected"))
               for r in pipeline_rules
           )
           has_default = any(r.get("branch_type") in ("default", "all", None) or r.get("branches") for r in pipeline_rules)
           if not has_mr:
               self.add("warning", where, "no rule covers merge_request_event pipelines")
           if not has_default:
               self.add("warning", where, "no rule covers default-branch pipelines")


       for k, a in enumerate(actions):
           aw = f"{where}.actions[{k}]"
           if not isinstance(a, dict):
               self.add("error", aw, "action must be a mapping")
               continue
           scan = a.get("scan")
           cap = ACTION_MAX_PROPERTIES.get(scan)
           if cap and len(a) > cap:
               self.add("error", aw, f"{len(a)} properties exceed maxProperties {cap} for {scan}; document is rejected")
           if self.require_tags and not a.get("tags"):
               self.add("error", aw, "no tags; job stays pending if runners do not accept untagged jobs")
           if not (a.get("scan_settings") or {}).get("ignore_default_before_after_script"):
               self.add("warning", aw, "set scan_settings.ignore_default_before_after_script: true so project before_script cannot break or tamper with the scan")
           if "template" not in a:
               self.add("info", aw, "template not pinned; analyzer behaviour can change on upgrade")
           variables = a.get("variables") or {}
           for name, value in variables.items():
               if not isinstance(value, str):
                   self.add("error", f"{aw}.variables.{name}", "variable values must be strings")
           if scan in SAST_LIKE and pipeline_rules and variables.get("AST_ENABLE_MR_PIPELINES") != "true":
               self.add("warning", aw, "AST_ENABLE_MR_PIPELINES is not 'true'; analyzer may not run in MR pipelines")
           if scan == "dast" and not a.get("site_profile"):
               self.add("error", aw, "dast action requires site_profile")


   def _approval_policy(self, where: str, p: dict) -> None:
       rules = p.get("rules") or []
       if len(rules) > APPROVAL_RULES_MAX:
           self.add("error", where, f"{len(rules)} rules exceed {APPROVAL_RULES_MAX}")
       for j, r in enumerate(rules):
           if isinstance(r, dict) and "newly_detected" in (r.get("vulnerability_states") or []):
               self.add("error", f"{where}.rules[{j}]", "newly_detected was removed in 17.0 and invalidates the whole document; use new_needs_triage/new_dismissed")
           if isinstance(r, dict) and r.get("branch_type") and r["branch_type"] not in APPROVAL_BRANCH_TYPES:
               self.add("error", f"{where}.rules[{j}]", f"approval rule branch_type must be default|protected, got {r['branch_type']!r}")
       if (p.get("fallback_behavior") or {}).get("fail") != "closed":
           self.add("warning", where, "fallback_behavior.fail is not 'closed'; missing scans pass the gate")
       settings = p.get("approval_settings") or {}
       missing = [s for s in APPROVAL_SETTINGS_EXPECTED if settings.get(s) is not True]
       if missing:
           self.add("warning", where, "approval_settings not enforced: " + ", ".join(missing))
       for k, a in enumerate(p.get("actions") or []):
           if not isinstance(a, dict) or a.get("type") != "require_approval":
               continue
           roles = [str(r).lower() for r in a.get("role_approvers") or []]
           if "developer" in roles:
               self.add("warning", f"{where}.actions[{k}]", "role_approvers includes developer; any developer can approve the gate")
           if not any(a.get(f) for f in ("group_approvers", "group_approvers_ids", "user_approvers", "user_approvers_ids", "role_approvers")):
               self.add("error", f"{where}.actions[{k}]", "require_approval without approvers")
       if p.get("bypass_settings"):
           self.add("info", where, "bypass_settings present; confirm each bypass is justified and audited")
       if (p.get("policy_tuning") or {}).get("unblock_rules_using_execution_policies"):
           self.add("info", where, "unblock_rules_using_execution_policies weakens fail-closed (experimental)")


   def _vulnerability_management_policy(self, where: str, p: dict) -> None:
       rules = p.get("rules") or []
       if len(rules) > VMP_RULES_MAX:
           self.add("error", where, f"{len(rules)} rules exceed {VMP_RULES_MAX}")
       if "policy_scope" not in p:
           self.add("warning", where, "no policy_scope; auto-dismissal applies to every linked project")


   def _pipeline_execution_schedule_policy(self, where: str, p: dict) -> None:
       for field in ("content", "schedules"):
           if field not in p:
               self.add("error", where, f"missing required {field!r}")


   def _pipeline_execution_policy(self, where: str, p: dict) -> None:
       if p.get("pipeline_config_strategy") == "override_project_ci":
           self.add("info", where, "override_project_ci replaces project CI; confirm projects expect this")
       for field in ("content", "pipeline_config_strategy"):
           if field not in p:
               self.add("error", where, f"missing required {field!r}")
       vo = p.get("variables_override")
       if isinstance(vo, dict) and "allowed" not in vo:
           self.add("error", f"{where}.variables_override", "requires 'allowed'")
       if vo is None or (isinstance(vo, dict) and vo.get("allowed") is True and not vo.get("exceptions")):
           self.add("warning", where, "variables_override not denied; project variables can alter injected jobs")




def load(path: str) -> Any:
   with open(path) as f:
       text = f.read()
   if path.endswith(".json"):
       return json.loads(text)
   try:
       import yaml  # type: ignore
   except ImportError:
       try:
           return json.loads(text)
       except json.JSONDecodeError:
           sys.exit("PyYAML is required for YAML input (pip install pyyaml), or pass JSON")
   return yaml.safe_load(text)




def main(argv: list[str] | None = None) -> int:
   ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
   ap.add_argument("file")
   ap.add_argument("--require-tags", action="store_true", help="error if a scan action has no runner tags")
   ap.add_argument("--max-per-type", type=int, default=5, help="instance limit of policies per type (default 5)")
   args = ap.parse_args(argv)
   findings = Linter(args.require_tags, args.max_per_type).lint(load(args.file))
   json.dump({"file": args.file, "findings": findings}, sys.stdout, indent=2)
   print()
   return 1 if any(f["severity"] == "error" for f in findings) else 0




if __name__ == "__main__":
   sys.exit(main())
