# GitLab Security Policies


An installable Agent Skill for designing, changing, governing and troubleshooting centrally
enforced GitLab security policies. It covers:


- scan execution, approval (MR gate), pipeline execution, scheduled pipeline execution and
 vulnerability management policies;
- policy exceptions;
- dependency scanning v2 resolution failures;
- estate-wide failure surveys;
- answering developer questions about findings.


The skill does not depend on how you deliver policies. Terraform/OpenTofu, API scripts, a
policy-as-code repository with CI and the UI editor are all covered. Production guidance and
measured behaviour come from operating policies on self-managed GitLab EE 19.x. Behaviour is
version-sensitive, so the skill verifies it against your instance's schema before relying on it.


## Installation and prerequisites


Copy this directory, keeping its name, into your host's skill directory. Examples:


- `~/.claude/skills/gitlab-security-policies`;
- `~/.codex/skills/gitlab-security-policies`;
- `.github/skills/gitlab-security-policies` in a repository.


Reload skills as your host requires.


Runtime requirements:


- Python 3.10+, standard library only.
- `jq`, plus `glab` (preferred) or `curl` for the runbook recipes.
- PyYAML, if you want `lint_policy.py` to read YAML directly. Otherwise pass JSON.
- A GitLab token with `read_api` for investigations and surveys. Use write scopes only for
 approved changes, such as policy commits or resync mutations.


Never bundle tokens, real job logs or organisation inventories in this directory.


## Invocation


Fill in [prompt.md](prompt.md). Fields you don't know can stay empty. Do not commit the filled-in
copy here. A short form also works:


```text
Use $gitlab-security-policies to find out why dependency scanning resolution fails in
group acme/payments since Monday. GitLab 19.3 self-managed, policies delivered by OpenTofu.
Read-only.
```


Run the scripts from this skill directory:


```sh
python scripts/lint_policy.py policy.yml --require-tags
python scripts/survey_failed_jobs.py --url "https://$GITLAB_HOST" --token-env GITLAB_TOKEN \
 --since 2026-01-01T00:00:00Z --group acme --fetch-logs --max-logs 200 > survey.json
python scripts/survey_failed_jobs.py --summarise survey.json
```


Script behaviour:


- Tokens are read from the environment variable named by `--token-env`, never from the command
 line.
- `survey_failed_jobs.py` is read-only and bounded by `--max-projects`, `--max-logs` and
 `--max-calls`.
- Survey requests require HTTPS and reject redirects. Responses larger than 10 MB
  are skipped with a warning for individual job or trace reads. Project discovery
  fails if its response exceeds the limit.
- `--keep-logs` stores log tails in the output so you can reclassify offline with
 `--reclassify`. Those tails may contain sensitive data, so handle them accordingly.
- `lint_policy.py` complements validation against the JSON schema at your version tag; it does
 not replace it. See [runbooks](references/runbooks.md).


## Layout


| Path | Purpose |
|---|---|
| [SKILL.md](SKILL.md) | Entry point: modes, guardrails, workflow |
| [prompt.md](prompt.md) | Intake template |
| [references/](references/) | Design principles, policy authoring, measured GitLab behaviour, exceptions, delivery, runbooks, troubleshooting, developer communication, report template, sources |
| [playbooks/](playbooks/index.md) | Symptom-driven investigation steps |
| [scripts/](scripts/) | `lint_policy.py`, `survey_failed_jobs.py` |
| [tests/](https://github.com/leonidpeskov1337/ai-agent-skills/tree/main/gitlab-security-policies/tests/) | Offline unit tests for the scripts |
| [evals/](https://github.com/leonidpeskov1337/ai-agent-skills/blob/main/gitlab-security-policies/evals/evals.json) | Scenario prompts with assertions |


## Validation


```sh
python -m unittest discover -s tests -v
```


The tests are offline and use synthetic fixtures. They check the linter and classifier logic, not
the agent's real-world accuracy. Use [evals](https://github.com/leonidpeskov1337/ai-agent-skills/blob/main/gitlab-security-policies/evals/evals.json) to assess reasoning. For formal
frontmatter validation, use the Skill Creator `quick_validate.py`.


## Maintenance


- When you find a new failure signature, add it to both
 [troubleshooting](references/troubleshooting.md) and `SIGNATURES` in
 `scripts/survey_failed_jobs.py`, with a test case.
- On a GitLab upgrade, diff the policy schema between the old and new version tags. Then re-check
 [gitlab-behaviour](references/gitlab-behaviour.md) and the linter constants.
- Record the provenance of every new measured fact in [sources](references/sources.md).
