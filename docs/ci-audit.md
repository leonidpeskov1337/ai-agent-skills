# CI simplification audit

The seven reported findings were confirmed against merged main and GitHub APIs.
Main remains the default branch. The active native ruleset now requires PRs,
Validation gate, resolved threads and linear history, blocks deletion/force pushes,
and has no bypass actors. Only the owner is a direct collaborator, so mandatory
independent approval remains zero. Squash-only merging and automatic branch deletion
are enabled. These changes were explicitly authorized by this audit request.

| Tool | Decision | Reason |
| --- | --- | --- |
| Anthropic validator and supplementary validation | Retained | Official metadata checks plus tested reference/schema safety |
| skills.json | Removed | Root SKILL.md discovery is authoritative |
| package_skill.py | Simplified | Optional argument; no argument packages all discovered skills |
| changed_skills.py | Retained | Selective tests without skipped required checks |
| branch_policy.cjs and commitlint configs | Retained | Existing policy and official commit parser |
| release_target.py | Removed | Manual tagging no longer required |
| release.mjs / skill-release.mjs | Replaced manual flow | Semantic-release owns versions/tags/notes; small adapter filters by skill path; gh owns publication |
| model_cases.json | Moved | Each skill owns optional model cases |
| run_model_evals.py | Simplified | Discovers skill names and local cases |
| install_binary.py | Retained | Pinned verified binaries support local and CI validation |
| lint/security configurations and tests | Retained | Deterministic regression and security checks |
| ruleset proposal | Activated | Native GitHub enforcement, no custom protection implementation |

CI discovers skill folders, validates and packages all, selects applicable optional
tests, and reports Validation gate. A successful main push then invokes the reusable
release workflow. PRs never invoke a write-token release job. Manual recovery remains
available on main. Paid evaluations remain optional and do not gate routine changes.

Release Please requires release PR/manifest state; semantic-release directly releases
on merge and supports independent tag formats without new-skill manifests. Only one
release system is used. A new skill requires only its directory and SKILL.md.

Two moderate denial-of-service advisories remain in the unused bundled npm publisher
shipped by semantic-release: GHSA-3g3m-2fjr-6pw4 and GHSA-g3hv-75wg-m249. The explicit
plugin list does not load that npm publisher. audit-ci exceptions are restricted to
those advisory IDs through semantic-release's npm dependency path; all other moderate
or higher findings block CI. Remove these exceptions once upstream updates bundled
npm. Patched glob/minimatch overrides protect non-bundled consumers. Raw npm audit
still reports the unused bundled dependencies; this is not a zero-advisory claim.

Earlier governance/research/verification documents describe the initial implementation;
this audit and releases.md supersede their disabled-release and registry instructions.

## Verification

117 Python tests and 33 subtests passed locally. Node regressions cover branch and
commit policy, path-scoped release analysis, filesystem discovery, and an actual
semantic-release initial 1.0.0 tag followed by a no-op retry in a disposable bare
Git repository. Hosted PR CI passed all applicable jobs. Native ruleset 26754711
was read back as active with no bypass actors; an actual direct main push was
rejected with GH013 (PR and Validation gate required).
