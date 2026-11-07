# AI Agent Skills

Reusable skills for cloud infrastructure, platform engineering, and security.

## Skill catalog

| Skill | What it helps you do | Start here |
| --- | --- | --- |
| [Kubernetes Troubleshooter](kubernetes-troubleshooter/README.md) | Investigate Kubernetes incidents with read-only diagnostics, historical Prometheus and Mimir metrics, and 32 playbooks. Covers capacity reviews, change verification, and Argo CD when it manages the affected workload. | [Incident prompt](kubernetes-troubleshooter/prompt.md) · [Argo CD guide](kubernetes-troubleshooter/ArgoCD/README.md) |
| [GitLab Security Policies](gitlab-security-policies/README.md) | Design, audit, and troubleshoot centrally enforced GitLab security policies. Includes a policy linter, investigation playbooks, and a read-only survey of failed scan jobs. | [Policy prompt](gitlab-security-policies/prompt.md) · [Runbooks](gitlab-security-policies/references/runbooks.md) |

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
