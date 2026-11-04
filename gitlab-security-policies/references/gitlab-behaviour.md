# GitLab behaviour: verified facts and traps


Unless a row says otherwise, everything here was **measured** on GitLab EE 19.2–19.4
(self-managed). Behaviour changes between minor releases. Before relying on a row:


- re-check it on the running version;
- read the release notes for the versions in between.


Mark each claim in reports as *verified here*, *documented* or *inferred*.


## Contents


1. [Policy loading and propagation](#policy-loading-and-propagation)
2. [Scope and linking](#scope-and-linking)
3. [Pipelines and jobs](#pipelines-and-jobs)
4. [Gates and approvals](#gates-and-approvals)
5. [Vulnerability lifecycle](#vulnerability-lifecycle)
6. [Dependency scanning v2](#dependency-scanning-v2)
7. [Reports and UI](#reports-and-ui)
8. [DAST](#dast)
9. [Limits](#limits)


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
| An MR rule with `branch_type: target_default` left MRs into non-default branches (GitFlow `feature/* → develop`) unscanned in production, while a sandbox did not reproduce it | Use `branch_type: all` for MR rules; it is correct under either reading |
| Pipelines created through the API (`POST /projects/:id/pipeline`) got no policy jobs under push/MR rules, and the call returns `400 Missing CI config file` without a `.gitlab-ci.yml` | Test policies with real pushes and MRs |
| Policy jobs carry only the policy's `tags` | If no runner accepts untagged jobs, an untagged policy job stays `pending` forever ("no runners online") |
| Policy variables override project and group variables for policy jobs, and only variables the policy sets are locked. The job log line "User-defined CI/CD variables are allowed … (except for X, Y)" lists the locked set | Set every security-relevant knob in the policy. Unset knobs (`DS_DISABLED_RESOLUTION_JOBS`, `MAVEN_ARGS`, `GRADLE_OPTS`, `JAVA_TOOL_OPTIONS`) remain project-controllable |
| Precedence: policy variables (locked) > project CI/CD settings variables > template job-level variables (for example `DS_*_RESOLUTION_IMAGE`) > top-level `variables:` in the project's `.gitlab-ci.yml`. Top-level variables **do** reach policy jobs but lose to template job-level defaults. They still apply to anything the template leaves unset, such as `KUBERNETES_MEMORY_LIMIT` | Tell projects to use CI/CD settings variables for supported workarounds. Set resource variables in the policy if the platform owns sizing |
| A scan execution policy cannot set `retry` or `allow_failure: false` on its jobs | Transient failures need a manual retry. Detect failures by survey, not by pipeline status |
| `FAIL_NEVER=true` (and similar) turns a failing analyzer into a green job with no report | Never use it to quiet failures; it hides coverage loss |
| GitLab pre-sets `*_EXCLUDED_PATHS` on policy-enforced projects. Only a policy can override them | Path exceptions need a policy-level variable, usually via a per-project override policy project |
| A missing prerequisite makes most scanners skip quietly. **Container scanning fails** (`gl-container-scanning-report.json: no matching files`) | Make container scanning opt-in per image-building group |
| `AST_ENABLE_MR_PIPELINES` is needed for analyzers to run in MR pipelines | Set it as a policy variable |
| Including security templates in the project as well as the policy produces duplicate jobs | Harmless for enforcement. Ask projects to remove the local includes |
| Repository rulesets (`.gitlab/sast-ruleset.toml`, gitleaks config) suppress findings before the gate sees them | Not closed by default. A locked policy variable `SECURE_ENABLE_LOCAL_CONFIGURATION: "false"` should close it (*unverified*); otherwise CODEOWNERS and review |
| A wrapper committed without the exec bit (`100644`) fails with `fork/exec …/gradlew: permission denied` in **`spotbugs-sast`**, which executes `gradlew` directly. It is triggered by Groovy, Scala or Kotlin sources. DS v2 Gradle resolution runs `sh ./gradlew` and is unaffected (19.4) | Project fix: `git update-index --chmod=+x gradlew` (beware `core.fileMode` reverting it on `commit -a`). Do not run analyzers privileged or chmod runner-wide |
| SpotBugs (Java SAST fallback) compiles the project by running `gradlew`/`mvn`, so build problems surface as SAST failures | Treat as a build issue; `COMPILE` and `SAST_JAVA_VERSION` affect only SpotBugs |
| Some analyzers (Advanced SAST) size worker counts from node CPUs, not the pod's cgroup, and OOM on small pods. Advanced SAST starts up to 3 `lightz` workers. Each gets `-max_memory` equal to the **whole** detected memory, and GitLab documents at least 4 GB per worker | Set `ADVANCED_SAST_AVAILABLE_CPUS` and `ADVANCED_SAST_AVAILABLE_MEMORY` in the policy, together with `KUBERNETES_MEMORY_LIMIT` ≥ workers × 4 GB. The job log should show "Overriding the detected CPU amount" and `MemoryLimit overwritten` |
| KICS (IaC) file-reference resolution and timeouts, reported on GitLab EE 19.4, analyzer 6.13.0 / KICS 2.1.20 | YAML/JSON references into repository files and downloaded artifacts expanded a monorepo scan from 3.7 GB to 14 GB peak, exceeding an 8Gi pod limit. The supplied canary used `KICS_MAX_RESOLVER_DEPTH: "0"` and reported 9,775 identical rule/file/line findings, 0.5 GB peak and 69 s versus 458 s. Depth 1 still peaked at 8.9 GB. Check the effective variable mapping on the installed analyzer and compare coverage before adoption. In this case `.gitignore`, `SAST_EXCLUDED_PATHS` and worker reductions did not resolve the expansion. Query timeouts also dropped findings. Evaluate `KICS_TIMEOUT: "300"` with completion and job-budget evidence. |

The supplied KICS build used Go 1.25 and logged `CPU: 4.0` under a four-CPU pod
limit. Verify runtime and worker overrides on the installed build. Its `Total memory`
log described the node. Use the runner override and actual cgroup limit for sizing.
In that reproduction, 4/8/16 workers used 3.6/3.8/4.1 GB, making resolver expansion
the more discriminating test. These are attributed incident observations.


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
   - advisories use `CVE-…`, `GHSA-…` or `Gemnasium-<uuid>`.
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
| A Gradle settings plugin requiring JVM 21 or 25 fails while the daemon runs an older JDK | The project adds `gradle/gradle-daemon-jvm.properties` with `toolchainVersion=<N>`. Daemon toolchains need a committed wrapper of Gradle ≥ 8.8, and ≥ 9.1 for JDK 25 |
| A multi-JDK resolution image works best with the daemon on JDK 17 (runs Gradle 7.3–9.x; Gradle 8.x cannot run on JDK 25) and extra JDKs in `/usr/lib/jvm`, which Gradle auto-detects | Validate any resolution image with a Gradle-version × toolchain matrix |
| Gradle < 7.3 is not supported; it fails with `Unsupported class file major version 61` | The project upgrades its wrapper |
| The resolver runs `dependencies`, `projects` and `properties` on every subproject | Builds that guard missing files by task name must include these tasks |
| Gradle `Java heap space` during resolution | `GRADLE_CLI_OPTS: "-Dorg.gradle.jvmargs=-Xmx2g"` (still honoured by v2) |
| Nested builds (a `settings.gradle`/`gradlew` not at the root) fail with "Project with path … could not be found" or a missing `GradleWrapperMain` | Project-side fix, or `DS_EXCLUDED_PATHS` |
| Builds needing uncommitted local files (`local.properties`, secrets files) fail | The project provides CI-safe defaults |
| Direct Maven Central access gets **HTTP 429** under load | Route through the internal proxy |
| Python resolution runs `pip-compile`, which **ignores `[tool.uv]` indexes** | Pin `PIP_INDEX_URL` to an internal superset index as a policy variable |
| A committed `uv.lock` or `poetry.lock` is used directly, with no resolution | Recommend lockfiles |
| Absolute paths in `-c constraints.txt` fail in the resolver container (analyzer `FATA`) | Project-side fix |
| `expected pip-compile lock file but found plain manifest` is logged as a parsing warning, not necessarily the failure | Look further for the real error before acting on it |
| `pip-compile` runs with `--all-extras --no-emit-index-url`; `git+` URLs and packages needing native builds can fail | Project fix, or a path exception |
| A transient sidecar error, "`.gitlab_ds/dependency_resolution.sh` not found after 60 seconds" | Retry. Investigate if it persists |
| `GRADLE_CLI_OPTS` and `MAVEN_CLI_OPTS` still apply (`MAVEN_ARGS` defaults to `MAVEN_CLI_OPTS`). `DS_JAVA_VERSION` is ignored | Older docs are misleading |
| The CycloneDX upload is limited by plan limit `ci_max_artifact_size_cyclonedx` (added in 19.3, default 1 MB; `0` means "use the max artifact size"; the smaller of the two applies). Large multi-module SBOMs hit `413 Payload Too Large`, so the job fails and **nothing is ingested** | An instance admin raises it in Admin → CI/CD limits or via the Rails console. On 19.4 the plan limits REST API silently drops this parameter. Compression is large: 16.5 MB of SBOMs uploaded as 1.3 MB |


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


See [policy-authoring § Limits](policy-authoring.md#limits). GitLab ignores anything over a limit
without reporting an error.
