# CI architecture and repository governance

## Discovery and gap analysis

Public GitHub API inspection on 2026-11-07 confirmed `main` as the default branch,
public visibility, and an empty repository ruleset list. Unauthenticated branch
protection reads returned HTTP 401, so classic protection and private settings
could not be verified. No live settings were changed. The account plan and number
of independent maintainers were not available through public metadata.

Before this change the repository had two root skills, Python standard-library
helpers, 81 offline tests, JSON incident/evaluation/report artifacts, and a
deterministic Kubernetes-only packager. It had no Actions workflows, dependency
locks, contribution policy or ruleset definitions. The existing skill directories
and behavior are preserved; only two unused test imports were removed for linting.

## Validation design

| Responsibility | Implementation |
| --- | --- |
| PR branch, title, every commit | Reusable `pr-policy.yml`, commitlint, authenticated PR-author bot exceptions |
| Metadata | Unmodified pinned Anthropic `quick_validate.py` plus minimal spec checks |
| References and fixtures | CommonMark parser, JSON Schema, strict JSON parsing, YAML parsing |
| Packages | Existing deterministic ZIP design extended to both skills, nested fixtures, integrity and SHA-256 checks |
| Code quality | Ruff, pytest, yamllint, markdownlint-cli2, actionlint |
| Security | zizmor, Gitleaks history and directory scans, pip-audit, npm audit, Dependabot |
| Behavioral evaluation | Existing offline tests and optional paired real-agent tasks with human rubric review |
| Mandatory merge result | **Validation gate**, which requires success from every applicable job |

CI runs on all PR updates without path filters, including title edits. Full-history
checkout covers `base..head`, including earlier PR commits; commitlint handles
generated merge/revert/version commits with its standard ignores. All PR jobs have
read-only tokens, no persisted checkout credentials, and no application secrets.
There is no `pull_request_target` execution. PR content enters shell commands only
through quoted environment variables, and branch/title data is never evaluated as code.

Skill-specific tests use a NUL-delimited Git diff; shared or unknown paths select
both skills. Root/docs-only Markdown changes skip skill tests but still run structure,
packaging, quality and security. Changes within a skill select its tests even for
Markdown because skill prose is executable agent guidance. No normal PR invokes a
paid model. The always-running gate explicitly accepts skipped skill tests only
when detection selected none. A failed/cancelled dependency fails the gate. Use
**Validation gate** as the single required status; matrix job names can evolve.

Concurrency cancels superseded PR runs. No dependency cache is used initially:
installations are small, locks are integrity checked, and there is no cross-trust
cache to poison. Consider cache additions only after measuring run time.

The official validator does not enforce nonempty values, directory/name equality,
relative links, evaluation schemas or archive safety. Supplementary checks cover
these gaps with negative tests. They do not impose headings. Markdown file links
are parsed outside code examples; external URLs and heading anchors are outside
the offline check. Evaluation suites validate IDs, references and assertion shape;
historical reports remain distinct JSON artifacts, not claims of new model runs.
Description relevance and prose quality still require maintainer review.

The pinned upstream packager was inspected. It recursively copies files and omits
root `evals/`, whereas this repository distributes its evaluation fixtures. Reusing
the existing packager preserves that behavior while adding independent skill input,
nested resources, safe input restrictions and archive verification. Packages include
tests/evaluations intentionally. Gitleaks checks source before release; a checksum
proves integrity, not absence of secrets or publisher authenticity.

## Proposed GitHub setup — requires administrator approval

The JSON under [.github/governance](../.github/governance/default-branch.ruleset.json)
is a disabled proposal, not evidence of enforcement. It targets `~DEFAULT_BRANCH`
so it survives an approved rename from `main` to `master`.

1. Review this change through a PR and confirm a successful **Validation gate**.
2. Decide whether to rename `main` to `master` in repository Settings → Branches.
   Update existing PR bases, local tracking and default-branch links after renaming.
   Workflows already accept both names; keep only the chosen trunk long term.
3. Apply the proposed [repository merge settings](../.github/governance/repository-settings.json):
   squash only, PR-title squash subjects, automatic merged-branch deletion.
4. Import the disabled ruleset, select **Validation gate** from an actual run, and
   verify GitHub Actions is its expected source (integration ID 15368). Require an
   up-to-date branch, resolved conversations, linear history, PRs, no deletion or
   force push, and no routine bypass actors. Activate only after reviewing the API
   response and UI. Do not add a blanket restricted-updates rule with no bypass:
   that would also block the desired merges.
5. The proposal uses zero mandatory approvals for a solo maintainer. When an
   independent maintainer is confirmed, change approval count to one and consider
   CODEOWNERS for `.github/`, `tools/`, locks and skill scripts. Enable stale-review
   dismissal and last-push approval only when independent review is satisfiable.
6. Set default Actions token permission to read-only, allow only reviewed actions,
   and require approval for outside-contributor workflow runs. Workflow, lock and
   policy changes require particular scrutiny: ordinary repo-controlled checks can
   themselves be edited by a PR. A required trusted workflow policy, where the plan
   supports it, strengthens this boundary.
7. Configure the protected `release` and `model-evals` environments, restricted to
   the default branch, before enabling their repository variables. See the linked
   release and evaluation guides. No production credentials belong in this repo.
8. Re-read rulesets and classic branch protection with authenticated admin access,
   verify API responses, then test an invalid PR, a direct push, force push and
   deletion using a disposable branch/repository. Do not perform destructive tests
   against the actual trunk. Record the observed results before claiming enforcement.

[GitHub documents rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets)
for public repositories on Free, including personal public repos. The actual
account plan and availability of advanced metadata restrictions remain unverified.
If Settings → Rules → Rulesets offers branch-name metadata restrictions, apply the
same prefix pattern as `tools/branch_policy.cjs`, with explicit bot exceptions and
exclusions for trunk. Native restrictions apply only to this repository's branches;
the PR check is still needed for forks. Do not activate an unconditional pattern
that blocks trunk or approved automation.

Native commit-message metadata rules, if available, can restrict server-side pushes.
They use regex semantics and do not replace commitlint; account for generated merge,
revert and automation messages before activation. Without these native restrictions,
invalid commits can be pushed to development branches but cannot satisfy an intact
required PR gate. GitHub Actions YAML alone does not protect a branch.

## Updating dependencies and upstream tooling

- Python: edit `requirements-ci.in`, use Python 3.14 and `pip-tools==7.6.2`, then run
  `pip-compile --generate-hashes --strip-extras --output-file requirements-ci.txt requirements-ci.in`.
  Verify the lock installs on Linux as well as Windows; re-run pip-audit.
- Node: use Node 24 and `npm install --ignore-scripts` to refresh `package-lock.json`.
  Update the separate optional-model lock in `.github/model-evals` independently.
- Actions: Dependabot proposes SHA updates. Review upstream release notes and
  action permissions/runtime before merging.
- Binary tools: update the versioned upstream release URLs and archive SHA-256
  values in `tools/binaries.json`; verify published checksum lists and releases.
  Installer extracts only the named executable after hash verification.
- Anthropic validator: review a specific upstream commit, copy only the validator
  and its Apache license, update `UPSTREAM.json` digests, and run negative tests.
  CI never downloads code from upstream's moving branch.

Dependabot updates require matching hash/integrity locks; CI fails inconsistent
updates. No blanket advisory suppression or secret-scan baseline is configured.

## Troubleshooting CI

- **PR policy**: check branch prefix, every introduced commit, and PR title. Rebase
  or fix commit messages on the development branch; do not force-push trunk.
- **Structure**: use the reported file/reference/schema error. Register new skills;
  do not silently remove registry entries to hide a missing `SKILL.md`.
- **Tests**: run the selected skill tests locally. Kubernetes tests use loopback
  mock HTTP servers, never live cluster endpoints. Restricted desktops may need
  local execution permission for subprocesses and loopback sockets.
- **Security**: fix the finding. For an intentional fixture, narrowly document and
  test an exception; never exclude all skill scripts or workflows.
- **Gate skipped or failing**: inspect upstream jobs. Do not remove `always()` or
  add workflow path filters. External advisory outages are infrastructure failures.
- **Manual workflows skipped**: check default ref, enablement variable and protected
  environment setup; an intentional skip is not a successful evaluation or release.

See [tool research](tooling-research.md), [evaluations](evaluations.md),
[releases](releases.md), and [verification record](verification.md).
