# ai-agent-skills
A collection of reusable AI agent skills for cloud infrastructure, platform engineering, and security.

- [Kubernetes Troubleshooter](kubernetes-troubleshooter/README.md): read-only,
  hypothesis-driven incident investigation, historical Prometheus/Mimir metrics,
  27 targeted playbooks and offline evaluation fixtures.
  Start with the [incident prompt template](kubernetes-troubleshooter/prompt.md);
  [Argo CD guidance](kubernetes-troubleshooter/ArgoCD/README.md) applies when relevant.

Package with `python tools/package_skill.py`; see the skill README for installation,
usage, validation results and operational limits.
