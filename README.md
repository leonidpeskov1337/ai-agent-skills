# AI Agent Skills

Reusable skills for cloud infrastructure, platform engineering, and security.

## Skill catalog

Generated from each skill's metadata. After adding or updating a skill, run
`python -m tools.update_catalog`; CI checks that this table is current.

<!-- skill-catalog:start -->

| Skill | What it helps you do | Start here |
| --- | --- | --- |
| [Code Quality Platform](code-quality-platform/README.md) | Build and troubleshoot shared code-quality CI platforms | [Prompt template](code-quality-platform/prompt.md) |
| [GitLab Security Policies](gitlab-security-policies/README.md) | Design, change, govern and troubleshoot GitLab security policies | [Prompt template](gitlab-security-policies/prompt.md) |
| [Kubernetes Troubleshooter](kubernetes-troubleshooter/README.md) | Investigate Kubernetes incidents with evidence | [Prompt template](kubernetes-troubleshooter/prompt.md) |

<!-- skill-catalog:end -->

## Getting started

Open the skill's README for installation, prerequisites, and usage. Once installed,
invoke the skill by name and use its prompt template to share the context you have.

To build an independent `.skill` archive, install the development dependencies and
run `python -m tools.package_skill` for all discovered skills, or pass a skill
folder name to build just one. Use `--scan-secrets` for the same payload scan as CI. Archives and checksums are
written to `dist/`.

## Development

Read [CONTRIBUTING.md](CONTRIBUTING.md) for branch conventions, Conventional Commits
and local checks. [CI and governance](docs/ci-governance.md) describes validation,
security checks and the active GitHub protections.
[Releases](docs/releases.md) and [model evaluations](docs/evaluations.md) use trusted refs. Releases run automatically after successful main CI; paid model
evaluations remain opt-in.
