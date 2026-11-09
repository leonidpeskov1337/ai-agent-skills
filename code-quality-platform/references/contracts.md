# Contracts


Behavioural contracts a code-quality platform must hold. Each has a *why* (the failure it
prevents) and a *test* expectation.


## 1. Analyzer execution health


- The scan job writes `analyzer-scan-<name>.json` (`schema_version`, `analyzer`, `version`,
 `status: succeeded`, `files_analyzed`, `findings`) **only after the analyzer exits 0**. A crash
 therefore leaves no manifest. The report job adds the report path → `quality-analyzer-<name>.json`.
- The summary derives health per analyzer:


 | Status | Meaning | Gate |
 |---|---|---|
 | `succeeded` | ran; `findings: 0` is a real clean result | — |
 | `skipped` | no matching sources, or all excluded (`reason: no_eligible_sources`) | — |
 | `disabled` | turned off by input | — |
 | `report_missing` | manifest present, report absent | config error, every mode |
 | `manifest_malformed` | manifest unparsable | config error, every mode |
 | `no_health_evidence` | enabled, sources exist, no manifest | config error, every mode |


- Optional `analysis_mode: degraded` (for example bytecode analysis without dependency classpath)
 is shown, never hidden.
- The summary's source-detection glob and the job's `rules:exists` glob must be identical.
- *Why:* an analyzer that crashed and one that found nothing must not both show "0 issues".
- *Test:* delete a manifest → `no_health_evidence` → gate exits non-zero even in report mode.


## 2. Gate semantics


Per metric the gate sees a status and a value:


| Status | Meaning | Block-mode result |
|---|---|---|
| available | measured | compare to threshold |
| `not_applicable` | no relevant change (for example no analyzable production source changed) | pass, shown `SKIPPED … not_applicable` |
| `no_covered_executable_lines` | changed code has nothing measurable | pass |
| `unavailable` | could not measure (no diff, no coverage data for changed files) | **fail**: `<metric>: metric is unavailable` |
| baseline missing | `max_new_*` and `maximum_overall_coverage_drop` cannot compare | pass, shown `SKIPPED … baseline_missing` |


- `report` mode: verdict published (summary, MR widget, job log), job succeeds.
- `block` mode: only the gate job fails; analyzers stay green.
- Configuration errors (invalid exception, invalid threshold) and analyzer-health failures fail
 the gate in **every** mode (`- CONFIGURATION ERROR …`).
- A missing baseline classifies nothing as new; it is never "zero new findings".
- LCOV: a changed file absent from the tracefile is `not_applicable` (outside the runner's
 coverage scope). JaCoCo: a changed production source absent from the report is `unavailable`.
- Only production sources are relevant (test source sets, build scripts and config are not).
- Log lines worth recognising: `Quality Gate PASSED|FAILED (<mode> mode)`,
 `- <metric>: <value> is below <threshold>`, `- <metric>: <value> exceeds <threshold>`,
 `- <metric>: metric is unavailable`, `- SKIPPED <metric>: not_applicable`.
- *Why:* "could not measure" passing silently is the classic false green; "nothing changed" failing
 is the classic blocker for config/version-only MRs.


## 3. Baseline and new-code


- New code = findings/lines present now but not in the baseline, and changed lines for coverage
 and duplication.
- **MR pipeline:** baseline = the MR's *target branch* summary; diff base =
 `CI_MERGE_REQUEST_DIFF_BASE_SHA`.
- **Protected/default branch push:** baseline = that branch's *own* previous summary; diff =
 `HEAD^..HEAD`. Do **not** use the project default branch blindly: many projects have a default
 branch (`develop`) that differs from the release/protected branch (`master`/`main`). Comparing a
 `master` push with `develop` counts the entire develop→master delta as new code, so already
 reviewed code appears with 0% coverage or many "new" issues.
- **Empty MR diff:** if an MR's net diff is empty (for example two commits that revert each other),
 GitLab leaves `CI_MERGE_REQUEST_DIFF_BASE_SHA` empty and the diff is
 `unavailable:no_merge_base`. A robust platform falls back to the target-branch SHA so the result
 is `not_applicable`, not fail-closed.
- Diff failure reasons are explicit statuses (`unavailable:no_merge_base`, `git_missing`,
 `base_unreachable`, `diff_failed`) so the gate message is diagnosable.
- Baseline artifact retrieval must use the project's job/artifact API with proper error handling
 (prefer a maintained client library over hand-rolled redirects and token forwarding).
- *Test:* env-var matrix per context in a unit test; assert baseline ref and diff command.


## 4. Fingerprints


- v1 = `sha256("v1" | analyzer | rule | repo-relative path | normalized source context)`.
 **No line numbers**: moving code must not make findings "new".
- Fallback when source is unreadable: normalized message, or duplication metadata for CPD.
- Identical siblings: sort by path, line, rule; later occurrences get an ordinal salt. Known limit:
 when one of several identical siblings is removed, the platform cannot tell which.
- The summary records `fingerprint_schema`; a change of algorithm bumps it.
- *Test:* rerun → identical; insert lines above → same fingerprint; two identical siblings →
 distinct.


## 5. Selective execution


- Every analyzer rules block: kill-switch first, then MR (`merge_request_event`), parent/downstream
 (`parent_pipeline`/`pipeline`), branch push — each with a literal `exists:` glob; skip branch
 pipelines when an MR is open to avoid duplicates.
- A shared multi-language template needs one rule per language per context; `exists:` cannot be
 built from an input.


## 6. Exceptions


- Selectors AND-combined (analyzer, rule glob, path glob, fingerprint); mandatory `key`, `reason`,
 `owner`; optional `expires`. Project entry with the same key overrides global; `enabled: false`
 restores a finding.
- Invalid entries and duplicate keys are configuration errors (gate fails in every mode); a selector
 matching nothing is silent (finding stays visible).
- Excepted findings leave gate counts and the published report but are listed in the summary
 (`exceptions.applied`); an excepted baseline finding counts as resolved.


## 7. Severity normalization


One documented table per analyzer mapping native severities to the five platform severities
(blocker, critical, major, minor, info). Duplication blocks have a fixed severity. Changing a
mapping is a breaking change for gates keyed on severity counts.


## 8. Supply chain


Pinned version + archive checksum per download; fetched via the organisation's artifact proxy;
checksum verified before execution; image tags pinned.
