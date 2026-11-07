# CI maintainability audit

## Final refinement — 2026-11-08

Initial inspection confirmed active native ruleset 26754711, no bypass actors and
the required Validation gate. The latest successful main CI was run 42418062515;
manual recovery run 42418211562 also passed. The published v1.0.0 release and asset
IDs were captured for post-change comparison. This pass does not modify GitHub
settings, merge its own PR, or publish synthetic releases.

The current Anthropic Skill Creator source is still commit
2c5958ecac7cee2b583967a2c4981d0f4a75c579, matching the vendored validator. Its packager
was inspected again: it walks arbitrary files and excludes evals/caches, but lacks
our deterministic metadata, size bounds, payload-reference checks and symlink safety.
Retaining the small ZIP implementation preserves demonstrated controls; its extension
and directory allowlists were the actual restriction and have been removed.

| Helper | Decision | Reason |
| --- | --- | --- |
| Pinned official quick_validate.py | Keep | Direct reuse, source digests unchanged |
| validate_repo.py | Simplify | Share CommonMark target extraction with package validation; retain duplicate-key, metadata, fixture and path checks |
| package_skill.py | Simplify | Generic regular files, explicit exclusions, dev opt-in, bounds and exact-payload secret scan |
| changed_skills.py | Simplify | Same selector for pushes and PRs, plus a tooling-regression decision |
| branch_policy.cjs and commitlint configurations | Keep | Existing branch rules and maintained commit parser |
| release.mjs | Simplify | Avoid rebuilding complete retries and analyzing unchanged skills |
| skill-release.mjs | Keep | Existing semantic-release library; scan and validate the specific package |
| run_model_evals.py | Keep | Optional bounded agent tasks; independent of mandatory CI |
| install_binary.py | Keep | Checksum-pinned local/CI binaries without extra wrapper Actions |
| External-linter negative tests | Restrict execution | Tooling/config/workflow changes exercise integration; actual linters remain mandatory |
| pytest configuration | Replace static paths | Native recursive discovery and excluded dependency/scratch directories |

Full structural validation remains mandatory because it is cheap and catches broken
cross-resource references. There is no new workflow, framework, registry, language or
paid model gate. The active ruleset, Conventional Commit policies, dependency audits,
SHA-pinned Actions and read-only PR jobs are preserved.

Two existing moderate advisories in semantic-release's unused bundled npm publisher
remain narrowly excepted by exact advisory paths in audit-ci.json. This pass does
not broaden the exceptions. The latest supported release dependencies were checked;
updates are preferable when an upstream compatible bundle fixes them. No zero-advisory
claim is made. Spelling and grammar checks remain disabled.

## Verification and measurement

Regression coverage uses disposable skill directories and Git remotes. It exercises
normal local validation, automatic pytest discovery/execution, arbitrary nested
resources, semantic first versions, independent/multi-skill/shared-only commits,
breaking changes, no-op tags and mocked GitHub CLI retry behavior. Fake skills are
never published to the production repository. Hosted Linux CI is the authority for
symlink creation on platforms that do not grant that capability locally.

The baseline successful main CI took 84 seconds including publication; its recovery
run took 26 seconds. Compare the refinement PR's validation jobs to prior PR runs,
not directly to main's total, because PRs intentionally skip publication. Single-run
wall times include runner/dependency-network variation and are not a guaranteed speedup.

The authoritative current behavior lives in [governance](ci-governance.md),
[releases and packaging](releases.md), and [contribution instructions](../CONTRIBUTING.md).
Older research and verification records are explicitly historical.
