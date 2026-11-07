# CI architecture and repository governance

## Active GitHub settings

Main is protected by native ruleset 26754711: PRs and a successful **Validation gate**
are required, branches must be up to date, conversations resolved and history linear.
Deletion and force pushes are blocked, with no bypass actors. Only the owner is a
direct collaborator, so independent approval count is zero. Squash merging is the
only merge method, PR titles form squash subjects, and merged branches are deleted.
Actions defaults use read-only tokens and cannot approve PR reviews.

These settings were explicitly activated during the audit. Authenticated API reads
confirmed enforcement, and an actual controlled direct push to main was rejected
with GH013. The committed ruleset JSON records the active configuration. See
[the audit](ci-audit.md) for the tool-by-tool decisions and verification limits.

## Workflow architecture

1. CI runs for every PR update and main push without workflow path filters.
2. Reusable PR policy validates contributor branches, strict conventional PR titles,
   and every introduced commit using the full base..head range and commitlint.
3. Structure validation discovers root folders containing SKILL.md, validates them
   and builds each independent package. No manually maintained registry exists.
4. Skill tests are selected from a NUL-delimited Git diff. Shared/unknown paths
   select all skills; root documentation-only changes select none. Optional test
   directories run when present. A skill's Markdown changes still select its tests.
5. Code quality runs Ruff, pytest, yamllint, Markdown structure lint and actionlint.
   Security runs zizmor, redacted Gitleaks scans, pip-audit and the npm audit policy.
6. The always-running Validation gate explicitly checks applicable success and
   intentional skips. Failed, cancelled or unexpectedly skipped jobs fail it.
7. Only successful main pushes invoke the reusable automatic release workflow.
   Its condition explicitly tolerates the skipped PR-only policy job. Release
   failure fails the overall run and can be retried; it does not falsify validation.

PR jobs receive read-only tokens and no production or paid-model credentials.
Checkout does not persist credentials. Untrusted PR strings enter shells only as
quoted environment variables. There is no pull_request_target or privileged
workflow_run execution. Only the trusted main release job receives contents:write.
Paid model evaluations remain manually enabled on trusted refs.

Concurrency cancels superseded CI runs. Releases use a separate non-cancelling
concurrency group. Dependency caches are disabled; installations use integrity locks.
No spelling or grammar enforcement is configured.

## Skill discovery and local tooling

Add `new-skill/SKILL.md` with matching metadata. Optional scripts, references, tests
and evaluations stay within that folder. Discovery, validation, packaging and release
require no central edits. Optional paid model cases belong in evals/model-cases.json.
Run `python -m tools.validate_repo`, `python -m pytest`, `npm run test:policy`, and
`python -m tools.package_skill` to validate and package all discovered skills locally.

The unmodified pinned Anthropic validator supplies metadata validation. Minimal
supplementary checks cover nonempty fields, name/directory agreement, duplicate
YAML/JSON keys, relative resources, evaluation schemas and archive safety. Markdown
links are parsed outside code examples. External URLs and heading anchors are not
checked offline; description relevance remains a maintainer review responsibility.
No heading structure is prescribed. Historical evaluation reports are not new model
runs merely because their JSON passes validation.

The original deterministic packager is retained and generalized. It includes tests
and evaluations, unlike the upstream packager's default evals exclusion, and verifies
ZIP contents and checksums. Development dependencies are not bundled into skills.

## Maintaining the system

- Python: edit requirements-ci.in and regenerate requirements-ci.txt with Python
  3.14 and pip-tools 7.6.2 using hash generation, then run pip-audit and tests.
- Node: regenerate package-lock.json with installation scripts disabled and run
  `npm run audit`. The audit documents exact exceptions for two advisories in
  semantic-release's unused bundled npm publisher; it does not claim zero advisories.
- Actions: review Dependabot SHA updates and runtime/permission changes.
- Binaries: review release artifacts and checksums before editing tools/binaries.json.
- Anthropic: review a specific upstream commit, preserve its license and exact
  bytes, update UPSTREAM.json digests, and rerun negative tests.
- Release preset/writer upgrades: run the initial-tag integration test, including
  actual release-note rendering, before merging. See [releases](releases.md).

Sensitive workflow/lock/governance changes need particular review because ordinary
repo-controlled checks can themselves be edited by a PR. Native metadata restrictions
are plan-dependent; GitHub documents additional controls for Enterprise organizations.
This personal repository enforces branch names and commits through its PR checks.
Unprotected development branches can contain invalid commits, but those cannot pass
an intact required gate. Local hooks remain optional developer conveniences.

For another maintainer, require independent approval and consider CODEOWNERS for
.github/, tools/, locks and skill scripts. Do not make solo review impossible.

## Troubleshooting

Run the same check locally and use its file/schema/advisory diagnostic. Do not hide
failures by removing the gate's always() condition, adding workflow path filters or
broadening secret/audit exceptions. Advisory-service outages are infrastructure
failures. Kubernetes helper tests use loopback mocks; restricted desktop sandboxes
may require execution permission for subprocesses and sockets. No cluster access is
needed. Manual release recovery is available on main; no hand-created tag is required.
