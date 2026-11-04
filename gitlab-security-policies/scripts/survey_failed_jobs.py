#!/usr/bin/env python3
"""Survey failed GitLab security-policy jobs and classify them by log signature.


Read-only. Uses only the GitLab REST API with a token taken from an environment variable.


 survey_failed_jobs.py --url https://gitlab.example.com --token-env GITLAB_TOKEN \
     --since 2026-01-01T00:00:00Z --group platform --fetch-logs > survey.json
 survey_failed_jobs.py --summarise survey.json
 survey_failed_jobs.py --reclassify survey.json > survey2.json
"""


from __future__ import annotations


import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from typing import Any, Iterable


DEFAULT_JOB_REGEX = (
   r"^(gitlab-advanced-sast|semgrep-sast|.*-sast|kics-iac-sast|secret-detection|"
   r"dependency-scanning.*|container-scanning|dast.*)(-\d+)?$"
)
LOG_TAIL_BYTES = 20_000


# Order matters: the first match wins, so specific signatures precede generic ones.
SIGNATURES: list[tuple[str, str, str]] = [
   ("artifact_413", "admin", r"413 Payload Too Large|Request Entity Too Large|artifact.*too large"),
   # Anchored so the two lookaheads scan the log once instead of from every offset.
   ("advanced_sast_oom", "platform", r"(?s)\A(?=.*lightz)(?=.*OOMKilled)"),
   ("kics_resolver_oom", "platform", r"(?s)\A(?=.*\bkics\b)(?=.*OOMKilled)"),
   ("oom", "infra", r"OOMKilled|exit code 137"),
   ("gradlew_not_executable", "project", r"fork/exec \S*gradlew: permission denied"),
   ("before_script", "platform", r"shopt: not found|readarray: not found"),
   ("jvm_runtime", "project", r"requires at least JVM runtime version \d+|This build uses a Java \d+ JVM"),
   ("toolchain_missing", "platform", r"Cannot find a Java installation|No matching toolchains found|toolchain.*download.*fail"),
   ("old_gradle", "project", r"Gradle version [\d.]+ (is )?not supported|minimum supported Gradle version|Unsupported class file major version"),
   ("gradle_heap", "project", r"Java heap space|GC overhead limit exceeded"),
   ("nested_build", "project", r"Project with path '[^']*' could not be found|GradleWrapperMain"),
   ("pip_private_index", "platform", r"No matching distribution found for"),
   ("constraints_path", "project", r"Could not open requirements file:.*constraint"),
   ("maven_central_429", "project", r"(429|Too Many Requests).*(repo\.maven\.apache\.org|repo1\.maven\.org)|(repo\.maven\.apache\.org|repo1\.maven\.org).*(429|Too Many Requests)"),
   ("plugin_not_found", "project", r"Could not resolve plugin artifact|Plugin\s+\[id:\s*'[^']+'[^\]]*\]\s+was not found"),
   ("missing_file", "project", r"FileNotFoundException|No such file or directory"),
   ("ds_sidecar_timeout", "infra", r"dependency_resolution\.sh.*not found after \d+ seconds"),
   ("cs_no_image", "project", r"gl-container-scanning-report\.json: no matching files"),
   ("tls_ca", "platform", r"x509: certificate signed by unknown authority|PKIX path building failed"),
   ("registry_429", "platform", r"toomanyrequests"),
   ("binary_store", "infra", r"Problems writing to Binary store"),
   ("git_infra", "infra", r"not our ref|exit code 128|The requested URL returned error: 50\d"),
   ("plain_manifest", "project", r"expected pip-compile lock file"),
   ("runner_infra", "infra", r"prepare environment|error dialing backend|tls: internal error|scheduler_failure|Resolving timed out"),
]
_COMPILED = [(c, o, re.compile(p, re.IGNORECASE)) for c, o, p in SIGNATURES]


FAILURE_REASON_CLASSES = {
   "runner_system_failure": ("runner_infra", "infra"),
   "scheduler_failure": ("runner_infra", "infra"),
   "stuck_or_timeout_failure": ("timeout", "infra"),
   "job_execution_timeout": ("timeout", "project"),
   "data_integrity_failure": ("runner_infra", "infra"),
}




def classify(log: str | None, failure_reason: str | None = None) -> tuple[str, str]:
   if log:
       for cls, owner, rx in _COMPILED:
           if rx.search(log):
               return cls, owner
   if failure_reason in FAILURE_REASON_CLASSES:
       return FAILURE_REASON_CLASSES[failure_reason]
   return ("unclassified" if log else "no_log"), "unknown"




class NoRedirect(urllib.request.HTTPRedirectHandler):
   def redirect_request(self, req, fp, code, msg, headers, newurl):
       return None


class Api:
   def __init__(self, url: str, token: str, max_calls: int) -> None:
       parsed = urllib.parse.urlsplit(url)
       if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.query or parsed.fragment:
           raise ValueError("Use an HTTPS GitLab base URL without credentials, query or fragment")
       self.base = url.rstrip("/") + "/api/v4"
       self.opener = urllib.request.build_opener(NoRedirect())
       self.token = token
       self.calls = 0
       self.max_calls = max_calls


   def _request(self, path: str, params: dict[str, Any] | None = None, raw: bool = False) -> tuple[Any, dict]:
       query = urllib.parse.urlencode(params or {}, doseq=True)
       req = urllib.request.Request(f"{self.base}{path}{'?' + query if query else ''}",
                                    headers={"PRIVATE-TOKEN": self.token})
       for attempt in range(4):
           if self.calls >= self.max_calls:
               raise RuntimeError(f"API call budget exhausted ({self.max_calls})")
           self.calls += 1
           try:
               with self.opener.open(req, timeout=60) as resp:
                   limit = 10_000_000
                   body = resp.read(limit + 1)
                   if len(body) > limit:
                       raise RuntimeError("API response exceeded the 10 MB limit")
                   headers = dict(resp.headers)
                   return (body if raw else json.loads(body)), headers
           except urllib.error.HTTPError as e:
               if e.code == 429 or e.code >= 500:
                   delay = e.headers.get("Retry-After", "")
                   if attempt < 3 and self.calls < self.max_calls:
                       time.sleep(min(30, int(delay)) if delay.isascii() and delay.isdecimal() and len(delay) < 10 else 2 ** attempt)
                   continue
               raise
       raise RuntimeError(f"giving up on {path}")


   def paged(self, path: str, params: dict[str, Any], limit: int) -> Iterable[dict]:
       page, n = 1, 0
       while True:
           items, headers = self._request(path, {**params, "per_page": 100, "page": page})
           for item in items:
               yield item
               n += 1
               if n >= limit:
                   return
           nxt = headers.get("X-Next-Page") or headers.get("x-next-page")
           if not nxt:
               return
           page = int(nxt)


   def trace_tail(self, project_id: int, job_id: int) -> str:
       body, _ = self._request(f"/projects/{project_id}/jobs/{job_id}/trace", raw=True)
       return body[-LOG_TAIL_BYTES:].decode("utf-8", "replace")




def survey(args: argparse.Namespace) -> dict:
   token = os.environ.get(args.token_env)
   if not token:
       sys.exit(f"environment variable {args.token_env} is not set")
   api = Api(args.url, token, args.max_calls)
   job_rx = re.compile(args.job_regex)


   params = {"last_activity_after": args.since, "archived": "false", "simple": "true", "order_by": "last_activity_at"}
   if args.group:
       path = f"/groups/{urllib.parse.quote(args.group, safe='')}/projects"
       params["include_subgroups"] = "true"
   else:
       path = "/projects"
   projects = list(api.paged(path, params, args.max_projects))


   latest: dict[tuple[int, str], dict] = {}
   for p in projects:
       try:
           jobs = api.paged(f"/projects/{p['id']}/jobs", {"scope[]": ["failed"]}, args.max_jobs_per_project)
           for j in jobs:
               if (j.get("created_at") or "") < args.since:
                   break
               if not job_rx.search(j["name"]):
                   continue
               key = (p["id"], j["name"])
               if key not in latest or j["id"] > latest[key]["job_id"]:
                   latest[key] = {
                       "project_id": p["id"],
                       "project": p["path_with_namespace"],
                       "job_id": j["id"],
                       "job": j["name"],
                       "stage": j.get("stage"),
                       "ref": j.get("ref"),
                       "created_at": j.get("created_at"),
                       "failure_reason": j.get("failure_reason"),
                       "web_url": j.get("web_url"),
                       "pipeline_source": (j.get("pipeline") or {}).get("source"),
                   }
       except (urllib.error.HTTPError, RuntimeError) as e:
           print(f"warning: {p['path_with_namespace']}: {e}", file=sys.stderr)
           if "budget" in str(e):
               break


   results = sorted(latest.values(), key=lambda r: r["created_at"] or "", reverse=True)
   for i, r in enumerate(results):
       log = None
       if args.fetch_logs and i < args.max_logs:
           try:
               log = api.trace_tail(r["project_id"], r["job_id"])
           except (urllib.error.HTTPError, RuntimeError) as e:
               print(f"warning: trace {r['job_id']}: {e}", file=sys.stderr)
       r["class"], r["owner"] = classify(log, r["failure_reason"])
       if log is not None and args.keep_logs:
           r["log_tail"] = log
   return {
       "since": args.since,
       "group": args.group,
       "job_regex": args.job_regex,
       "projects_scanned": len(projects),
       "api_calls": api.calls,
       "jobs": results,
   }




def summarise(data: dict, examples: int = 3) -> dict:
   by_class: dict[str, dict] = {}
   groups: dict[str, list[dict]] = defaultdict(list)
   for j in data["jobs"]:
       groups[j["class"]].append(j)
   for cls, jobs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
       by_class[cls] = {
           "owner": jobs[0]["owner"],
           "jobs": len(jobs),
           "projects": len({j["project"] for j in jobs}),
           "examples": [j["web_url"] for j in jobs[:examples]],
       }
   return {
       "since": data.get("since"),
       "total_failed_latest": len(data["jobs"]),
       "by_owner": dict(Counter(j["owner"] for j in data["jobs"]).most_common()),
       "by_job": dict(Counter(j["job"] for j in data["jobs"]).most_common()),
       "by_class": by_class,
   }




def reclassify(data: dict) -> dict:
   for j in data["jobs"]:
       j["class"], j["owner"] = classify(j.get("log_tail"), j.get("failure_reason"))
   return data




def main(argv: list[str] | None = None) -> int:
   ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
   ap.add_argument("--url", help="GitLab base URL")
   ap.add_argument("--token-env", default="GITLAB_TOKEN", help="name of env var holding a read_api token")
   ap.add_argument("--since", help="ISO-8601 timestamp; only jobs created after it")
   ap.add_argument("--group", help="group full path or ID; default: all visible projects")
   ap.add_argument("--job-regex", default=DEFAULT_JOB_REGEX)
   ap.add_argument("--max-projects", type=int, default=500)
   ap.add_argument("--max-jobs-per-project", type=int, default=200)
   ap.add_argument("--max-calls", type=int, default=5000)
   ap.add_argument("--fetch-logs", action="store_true", help="fetch job log tails for classification")
   ap.add_argument("--max-logs", type=int, default=300)
   ap.add_argument("--keep-logs", action="store_true", help="store log tails in output (enables --reclassify; may contain sensitive data)")
   ap.add_argument("--summarise", metavar="FILE", help="summarise an existing survey JSON")
   ap.add_argument("--reclassify", metavar="FILE", help="re-run classification on a survey saved with --keep-logs")
   args = ap.parse_args(argv)


   if args.summarise:
       with open(args.summarise) as f:
           out = summarise(json.load(f))
   elif args.reclassify:
       with open(args.reclassify) as f:
           out = reclassify(json.load(f))
   else:
       if not args.url or not args.since:
           ap.error("--url and --since are required for a survey")
       out = survey(args)
   json.dump(out, sys.stdout, indent=2)
   print()
   return 0




if __name__ == "__main__":
   sys.exit(main())
