# Code Quality Platform


An installable Agent Skill for building and operating a centrally governed code-quality platform
delivered as reusable CI/CD components. It covers:


- architecture: composition root, analyzer templates, summary, baseline-aware quality gate;
- contracts that prevent false greens (analyzer health, `not_applicable` vs `unavailable`,
 baseline per pipeline context, fingerprints, exceptions);
- coverage and new-code semantics, including the excluded-package trap;
- shared profiles, layered exceptions and the narrowest-fix decision table;
- release-driven versioning and getting a fix from the platform to every consumer;
- rollout beside a legacy tool, pilots, waves, decommissioning;
- symptom-driven playbooks and a log triage script;
- developer-facing communication.


Organisation- and vendor-neutral: estate specifics come from the intake in `SKILL.md` or from the
repository under change.


## Installation


Copy this directory, keeping its name, into your host's skill directory, for example
`~/.claude/skills/code-quality-platform`, `~/.codex/skills/...` or
`.github/skills/...` in a repository. Reload skills as your host requires.


## Requirements


- Python 3.10+, standard library only (for `scripts/triage_gate_log.py`).
- Read-only GitLab API access for investigation (token from an environment variable or an
 untracked local file; never committed).


## Layout


```text
SKILL.md          entry point: intake, modes, guardrails, invariants, workflows
prompt.md         fill-in request template for the host agent
references/       blueprint (build from scratch), lessons-learned, architecture, contracts,
                 coverage, profiles, release, rollout, testing, gotchas
playbooks/        symptom -> steps
scripts/          triage_gate_log.py (read-only gate log classifier)
tests/            python3 -m unittest discover -s tests
agents/           host UI metadata
```


## Test


```sh
python3 -m unittest discover -s code-quality-platform/tests
```
