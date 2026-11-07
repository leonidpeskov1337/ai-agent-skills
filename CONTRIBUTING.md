# Contributing

Use short-lived branches and pull requests against the current default branch.
GitHub currently uses `main`; the requested move to `master` is an administrator
decision. Workflows support both during that transition. There is no `develop` branch.

## Local workflow

1. Create a branch such as `git switch -c feature/mimir-discovery`.
2. Make a focused change and add meaningful offline regression tests for behavior changes.
3. Install and run the checks below.
4. Commit with a Conventional Commit, for example `fix(kubernetes): handle missing CPU metrics`.
5. Push your branch and open a PR with a conventional title.
6. Wait for **Validation gate**, resolve conversations, and obtain independent
   review when additional maintainers are available.
7. Squash merge; GitHub should delete the development branch after merging.

Branches use `feature/`, `fix/`, `skill/`, `refactor/`, `docs/`, `test/`, `ci/`,
`chore/`, or `security/` followed by lowercase kebab-case. Nested paths and
consecutive hyphens are rejected. Fork contributions follow the same rule.
Only PRs authored by `dependabot[bot]` and `renovate[bot]` receive their respective
automation branch exceptions. Add other automation identities deliberately.

Commit types: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`,
`revert`, `style`, `test`, `security`. Scopes are optional. Breaking changes use
`feat!: ...`, `feat(scope)!: ...`, or a `BREAKING CHANGE:` footer. Commitlint's
standard generated merge/revert/version ignores apply to commits; PR titles use
strict validation with those ignores disabled. Every commit in `base..head` is
checked with full history. Squash titles must remain conventional when merging.

## Install development tooling

Use Python 3.14 and Node.js 24, matching CI. Skill helpers themselves retain their
documented Python 3.10+ standard-library runtime.

```sh
python -m venv .venv
# POSIX: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-ci.txt
npm ci --ignore-scripts
```

```sh
python -m tools.validate_repo
python -m pytest
python -m ruff check .
python -m ruff format --check tools --exclude tools/vendor
yamllint .
npm run lint:markdown
npm run test:policy
python -m tools.package_skill kubernetes-troubleshooter
python -m tools.package_skill gitlab-security-policies
python -m tools.install_binary actionlint
python -m tools.install_binary gitleaks
# POSIX binary locations; append .exe on Windows:
.ci-bin/actionlint/actionlint
zizmor --offline .github/workflows
.ci-bin/gitleaks/gitleaks git --redact --no-banner
.ci-bin/gitleaks/gitleaks dir --redact --no-banner --config .gitleaks.toml .
pip-audit --disable-pip --no-deps -r requirements-ci.txt
npm audit --audit-level=moderate
```

Linting checks code and structural formatting; spelling and grammar are not enforced.
Python lint runs across existing helpers. Formatting is enforced on shared tooling
to avoid reformatting the established skill implementations in this change.

Optional local hooks: use [Husky](https://typicode.github.io/husky/) with a
`commit-msg` hook invoking `npx --no-install commitlint --edit "$1"` after installing
a reviewed version locally. Hooks improve feedback but can be bypassed; required
PR checks and approved GitHub rules provide the merge boundary.

## Skill creation checklist

- Create a root skill folder with `SKILL.md`, a matching name, and a clear description.
- Discovery, validation, packaging and release automatically find root skill folders.
- Use resources only when needed; there is no required Markdown heading layout.
- Keep relative links within the skill; include referenced files in its package.
- Add synthetic evaluations with assertions and meaningful offline script tests.
- Keep credentials, production access, caches and generated artifacts out of Git.
- Package the skill independently and inspect the archive before publishing.

See [CI and governance](docs/ci-governance.md), [release instructions](docs/releases.md),
and [evaluation instructions](docs/evaluations.md).
