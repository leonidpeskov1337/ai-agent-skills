# GitLab behaviour: verified facts and traps


Unless a row says otherwise, everything here was **measured** on GitLab EE 19.2â€“19.4
(self-managed). Behaviour changes between minor releases. Before relying on a row:


- re-check it on the running version;
- read the release notes for the versions in between.


Mark each claim in reports as *verified here*, *documented* or *inferred*.


## Contents


1. [Policy loading and propagation](#policy-loading-and-propagation)
2. [Scope and linking](#scope-and-linking)
3. [Pipelines and jobs](#pipelines-and-jobs)
4. [Pipeline execution policies (runtime)](#pipeline-execution-policies-runtime)
5. [Custom security reports and ingestion](#custom-security-reports-and-ingestion)
6. [Gates and approvals](#gates-and-approvals)
7. [Vulnerability lifecycle](#vulnerability-lifecycle)
8. [Dependency scanning v2](#dependency-scanning-v2)
9. [Reports and UI](#reports-and-ui)
10. [DAST](#dast)
11. [Limits](#limits)


## Policy loading and propagation


| Behaviour | Consequence |
|---|---|
| An invalid `policy.yml` is accepted on commit and then **ignored as a whole**, with no error in the UI, no failed pipeline and no audit event | Verify via GraphQL after every change (runbooks) |
| A stringified project ID in `policy_scope` invalidates the document | Emit integers; test the generator |
| Policy changes propagate asynchronously, typically within ~10 min. On one instance a group-level change never propagated without a resync | Run `resyncSecurityPolicies(fullPath: group)` after commits |
| A **new project** created under a linked group was not linked to the inherited policies: no scans, and CI lint showed "no visible job". Neither a policy change nor a group resync fixed it | Run `resyncSecurityPolicies(fullPath: project, relationship: INHERITED)` for new projects |
| A project's own override document needed `relationship: DIRECT` to reload. `INHERITED` alone left a removed exception active for 20+ min | Resync both when a project has its own policy project |
| A newly created vulnerability management policy was **not linked to existing projects**, so auto-dismiss did nothing after 15 min | Run an `INHERITED` resync on each affected project after the group resync |
| Linking and propagation run in Sidekiq. While Sidekiq was degraded, new projects silently stayed unlinked | Check Sidekiq health before blaming the policy |
| A new project without CI may get a failed or empty pipeline before its `INHERITED` link completes | Expected noise. Do not auto-delete such pipelines: a deletion rule cannot reliably tell them from real history |


## Scope and linking


- `securityPolicyProject` is singular per group and per project. Linking another policy project
 **replaces** the existing link. Project-level links are additive with policies inherited from
 groups.
- An empty scope means all projects. This applies to an empty `including` list and to an absent
 `policy_scope`.
- `projects.excluding` keeps new projects covered by default. `groups.including` covers
 repositories added later to that subgroup, including ones created outside the provisioning
 tool.
- Archived projects can be excluded through the scope (`excluding_archived_projects` in newer
 versions). Otherwise they still count.


## Pipelines and jobs


| Behaviour | Consequence |
|---|---|
| Projects **without** `.gitlab-ci.yml` still get a policy pipeline containing the scanner jobs | Coverage does not depend on project CI existing |
| A policy-forced pipeline also runs the project's **entire** `.gitlab-ci.yml` | Blocking `[skip ci]` makes release-bot commits run full pipelines |
| `workflow:rules` with `when: never` for a source prevents the pipeline, so the SEP has nothing to attach to | Documented upstream. Use a PEP with `override_project_ci`, or detect it |
| Scanner jobs inherit `default:before_script`/`after_script` unless `ignore_default_before_after_script: true` | A project script can kill scanners. Policy jobs are `allow_failure`, so the pipeline stays green: a silent fail-open |
| An MR rule with `branch_type: target_default` left MRs into non-default branches (GitFlow `feature/* â†’ develop`) unscanned in production, while a sandbox did not reproduce it | Use `branch_type: all` for MR rules; it is correct under either reading |
| Pipelines created through the API (`POST /projects/:id/pipeline`) got no policy jobs under push/MR rules, and the call returns `400 Missing CI config file` without a `.gitlab-ci.yml` | Test policies with real pushes and MRs |
| Policy jobs carry only the policy's `tags` | If no runner accepts untagged jobs, an untagged policy job stays `pending` forever ("no runners online") |
| Policy variables override project and group variables for policy jobs, and only variables the policy sets are locked. The job log line "User-defined CI/CD variables are allowed â€¦ (except for X, Y)" lists the locked set | Set every security-relevant knob in the policy. Unset knobs (`DS_DISABLED_RESOLUTION_JOBS`, `MAVEN_ARGS`, `GRADLE_OPTS`, `JAVA_TOOL_OPTIONS`) remain project-controllable |
| Precedence: policy variables (locked) > project CI/CD settings variables > template job-level variables (for example `DS_*_RESOLUTION_IMAGE`) > top-level `variables:` in the project's `.gitlab-ci.yml`. Top-level variables **do** reach policy jobs but lose to template job-level defaults. They still apply to anything the template leaves unset, such as `KUBERNETES_MEMORY_LIMIT` | Tell projects to use CI/CD settings variables for supported workarounds. Set resource variables in the policy if the platform owns sizing |
| A scan execution policy cannot set `retry` or `allow_failure: false` on its jobs | Transient failures need a manual retry. Detect failures by survey, not by pipeline status |
| `FAIL_NEVER=true` (and similar) turns a failing analyzer into a green job with no report | Never use it to quiet failures; it hides coverage loss |
| GitLab pre-sets `*_EXCLUDED_PATHS` on policy-enforced projects. Only a policy can override them | Path exceptions need a policy-level variable, usually via a per-project override policy project |
| A missing prerequisite makes most scanners skip quietly. **Container scanning fails** (`gl-container-scanning-report.json: no matching files`) | Make container scanning opt-in per image-building group |
| `AST_ENABLE_MR_PIPELINES` is needed for analyzers to run in MR pipelines | Set it as a policy variable |
| Including security templates in the project as well as the policy produces duplicate jobs | Harmless for enforcement. Ask projects to remove the local includes |
| Repository rulesets (`.gitlab/sast-ruleset.toml`, gitleaks config) suppress findings before the gate sees them | Not closed by default. A locked policy variable `SECURE_ENABLE_LOCAL_CONFIGURATION: "false"` should close it (*unverified*); otherwise CODEOWNERS and review |
| A wrapper committed without the exec bit (`100644`) fails with `fork/exec â€¦/gradlew: permission denied` in **`spotbugs-sast`**, which executes `gradlew` directly. It is triggered by Groovy, Scala or Kotlin sources. DS v2 Gradle resolution runs `sh ./gradlew` and is unaffected (19.4) | Project fix: `git update-index --chmod=+x gradlew` (beware `core.fileMode` reverting it on `commit -a`). Do not run analyzers privileged or chmod runner-wide |
| SpotBugs (Java SAST fallback) compiles the project by running `gradlew`/`mvn`, so build problems surface as SAST failures | Treat as a build issue; `COMPILE` and `SAST_JAVA_VERSION` affect only SpotBugs |
| Some analyzers (Advanced SAST) size worker counts from node CPUs, not the pod's cgroup, and OOM on small pods. Advanced SAST starts up to 3 `lightz` workers. Each gets `-max_memory` equal to the **whole** detected memory, and GitLab documents at least 4 GB per worker | Set `ADVANCED_SAST_AVAILABLE_CPUS` and `ADVANCED_SAST_AVAILABLE_MEMORY` in the policy, together with `KUBERNETES_MEMORY_LIMIT` â‰¥ workers Ã— 4 GB. The job log should show "Overriding the detected CPU amount" and `MemoryLimit overwritten` |
| KICS (IaC) file-reference resolution and timeouts, reported on GitLab EE 19.4, analyzer 6.13.0 / KICS 2.1.20 | YAML/JSON references into repository files and downloaded artifacts expanded a monorepo scan from 3.7 GB to 14 GB peak, exceeding an 8Gi pod limit. The supplied canary used `KICS_MAX_RESOLVER_DEPTH: "0"` and reported 9,775 identical rule/file/line findings, 0.5 GB peak and 69 s versus 458 s. Depth 1 still peaked at 8.9 GB. Check the effective variable mapping on the installed analyzer and compare coverage before adoption. In this case `.gitignore`, `SAST_EXCLUDED_PATHS` and worker reductions did not resolve the expansion. Query timeouts also dropped findings. Evaluate `KICS_TIMEOUT: "300"` with completion and job-budget evidence. |

The supplied KICS build used Go 1.25 and logged `CPU: 4.0` under a four-CPU pod
limit. Verify runtime and worker overrides on the installed build. Its `Total memory`
log described the node. Use the runner override and actual cgroup limit for sizing.
In that reproduction, 4/8/16 workers used 3.6/3.8/4.1 GB, making resolver expansion
the more discriminating test. These are attributed incident observations.


## Pipeline execution policies (runtime)


These additions combine documented rules with reporter observations on EE 19.4.4â€“19.4.5.
See [provenance](sources.md#provenance); they are not maintainer reproductions.


| Behaviour | Consequence |
|---|---|
| **An `inject_policy` PEP can change stage layout and move SEP jobs.** Non-DAST SEP jobs run in `test` (DAST has its own stage). Only when the pipeline has no `test` stage does GitLab inject `scan-policies` (after `build`, or first). A PEP whose content declares no `stages:` uses the default `[build, test, deploy]`, so `test` exists once the PEP applies. SEP jobs then move from `scan-policies` to `test` (*documented* for both rules; the interaction was *measured* on 19.4.5) | A project job that hard-codes `stage: scan-policies` without declaring it fails pipeline **creation**: `<job> job: chosen stage scan-policies does not exist; available stages are â€¦`. The pipeline is `failed` with no jobs. In that reproduction, REST `yaml_errors` was `null` and GraphQL `pipeline.errorMessages` exposed the error. Fix: the project declares every stage it uses. Before rollout, search scoped projects for `stage: scan-policies` |
| The reserved stages `.pipeline-policy-pre` and `.pipeline-policy-post` guarantee policy-job stage placement. Jobs placed in standard or project stages "may be ignored depending on the project pipeline configuration" (*documented*) | Put policy jobs in reserved stages. Avoid PEP-defined custom stages unless they are ordered consistently with every scoped project (`Cyclic dependencies detected when enforcing policies`) |
| `.pipeline-policy-pre` blocks the whole pipeline. From 18.10, if it fails, later jobs are skipped, even those with `needs: []` or `when: always` (verify feature-flag state on older releases) (*documented*) | Use it only for real gates; put long or optional work elsewhere |
| A policy job in `.pipeline-policy-post` keeps the default `when: on_success`. It is **skipped** when any earlier job that is not `allow_failure` fails (*measured*) | Unrelated build, lint or notification failures silently skip the scan. Use `when: always` only for independent scans and detect skips; it cannot bypass the failed `.pipeline-policy-pre` gate on current versions |
| PEP users need read access to the CI content project. If the content is stored in the security policy project, alternatively enable that project's pipeline-execution access setting (`spp_repository_pipeline_access` in the projects API). Without it: `Project <path> not found or access denied` (*measured*) | The supplied rollout reports a provider gap in its 18.x provider. Check the pinned provider schema and use a reviewed API fallback only if still necessary |
| `variables_override: {allowed: false, exceptions: [X]}` withholds project and group variables from policy jobs, except the listed ones. The job log states it: "User-defined CI/CD variables are ignored â€¦ (except for â€¦)" (*measured*) | Use an allow-list for the few variables a project must supply. Verify effective inputs, including dotenv behavior at the running version; an exception can override a policy value |
| A policy-injected `trigger:` job with `strategy: depend` and `forward: {yaml_variables: false, pipeline_variables: false}` creates the downstream pipeline in a central project (*measured*, 19.4.5) | Can isolate credentials in reviewed central CI. Disable both forwarding paths and use `inherit:variables: false`; validate any remaining explicit inputs; do not execute source-project scripts or artifacts with central secrets. Confirm where the report must be uploaded: downstream reports do not automatically become source-project vulnerability records |
| Multi-project downstream authorization uses the upstream triggering identity (which can be a policy bot; identify it). The user needs permission to run pipelines on the target ref of the central project (*measured*) | Protect the central project's branch and require review. Restrict changes to central CI and its includes independently from permission to trigger it; triggering alone does not confer repository write access |
| Pipeline variables outrank ordinary project and YAML variables; policy-enforced variables have separate precedence (*documented*) | Set the central project's `ci_pipeline_variables_minimum_override_role` to `no_one_allowed`. Read the setting back and test rejection of an unauthorized variable; a language `None` or API `null` does not establish `no_one_allowed` |
| Unprotected MR source branches normally cannot access protected variables; protected-branch MR access has version-specific conditions (*documented*) | Prefer short-lived OIDC (`id_tokens`) credentials in reviewed central CI, with audience, project/ref and protected-ref claims restricted by the cloud trust policy. Centralization alone does not make attacker-controlled inputs safe |
| The supplied 19.4.5 rollout could not use `CI_JOB_TOKEN` for MR diffs, note writes or cross-project pipeline listing (*measured*); job tokens do support some MR/notes reads (*documented*) | Check endpoint support, fine-grained permissions, target allowlist and triggering-user access before choosing credentials. If a bot token with `api` is necessary for note writes, scope its membership, lifetime and storage; read-only investigation does not need it |
| Editing another user's bot note returned `403` in the supplied rollout (*measured*, not a universal statement about admin permissions) | When updating a "sticky" MR comment, only edit notes authored by the current token's user. Otherwise create a new note only when commenting is explicitly authorized |
| Scheduled PEP (`pipeline_execution_schedule_policy`): `daily`/`weekly`/`monthly` schedules with `start_time`, `timezone` and `time_window` (minimum 600 s). Branches are exact names (*documented*/*measured*). The pipeline contains only policy jobs, not project CI (*measured*) | A scheduled scan cannot rely on the project building the artifact in the same pipeline. Generate artifacts in policy jobs or fetch a verified earlier artifact for the intended source project/ref/SHA. If reusing artifacts, `expire_in` must cover schedule gaps, weekends and missed runs; never silently scan a different revision |
| `rules:changes` compares the whole MR diff with the target branch in MR pipelines. Branch pipelines compare with the previous push; without `compare_to`, new branches and pipelines without a push event match (*documented*) | Use MR-scoped change filters for MR-only work, or explicitly choose and test `compare_to` for other sources |
| Overlapping push and MR rules can create two pipelines for one commit; `$CI_OPEN_MERGE_REQUESTS` is a condition, not a deduplication mechanism by itself (*measured*) | Prevent duplicate sources where intended, or deduplicate consumers by source project, exact SHA, pipeline type and artifact-producing job. Newest alone is insufficient; preserve MR/merge-train coverage |
| MR, merged-results and merge-train pipelines can use different refs and generated SHAs; project rules may build in only some of them (*measured*) | Test each pipeline type when a policy job consumes project artifacts |
| `resource_group` serialises jobs, not work already submitted to an external service (*inferred*) | Hold the job until external work completes, or enforce concurrency in the external service; releasing the job can leave submitted work running |


## Custom security reports and ingestion


| Behaviour | Consequence |
|---|---|
| Security-report ingestion requires a supported `artifacts:reports:<type>` declaration; plain `artifacts:paths` does not register a security report (*documented*) | A third-party scanner must emit a schema-valid report under the right report type |
| The supplied 19.4.5 instance reportedly accepted security report schemas 15.0.0â€“15.2.4 (*measured by reporter; not independently checked*) | Pin the report `version` to one the instance supports. Validate against that exact schema version |
| **Escaped non-BMP characters broke ingestion in the supplied reproduction.** A finding snippet with an emoji, written as the JSON surrogate pair `\ud83d\udd25` (Python `json.dumps` default `ensure_ascii=True`), passed schema validation and parsed. Storing it failed with `ActiveRecord::StatementInvalid: PG::Error: invalid multibyte character`. The UI showed only "Error parsing security reports â€¦ [ScanIngestionError] Ingestion failed for security scan", and the `Security::Scan` state was `preparation_failed` (*measured*, 19.4.5) | For this reproduced failure, emit literal UTF-8 (`ensure_ascii=False`, file encoding `utf-8`) and test a finding with an emoji through actual ingestion. Valid JSON surrogate pairs are legal; their presence alone does not prove a report is corrupt. Reject malformed Unicode separately; schema validation alone does not prove ingestibility |
| `StoreScanService` catches the exception and reports only `ScanIngestionError`. The real error is in Sidekiq logs (retention depends on deployment) or, with explicit write authorization, controlled service replay in a sandbox (*measured*) | See runbooks Â§ Ingestion root cause |
| The supplied failure was not repaired by an in-memory parser patch. The report is re-parsed from the artifact (`Security::Scan#security_report`) during later processing, so patching the parser at runtime is not enough (*measured*) | Fix and release the producer, then run a new scan with authorized execution. Prefer a new valid artifact over patching live parser state; do not claim every ingestion failure is unrecoverable |
| Project Vulnerability Report data comes from default-branch pipelines. That includes scheduled PEP pipelines on the default branch. Reports from tags and other branches appear only in that pipeline's Security tab (*measured*) | Schedule scans on the default branch if the findings should be tracked |
| Finding identity depends on stable identifiers and location. The supplied DAST guidance uses `method`, `path` and `param` with hostname excluded; verify the DAST location fingerprint in the source at the running version before relying on that identity rule | Keep the location fields stable between runs, and compare finding UUIDs and states on a canary; changes can recreate findings and lose triage |
| A partial scan, such as a changed-files-only or incremental scan, ingested as a full report can make absent findings look resolved (*inferred*) | Keep incomplete snapshots out of full-report ingestion unless the report type/version explicitly supports incremental semantics and the lifecycle is proven. Otherwise use plain artifacts or an explicitly authorized MR note; prove behavior with an unchanged known finding on a canary |


## Gates and approvals


| Behaviour | Consequence |
|---|---|
| `enforcement_type: warn` leaves the MR **unmergeable** until it is bypassed with a reason or approved | `warn` is not advisory-only. Because the author can bypass, a dead scanner ("scans missing") is easy to wave through; fail-closed bites fully only in `enforce` |
| `approval_settings` bypass protections are applied for `enforce` gates, not for `warn` | Do not count on them before `block` |
| `fallback_behavior: {fail: closed}` requires approval when a required report is missing | Keep gate scope equal to scanner scope. Otherwise excluded projects need approval forever |
| `group_approvers` are documented as direct members only, yet a sandbox showed 6 eligible approvers from a group with 1 direct member (*unexplained*) | List eligible approvers on a real MR before trusting the set |
| With SSO/SAML provisioning everyone as Developer, `role_approvers: [maintainer]` leaves nobody eligible, so `block` is unmergeable | Check the real role distribution before choosing role approvers |
| Group-level custom roles are deprecated on self-managed; creating one returned 400 | Dismissal rights cannot be delegated through a custom group role |
| `role_approvers: [developer]` typically makes hundreds of people eligible | A weak control. Prefer small accountable groups |
| GitLab snapshots MR approval rules at MR creation. Removing a project from a gate does not update open MRs | Recreate the MR, or close and reopen it, after the exception applies |
| A dismissed finding stops counting only if the gate uses `vulnerability_states: [new_needs_triage]` | Pair this with restricted dismissal rights |
| IaC (KICS) findings report as `sast` | One gate serves both. Exceptions must list both or neither |


## Vulnerability lifecycle


- Changing a vulnerability's status needs **Maintainer, Owner or Security Manager**. Developers
 cannot dismiss their own findings.
- Auto-dismiss runs at **default-branch scan ingestion** only:
 - it is not retroactive;
 - it does not cover findings introduced by an MR;
 - GitLab never reverts it after the policy is removed.
- Secret detection reports only the commits in a push or MR. An existing secret is re-evaluated
 only when a commit changes its line.
- Identifier matching in vulnerability management policies:
 - Exact names work for every scanner.
 - Typed matching worked only for `cve`, `cwe` and `owasp` on 19.2.
 - Names are scanner-specific:
   - KICS uses the rule title (`Missing User Instruction`);
   - secret detection uses `Gitleaks rule ID <rule>`;
   - Semgrep uses `SAST Rules ID - <rule>`;
   - advisories use `CVE-â€¦`, `GHSA-â€¦` or `Gemnasium-<uuid>`.
- Criteria in a rule are ANDed. `file_path` globs follow `File.fnmatch` with `FNM_PATHNAME`: `*`
 stays within one directory and `**/` spans directories.


## Dependency scanning v2


| Behaviour | Consequence |
|---|---|
| Finding UUID = report type + primary identifier + location (file:package) + project. Any change of the reported file recreates findings and loses triage | Before changing an analyzer or template, measure on a canary: record UUIDs and states, switch, compare |
| Switching from Gemnasium to `template: v2` kept all UUIDs and states in the canary (127/127); both emit the same `Gemnasium-<uuid>` identifiers | Triage and identifier-based exceptions survive the migration |
| A null or `default` dependency-scanning template still runs Gemnasium (deprecated in 17.9, proposed for removal in 20.0). `template: v2` exists from 18.4. Gemnasium-maven scans only the first matched directory | Pin `v2` explicitly |
| A failed resolution job only turns the pipeline yellow; the scan then falls back to direct dependencies (85 instead of 121 findings in one test) | Coverage drops silently. Survey resolution failures |
| When the default branch's resolution fails, its baseline is tiny, so almost every MR finding shows as "new" | Fix default-branch resolution before enabling gates |
| v2 scans **every** build directory, not the first one found | More findings in monorepos. Duplicates per module are expected |
| Resolution jobs (`dependency-scanning:{maven,gradle,python}-resolution`, `.pre`) **run the project's build tooling** | They execute untrusted build scripts. Use no platform secrets |
| The default Gradle resolution image ships one JDK, and toolchain auto-download fails behind TLS interception | Pin a multi-JDK image via `DS_GRADLE_RESOLUTION_IMAGE` |
| A Gradle settings plugin requiring JVM 21 or 25 fails while the daemon runs an older JDK | The project adds `gradle/gradle-daemon-jvm.properties` with `toolchainVersion=<N>`. Daemon toolchains need a committed wrapper of Gradle â‰¥ 8.8, and â‰¥ 9.1 for JDK 25 |
| A multi-JDK resolution image works best with the daemon on JDK 17 (runs Gradle 7.3â€“9.x; Gradle 8.x cannot run on JDK 25) and extra JDKs in `/usr/lib/jvm`, which Gradle auto-detects | Validate any resolution image with a Gradle-version Ã— toolchain matrix |
| Gradle < 7.3 is not supported; it fails with `Unsupported class file major version 61` | The project upgrades its wrapper |
| The resolver runs `dependencies`, `projects` and `properties` on every subproject | Builds that guard missing files by task name must include these tasks |
| Gradle `Java heap space` during resolution | `GRADLE_CLI_OPTS: "-Dorg.gradle.jvmargs=-Xmx2g"` (still honoured by v2) |
| Nested builds (a `settings.gradle`/`gradlew` not at the root) fail with "Project with path â€¦ could not be found" or a missing `GradleWrapperMain` | Project-side fix, or `DS_EXCLUDED_PATHS` |
| Builds needing uncommitted local files (`local.properties`, secrets files) fail | The project provides CI-safe defaults |
| Direct Maven Central access gets **HTTP 429** under load | Route through the internal proxy |
| Python resolution runs `pip-compile`, which **ignores `[tool.uv]` indexes** | Pin `PIP_INDEX_URL` to an internal superset index as a policy variable |
| A committed `uv.lock` or `poetry.lock` is used directly, with no resolution | Recommend lockfiles |
| Absolute paths in `-c constraints.txt` fail in the resolver container (analyzer `FATA`) | Project-side fix |
| `expected pip-compile lock file but found plain manifest` is logged as a parsing warning, not necessarily the failure | Look further for the real error before acting on it |
| `pip-compile` runs with `--all-extras --no-emit-index-url`; `git+` URLs and packages needing native builds can fail | Project fix, or a path exception |
| A transient sidecar error, "`.gitlab_ds/dependency_resolution.sh` not found after 60 seconds" | Retry. Investigate if it persists |
| `GRADLE_CLI_OPTS` and `MAVEN_CLI_OPTS` still apply (`MAVEN_ARGS` defaults to `MAVEN_CLI_OPTS`). `DS_JAVA_VERSION` is ignored | Older docs are misleading |
| The CycloneDX upload is limited by plan limit `ci_max_artifact_size_cyclonedx` (added in 19.3, default 1 MB; `0` means "use the max artifact size"; the smaller of the two applies). Large multi-module SBOMs hit `413 Payload Too Large`, so the job fails and **nothing is ingested** | An instance admin raises it in Admin â†’ CI/CD limits or via the Rails console. On 19.4 the plan limits REST API silently drops this parameter. Compression is large: 16.5 MB of SBOMs uploaded as 1.3 MB |
| The Gradle resolution job runs in `.pre`, delaying stage-ordered project jobs; `needs: []` or DAG scheduling can bypass ordinary stage waits. In one Android MR pipeline it took 899 s before `build` jobs could start. With resolution disabled and the graph generated in the build job, build, test and lint started within about 5 s (*measured*, 19.4.5) | For large Gradle builds, generate `gradle.graph.txt` in the project's existing build job and disable the resolution job (`DS_DISABLED_RESOLUTION_JOBS: gradle`). GitLab recommends this ("Create lockfile or dependency graph export manually") because it reuses the build's daemon, cache and resolved configuration, and can improve dependency fidelity when the exported configurations cover the intended scan scope |
| An unqualified root `dependencies` task does not guarantee reports for every subproject or included build (*inferred* from Gradle behaviour) | For multi-module builds, register a `DependencyReportTask` per project with an init script that writes `gradle.graph.txt` in each module directory, and collect `**/gradle.graph.txt`. Run included builds (`-p <dir>`) separately. Fail the producer if any expected module graph is missing, empty, unresolved or lacks representative dependencies. `test -s` on one root graph alone does not prove multi-module coverage |
| In the supplied SEP pipeline, `dependency-scanning` used normal earlier-stage artifact downloads (*measured*); inspect effective `needs`/`dependencies` and artifact expiry | For this artifact-download configuration, the graph-producing job must run in a stage **before** the scan stage (`test`, or `scan-policies` after `build`). If neither `test` nor `build` exists, `scan-policies` is injected first and a later graph producer cannot supply it |
| If the policy does not lock `DS_DISABLED_RESOLUTION_JOBS`, a project can change it (*inferred from variable precedence*) | A project can disable resolution and silently fall back to direct dependencies. Compare component sets, transitive dependencies and findings identities before and after; equal counts alone do not prove coverage. Accept it only where the project produces the graph itself |
| Setting `DS_DISABLED_RESOLUTION_JOBS` only for MR pipelines, through `workflow:rules:variables`, keeps GitLab resolution on the default branch (*measured*) | Use this when only MR pipelines build the graph, so default-branch coverage does not depend on that job |

Moving graph generation into a build job still executes untrusted build tooling. It does
not make platform secrets safe there. For a worked canary checklist, use
[dependency-resolution](../playbooks/dependency-resolution.md#graph-in-the-build-job).


## Reports and UI


- The MR security widget shows only a **limited number of findings** (25 observed). The full set
 is in the pipeline Security tab.
- Dependency findings are reported **per module manifest**. One CVE in a shared library appears
 once per module.
- Dependency scanning reports every resolved configuration, including test, lint, debug and
 annotation-processor classpaths. In Android apps, most findings typically come from test and
 lint tooling, not from the shipped release classpath. Classify findings by configuration
 before judging the noise.
- The analyzer treats only configurations named `test*`/`androidTest*` as development, so
 Android variant test configurations count as production, and
 `DS_INCLUDE_DEV_DEPENDENCIES=false` does not help. A possible workaround (*untested*): disable
 Gradle resolution for the project and commit a CI-generated runtime-classpath
 `gradle.graph.txt`.
- SCA (dependency scanning) and SAST answer different questions. Comparing counts with SonarQube
 or a mobile-binary scanner is not a validity test.


## DAST


- A scan execution policy `dast` action uses on-demand profiles, and active scans need a
 validated site profile. Without one, the job was created with no runner tags and sat pending
 forever.
- In a pipeline execution schedule policy, the DAST job runs as the Security Policy Bot and
 appears only in `pipeline_execution_policy_schedule` pipelines.
- `variables_override: {allowed: false}` blocked a hostile project-level `DAST_TARGET_URL`. This
 was measured.
- `tagList` on DAST scanner profiles is accepted and silently discarded (19.2).


## Limits


See [policy-authoring Â§ Limits](policy-authoring.md#limits). GitLab ignores anything over a limit
without reporting an error.
