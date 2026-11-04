# Troubleshooting: signature → cause → owner → fix


**Owner** decides who acts:


- **project**: the repository team;
- **platform**: whoever owns the policy content;
- **infra**: runners and the network;
- **admin**: instance settings;
- **product**: a GitLab limitation (workaround plus an upstream issue).


The regexes in `scripts/survey_failed_jobs.py` mirror these tables. Keep the two in sync.


## Contents


1. [Policy level: scans missing or not running](#policy-level-scans-missing-or-not-running)
2. [Job level: any scanner](#job-level-any-scanner)
3. [Dependency scanning v2 resolution](#dependency-scanning-v2-resolution)
4. [Findings missing or wrong](#findings-missing-or-wrong)
5. [Gates and exceptions](#gates-and-exceptions)
6. [Triage order](#triage-order)


## Policy level: scans missing or not running


| Signature | Likely cause | Owner | Check → fix |
|---|---|---|---|
| No policy jobs anywhere in the group after a change | `policy.yml` rejected (schema error, stringified ID, unknown key) | platform | GraphQL loaded-policies query returns nothing or stale names → validate against schema at version tag, fix generator |
| Some policies missing | Over the 5-per-type limit | platform | Count by type → consolidate |
| New project has no policy jobs; CI lint shows "no visible job" | Project not linked to inherited policies | platform | `resyncSecurityPolicies(project, INHERITED)`; automate on project creation |
| Change not visible yet | Async propagation | platform | Wait ≤10 min or resync group |
| Many new projects unlinked at once | Sidekiq degraded | infra | Check Sidekiq queues, then resync |
| Pipeline created via API has no policy jobs | API-triggered pipelines are not matched by push/MR rules | — | Test with real pushes/MRs |
| MRs into non-default branches unscanned | MR rule uses `branch_type: target_default` | platform | Use `branch_type: all` |
| MR shows "The following scans are missing" | Scanner excluded / skipped / job failed while gate expects report | platform/project | Align gate scope with scanner scope; fix failing job; scanner exception must cover gate |
| No pipeline at all for a push | Project `workflow:rules` suppress the source | project (platform if mandated) | Inspect `.gitlab-ci.yml` → fix rules or move enforcement to PEP |
| Job `pending`, "no runners online that can run this job" | Policy action lacks `tags` the runners require, or wrong tags | platform | Job `tag_list` vs runners → set `tags` on every action |
| Commit with `[skip ci]` has no scans | `skip_ci.allowed: true` | platform decision | Intended? Gate fail-closed should still demand approval on MRs |
| DAST job never appears on push | Expected: PEP schedule jobs only in `pipeline_execution_policy_schedule` pipelines | — | Check scheduled pipelines |
| DAST job created untagged, pending forever | SEP `dast` action without validated site profile | platform | Move to PEP schedule policy |
| Policy job in some projects only | Scope (`including`/`excluding`, compliance framework) | platform | Query `policyScope` on the loaded policy |


## Job level: any scanner


| Log signature | Cause | Owner | Fix |
|---|---|---|---|
| `shopt: not found`, `readarray: not found`, exit 127 early | Project `default:before_script` ran in scanner image | platform | `scan_settings.ignore_default_before_after_script: true` |
| `gl-container-scanning-report.json: no matching files` | No image to scan (`CS_IMAGE` unset) | project/platform | Set `CS_IMAGE` in the image-building job's pipeline, or scanner exception for repos with no image |
| `prepare environment`, `error dialing backend`, `tls: internal error`, `scheduler_failure`, `Resolving timed out` | Runner/Kubernetes transient | infra | Retry; recurring → runner/kubelet investigation |
| `exit code: 137, reason: 'OOMKilled'` with `lightz-core` lines (class `advanced_sast_oom`) | Advanced SAST workers × detected memory exceed the pod limit. A large repository makes it worse. Small repositories pass with the same settings | platform | Size the policy's SAST action (pod limit plus `ADVANCED_SAST_AVAILABLE_*`). Projects may add `SAST_EXCLUDED_PATHS` |
| `OOMKilled` with KICS markers (class `kics_resolver_oom`), often after `Inspector initialized, number of queries=…` | Candidate file-reference expansion from repository or downloaded-artifact YAML/JSON, or effective pod memory sizing | platform | Check input references, runner override and actual limit. Evaluate resolver depth 0 on an approved sandbox canary and compare exact findings. The routing signature identifies KICS OOM for investigation and requires further evidence to establish resolver expansion. |
| `ERR Timeout processing the results` in a successful KICS job | Query execution exceeded its timeout and report coverage may be incomplete | platform | Inspect effective per-query timeout and completion. Evaluate `KICS_TIMEOUT: "300"` with coverage and overall job-budget checks. |
| `ERROR: Job failed: pod … OOMKilled`, exit 137 | Effective scanner memory limit, input expansion or analyzer-specific worker sizing | infra/platform | Cap analyzer workers and raise memory for policy jobs |
| `fork/exec …/gradlew: permission denied` (in `spotbugs-sast`) | Wrapper committed as `100644`; SpotBugs executes it directly | project | `git update-index --chmod=+x gradlew` and commit |
| `Problems writing to Binary store` | Gradle cache on shared volume / disk | infra | Retry; check volume |
| `fatal: … not our ref`, exit 128 at fetch, HTTP 500 from GitLab | Git/GitLab transient | infra | Retry |
| `Uploading artifacts … 413 Payload Too Large` / `too large` | Report artifact exceeds instance plan limit (CycloneDX, dependency_scanning) | admin | Raise the artifact-type limit (CycloneDX: Admin UI or Rails console; the 19.4 REST API drops it); nothing was ingested until then |
| `x509: certificate signed by unknown authority`, `PKIX path building failed` | TLS interception without CA in analyzer image | platform/infra | Supply CA via `ADDITIONAL_CA_CERT_BUNDLE` (policy variable) |
| `toomanyrequests` / image pull 429 | Registry rate limit pulling analyzer images | platform | Pull analyzers via internal registry mirror (`SECURE_ANALYZERS_PREFIX`) |


The failed-job survey examines failed jobs. Inspect successful KICS logs separately
for query timeouts and verify report completeness.

## Dependency scanning v2 resolution


Jobs: `dependency-scanning:<maven|gradle|python>-resolution` (`.pre`) produce graph files; then
`dependency-scanning` builds the SBOM and scans.


| Log signature | Cause | Owner | Fix |
|---|---|---|---|
| `requires at least JVM runtime version 2[15]` / `This build uses a Java 17 JVM` | Settings/build plugin compiled for newer JVM than the daemon | project | `gradle/gradle-daemon-jvm.properties` `toolchainVersion=<N>` with committed wrapper ≥ 8.8, ≥ 9.1 for JDK 25 (resolution image must provide that JDK) |
| `Cannot find a Java installation … matching`, toolchain download failing | Toolchain not in image, auto-provisioning blocked | platform | Multi-JDK resolution image via `DS_GRADLE_RESOLUTION_IMAGE` |
| `Gradle version … not supported` / `Unsupported class file major version 61` / Gradle < 7.3 | Old wrapper | project | Upgrade wrapper |
| `Java heap space` / `OutOfMemoryError` during resolution | Default Gradle heap too small | project | `GRADLE_CLI_OPTS: "-Dorg.gradle.jvmargs=-Xmx2g"` as project CI/CD settings variable |
| `Project with path ':…' could not be found`, `GradleWrapperMain` | Nested build (`settings.gradle`/`gradlew` not at root) | project | Make root a build or exclude nested dir via path exception |
| `No such file or directory` / `FileNotFoundException` for `local*.properties`, `google-services.json`, secrets files | Build needs uncommitted local file | project | Committed CI-safe defaults or guarded reads |
| `429` / `Too Many Requests` from `repo.maven.apache.org`/`repo1.maven.org` | Direct Maven Central under load | project/platform | Repositories via internal proxy; consider platform-level mirror init script |
| `Could not resolve plugin artifact` / `Plugin … was not found` in internal repo | Unpublished internal plugin/version | project | Publish or fix version |
| `No matching distribution found for <internal-pkg>` | `pip-compile` ignores `[tool.uv]` indexes | platform | Pin `PIP_INDEX_URL` (superset internal index) as policy variable |
| `Could not open requirements file: … constraints` / absolute path, analyzer `FATA` | Absolute constraint path | project | Repository-relative constraints |
| `expected pip-compile lock file but found plain manifest` | Parsing warning, usually not the failure | — | Find the real error further down the log |
| `pip-compile` fails on `git+` URL or native build | Unresolvable source or missing build toolchain | project | Publish to the index, or path exception |
| `.gitlab_ds/dependency_resolution.sh … not found after 60 seconds` | Analyzer sidecar did not start in time | infra/product | Retry manually (policies cannot set `retry`); persistent → runner resources |
| Resolution green but scan finds nothing new | Graph lacks configuration, or scan job failed afterwards (413) | see "Findings missing" | |


## Findings missing or wrong


1. Did the **scan job** (not just resolution) succeed and upload its report? `artifacts` of the job.
2. Is the pipeline an MR pipeline with the MR's head? Findings compare against target branch.
3. Was the dependency actually resolved? Check graph files (`gradle.graph.txt`, `pipdeptree.json`)
  or SBOM for the package and version.
4. Is the vulnerable version in the advisory DB range? Check the advisory, not the CVE title.
5. Was it auto-dismissed (state `DISMISSED`, author = policy bot) or already present on target
  (not "new")?
6. Is the MR widget truncated? Check the pipeline Security tab.
7. "Too many findings": group by manifest file and configuration (test/lint/debug/release); count
  per module duplication; separate SCA from SAST before judging validity.


## Gates and exceptions


| Signature | Cause | Fix |
|---|---|---|
| Dismissed finding still blocks open MR | Approval is the unblock path; MR rules snapshotted | Approve, or re-evaluate MR (`mergeRequestResyncSecurityPolicies`, experiment) / recreate MR |
| Exception merged but finding still `DETECTED` | Auto-dismiss only at next default-branch ingestion; policy not linked to project | Run a default-branch pipeline; INHERITED (+DIRECT) resync |
| Exception removed but findings keep being dismissed | Override document not reloaded | `DIRECT` resync on project |
| Path exception ignored | Path not repo-relative, glob semantics (`*` vs `**/`), or project still excluded by whole-scanner exception | Fix pattern; whole-scanner exception wins |
| SAST excluded but MR still needs approval | IaC still feeds the shared `sast` gate, fail-closed | Exclude both or neither |
| Anyone can approve the gate | `role_approvers: [developer]` | Group approvers with direct, accountable members |


## Triage order


1. Is the job a policy job and did the policy load? (GraphQL)
2. Did a pipeline exist? (`workflow:rules`, `skip_ci`)
3. Did the job get a runner? (tags)
4. Did the job run the scanner? (before_script, prerequisites)
5. Did resolution/scan succeed? (log signatures)
6. Was the report uploaded and ingested? (artifacts, 413)
7. Did the gate/exception behave? (scope, snapshot, dismissal state)
