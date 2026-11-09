# Blueprint: building the platform from scratch


This is the reference design a production code-quality platform converged on after adversarial
validation and an estate-wide rollout. Build in the phase order at the end. **One prompt cannot
build it**: every phase has a proof and a stop point, and a later phase relies on artifacts
(baseline, releases, pilots) produced by earlier ones.


## 1. Design principles


1. **One public API.** A single façade component (`codequality`) is the only thing consumers
  include. It declares every consumer-facing input once, documents it, and forwards it to internal
  templates. Wrapper components (language/build pipelines) forward inputs unchanged and are tested
  for it. Internal templates are not a public contract.
2. **One decision point.** Analyzers publish; the summary aggregates; only the gate decides. The
  gate reads the summary and never recomputes a metric, so the JSON, the job log, the MR widget
  and the decision cannot disagree.
3. **Evidence or failure.** Absence of evidence (no manifest, no report, no diff, no baseline) is
  never read as "clean". Each absence has an explicit status with a defined gate effect.
4. **Policy failure ≠ platform failure.** Threshold violations obey the gate mode; configuration
  and analyzer-health errors fail the gate in every mode, including `report`.
5. **New code first.** Gates target new findings and changed-line metrics against a baseline, so
  legacy estates can adopt the platform without a cleanup project. Overall metrics are observation
  first.
6. **Native platform features first.** GitLab Code Quality report, coverage annotations, coverage
  widget and job artifacts as the baseline store: no database, no server, no custom UI.
7. **Pinned, verified, mirrored.** Every executable download is version-pinned, checksum-verified
  and fetched through the organisation's artifact proxy. Runtime packages come from lockfiles with
  integrity hashes.
8. **Centrally governed profiles, narrow exceptions.** Project analyzer config files never replace
  the shared profile; suppressions are auditable entries with owner and reason.
9. **Selective and cheap.** Jobs exist only when matching sources exist; source-only analyzers start
  with `needs: []`.
10. **Simplest correct implementation.** Native capability → approved library → small stdlib code →
   custom framework. Remove capability and duplication rather than weaken validation.
11. **Migration-safe defaults.** Default gate mode `report`; enforcement is opt-in per project once
   owners approve thresholds.


## 2. Public API: the façade


Group inputs so the surface stays readable. Names below are the proven set; keep the naming
convention even if the analyzers differ.


| Group | Inputs |
|---|---|
| Platform / execution | `<registry>_host`, registry repository names (docker, generic, npm, pypi, github-remote), `job_stage`, `job_prefix`, `runner_tags`, `job_artifacts_expiration` (short, diagnostics), `baseline_artifacts_expiration` (long, the baseline), `job_report_image`, `job_git_python_image` (must contain `git`) |
| Profiles | `codequality_profile_version` (literal, bumped by release), `codequality_profile_path` (profile development only), `job_profiles_image`, `profile` (options list, e.g. `standard`) |
| Analyzer selection | `enable_<analyzer>` per analyzer and `enable_<language>_cpd` per language; `enable_mr_pipelines` |
| Sources | `<language>_source_paths`, `cpd_minimum_tokens`, `cpd_excluded_path_patterns`, language-specific CPD excludes |
| Supply chain | `<tool>_version`, `<tool>_archive_sha256`, `job_<tool>_image` per analyzer |
| Build artifacts | `<bytecode-analyzer>_bytecode_job_name`, `_class_paths`, `_aux_classpath`, `_compile_command`; `coverage_job_name`, `coverage_report_path` (recursive glob allowed), `coverage_format` (`jacoco`/`lcov`) |
| Exceptions | `project_exceptions_file` (default `.codequality-exceptions.json`) |
| Gate | see §3 |


Rules:


- Types are explicit (`boolean`, `number`, `array`, `string` with `options`).
- GitLab has no nullable number input; optional thresholds are strict numeric strings where empty
 means "not evaluated".
- Never derive one input from another through `rules:`-conditional inputs; reference root inputs
 directly (chaining is unreliable).
- Kill switch: a CI variable (for example `CODE_QUALITY_DISABLED`) suppresses every generated job.
- Producer job names are inputs, and `needs:` on consumer jobs is `optional: true`; a missing
 artifact fails *inside* the job with an actionable message, never at pipeline creation.


## 3. Quality Gate API


| Input | Default | Meaning |
|---|---|---|
| `quality_gate_mode` | `report` | `report` (publish verdict, job passes), `block` (gate job fails on violation), `disabled` |
| `max_new_blocker` / `max_new_critical` / `max_new_major` | `0` | New findings per severity vs baseline |
| `minimum_new_code_coverage` | `80` | Coverage of changed executable code |
| `maximum_new_code_duplication_percent` | `3` | Duplicated lines among changed lines |
| `minimum_coverage` | empty | Overall coverage (observation first) |
| `maximum_overall_coverage_drop` | empty | Percentage-point fall vs baseline |
| `maximum_duplication_percent` | empty | Overall duplication |


Per-criterion outcome: `passed`, `failed`, or `skipped` with a reason (`not_applicable`,
`no_covered_executable_lines`, `baseline_missing`). `unavailable` → failed in block mode.
Complexity is enforced through finding severity in the profile, not as an aggregate gate input,
because analyzers do not expose a reliable aggregate.


Gate log format (keep it stable; support and scripts parse it):


```text
Quality Gate FAILED (block mode)
- minimum_new_code_coverage: 42.1 is below 80
- max_new_major: 3 exceeds 0
    + pmd PMD/RuleName src/main/java/A.java:12      # up to 20 offending new findings
- maximum_new_code_duplication_percent: metric is unavailable
- SKIPPED maximum_overall_coverage_drop: baseline_missing
- CONFIGURATION ERROR analyzer health: <analyzer error>
```


The gate also writes `quality-gate.json`: `schema_version`, `mode`, `status`, `violations`,
`skipped`, `configuration_errors`, `baseline_status`, `analyzers` (name → status), `thresholds`.
Configuration errors exit non-zero before the mode is consulted.


## 4. Job topology


```text
pipeline start ──► source-only analyzers (needs: [])            → scan + report jobs
profiles job ───► analyzers needing installed rule runtimes
build/test ─────► bytecode analyzer, coverage bridge (optional needs on consumer jobs)
all reports ────► <prefix>:summary ──► <prefix>:quality-gate
```


- Job names: `<prefix>:<analyzer>:scan`, `<prefix>:<analyzer>:report`, `<prefix>:profiles`,
 `<prefix>:coverage`, `<prefix>:summary`, `<prefix>:quality-gate`.
- The summary `needs:` each enabled report job, so disabling an analyzer removes a job rather than
 breaking the DAG.
- Only the summary publishes the GitLab Code Quality report, **after exceptions are applied**, so
 the MR widget shows exactly what the gate counts.
- Rules per job: kill switch → MR (`merge_request_event`, if MR pipelines enabled) → child/
 multi-project (`parent_pipeline`, `pipeline`) → suppress branch pipeline when an MR is open →
 branch; each with a literal `exists:` glob identical to the summary's health source pattern.


## 5. Schemas (versioned internal contracts)


**Scan manifest** `analyzer-scan-<name>.json`, written only after the analyzer exits 0:


```json
{"schema_version": 1, "analyzer": "pmd", "version": "7.x", "status": "succeeded",
"files_analyzed": 123, "findings": 7}
```


The report job adds `report` path and finding count → `quality-analyzer-<name>.json`.
Optional: `analysis_mode: degraded` when the analyzer ran with reduced capability (for example a
bytecode analyzer without the dependency classpath) so it is visible, not silent.


**Analyzer health** (computed by the summary from manifests + `enable_*` + source detection):


| Status | Meaning | Gate effect |
|---|---|---|
| `succeeded` | ran to completion; `findings: 0` is a real clean result | none |
| `skipped` | enabled, no matching sources (or all excluded by profile) | none |
| `disabled` | turned off by input | none |
| `report_missing` | ran, but its report is absent | configuration error |
| `manifest_malformed` | manifest unparsable | configuration error |
| `no_health_evidence` | enabled, sources exist, no manifest | configuration error |


**Summary** `quality-summary.json` (also the baseline):


```json
{
 "schema_version": 1, "fingerprint_schema": 1, "profile": "standard",
 "baseline": {"status": "available|missing", "ref": "main"},
 "codequality_report": {"scope": "all|new", "reason": "..."},
 "findings": {"total": {"blocker": 0, "critical": 0, "major": 0, "minor": 0, "info": 0},
              "new": {}, "existing": {}, "resolved": 0,
              "raw_count": 0, "effective_count": 0, "items": [], "new_items": []},
 "changed_lines_status": "available|unavailable:<reason>",
 "coverage": {"status": "", "metric": "instructions|lines", "overall_percent": 0,
              "baseline_overall_percent": 0, "overall_percent_drop": 0, "overall_drop_status": "",
              "new_code_percent": 0, "new_code_status": ""},
 "duplication": {"status": "", "overall_percent": 0, "new_code_percent": 0, "new_code_status": ""},
 "exceptions": {"applied": [], "expired_ignored": [], "disabled_overrides": [], "invalid": []},
 "analyzers": {}, "analyzer_errors": []
}
```


**Finding** (GitLab Code Quality / CodeClimate shape): `description`, `check_name`, `engine_name`,
`severity` (`blocker|critical|major|minor|info`), `fingerprint`, `location.path`,
`location.lines.begin`.


**Fingerprint v1**: `sha256("v1" | analyzer | rule | repo-relative path | normalized source
context)`. **No line numbers** (moving code must not create "new" findings). Identical siblings are
ordered by path, line, rule and later occurrences get an ordinal salt. Fallback when source is
unreadable: normalized message or duplication metadata. Bump `fingerprint_schema` on any change and
treat an incompatible baseline as missing.


**Exceptions** (global file in the platform repo, local file in the project):


```json
{"schema_version": 1, "exceptions": [{
 "key": "unique", "reason": "why", "owner": "team",
 "analyzer": "pmd", "rule": "PMD/Rule", "path": "glob/**", "fingerprint": "…",
 "expires": "YYYY-MM-DD", "enabled": true}]}
```


`key`, `reason`, `owner` + ≥1 selector required; selectors AND-combined; project key overrides
global key; `enabled: false` restores; expired entries stop applying; invalid/duplicate → config
error in every mode; no-match is silent.


## 6. Baseline and new code


| Pipeline | Baseline summary from | Changed lines diff base |
|---|---|---|
| MR | latest successful target-branch pipeline | `CI_MERGE_REQUEST_DIFF_BASE_SHA` |
| Default **or any protected** branch push | that branch's own latest successful pipeline | `HEAD^` |
| Other branch | latest successful default-branch pipeline | `origin/$CI_DEFAULT_BRANCH` |


- Baseline is an ordinary job artifact retained for `baseline_artifacts_expiration`; fetch it with a
 maintained API client (pinned).
- Missing baseline: nothing classified new; baseline-dependent criteria `SKIPPED baseline_missing`;
 the next branch pipeline recreates it. Never treat as "no new findings".
- Missing git object → metric `unavailable:<reason>` (`no_merge_base`, `git_missing`,
 `base_unreachable`, `diff_failed`), never guessed. Empty MR diff: fall back to
 `CI_MERGE_REQUEST_TARGET_BRANCH_SHA`.
- Relevant change: only production sources count. Test source sets, build scripts and config → the
 criterion is `not_applicable`. Changed production lines with no executable code →
 `no_covered_executable_lines`.
- When GitLab's MR base pipeline was skipped (`[skip ci]` release commits), publish only new
 findings so the widget does not label everything new; record `codequality_report.scope`.
- Print `Findings against <ref>: N new, M existing, K resolved` and list new findings in the
 summary log — developers read logs before widgets.


## 7. Coverage


- The platform never runs tests. A build-side producer job emits the coverage report (JaCoCo/Kover
 XML or LCOV) and compiled classes; the platform consumes them by job name.
- Coverage bridge validates the report (fails when the glob matches nothing, records are malformed,
 or no source files exist) and publishes `artifacts:reports:coverage_report` for diff annotations;
 LCOV is converted to Cobertura for GitLab.
- Summary prints one anchored line, e.g. `<Org> overall instruction coverage: 83.32%`, and the job's
 `coverage:` regex matches only that line — widget and JSON cannot disagree.
- Metric is consistent per format (`instructions` for JaCoCo, `lines` for LCOV); drop is computed
 only against a baseline with the same metric.
- Multi-module: recursive glob, aggregate counters across reports.


## 8. Profiles


- `profiles/` in the platform repo is the single editable source: per-language rule files, global
 exceptions, version file.
- Released as one deterministic, immutable bundle (sorted members, normalized metadata, zero
 timestamps) to a generic registry repo under `<name>/<version>/…tar.gz`; **bundle version =
 component version**, kept as one literal that the release tool bumps.
- `publish` refuses to overwrite a version with different bytes; an MR check fails if `profiles/`
 differs from the published bundle of the pinned version.
- One `profiles` job downloads, asserts every expected file exists and is non-empty (silent
 fallback to analyzer defaults reports *fewer* findings and looks like an improvement), and shares
 it as an artifact.
- Executable files in the bundle are allow-listed by exact path.
- `codequality_profile_path` swaps in a checkout's `profiles/` tree, for self-test and dedicated
 variants only.


## 9. Repository layout


```text
templates/        codequality.yml (façade) + one template per concern
profiles/         canonical rules + global-exceptions.json + VERSION
scripts/          canonical reference module, bundle tool, structural verifier
tests/            unit, embedded-script execution, adversarial, mutation-style
test-projects/    fixture projects run as child pipelines against profiles/
docs/             per-language guides, diagrams
README.md         full input and contract reference (source of truth for docs elsewhere)
```


Platform CI: `test:platform-contracts` (unit + structural verifier), `test:profiles` (bundle
determinism/immutability), `trigger:<language>-code-quality` fixture child pipelines,
`publish:profiles` and release on the default branch only, publish before tag.


## 10. Build order (phases with stop points)


| # | Phase | Exit proof |
|---|---|---|
| 0 | Intake + design record (§1–§3 decisions, languages, registry, runner tags) | User agrees API and defaults |
| 1 | Façade + one analyzer end to end (scan → report → summary → gate) + schemas | Unit tests incl. missing-manifest fail-closed |
| 2 | Structural verifier + embedded-script execution tests | Mutations of templates fail the suite |
| 3 | Remaining analyzers, CPD, fingerprints | Fixture child pipelines green per language |
| 4 | Profiles bundle + publish/immutability + exceptions | `test:profiles`, exception probes |
| 5 | Coverage bridge + native visualization | Widget value equals summary value |
| 6 | Baseline lifecycle on the default branch (**user merges**) | Controlled MR shows correct new/existing/resolved; moving code yields 0 new |
| 7 | Release automation, then wrapper-component integration MR | Wrapper forwards every input; release publishes bundle before tag |
| 8 | Pilots in `report` mode via unmerged MRs; noise review; profile tuning with evidence | Findings reviewed per rule; false-red classes fixed |
| 9 | Waves, `block` per team, support playbooks, docs | Survey of failures per wave |
