# Analyzer onboarding checklist


Prerequisite: read the live composition root, the summary's analyzer registry/health/`has_sources`
logic, the closest existing analyzer template, and the tests that encode the contracts. The repo
wins over this checklist.


## 1. Classify


- Language and file extensions (drive `exists:` globs and `has_sources()`).
- Distribution: static binary, JVM jar, or package-manager tool (flag the last explicitly).
- Native report: CodeClimate JSON, SARIF, own XML/JSON, text → decides converter size.
- Needs build output (bytecode, compiled classes)? Add a `*_job_name` input; consume the existing
 build job's artifacts, never recompile.
- Duplication support: check whether the existing CPD tool supports the language first.
- Severity mapping to the five platform severities, written as an explicit map.


## 2. Template (self-contained)


- Inputs mirror existing naming: registry host/repos, stage, prefix, image, `<tool>_version`,
 `<tool>_archive_sha256`, report image, artifact expiry, runner tags, source paths, profile,
 `enable_mr_pipelines`.
- Jobs: `…:rules` (hidden) → `…:scan` (pinned download + `sha256sum -c`, run with the shared
 profile, write raw report + scan manifest with a *real* `files_analyzed` count) → `…:report`
 (normalize, severity map, fingerprint, fold manifest into the health file).
- Diagnostics artifacts `when: always`; the manifest exists only on success. Only the summary
 publishes `reports: codequality:`.


## 3. Wire


1. Root input `enable_<x>` (new/unproven analyzers may default off until a pilot validates them).
2. Root source-path and version/checksum inputs (re-declared leaf inputs are intentional).
3. `include:` entry gated on the toggle.
4. Summary: registry entry, `needs:` (optional), `has_sources()` pattern in lockstep with the rules.
5. Gate and docs: threshold names unchanged unless deliberate; README analyzer + severity tables.


## 4. Profile


Add the language profile to the shared bundle (see
[profiles-and-exceptions](profiles-and-exceptions.md)); the bundle's required-file check must list
it so a missing file is a loud failure, not a silent default.


## 5. Tests (prove no false green)


- Manifest missing while sources exist → `no_health_evidence`, gate exits non-zero in every mode.
- Report missing → `report_missing`; malformed manifest → `manifest_malformed`.
- Analyzer ran clean → `succeeded`, 0 findings, gate passes.
- No matching sources → `skipped`, no error.
- Fingerprint stability and sibling uniqueness.
- Selective execution: rules fixture or `verify` tooling confirms the job is absent without
 sources.
- Converter edge cases: empty report, malformed report, missing severity.


## 6. Prove and pilot


Unit tests + component verification, then the platform repo's own pipeline with fixture projects,
then a consumer pilot through an unmerged MR in `report` mode. Review pilot findings for noise
before anyone is blocked.
