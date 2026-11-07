# Deterministic and model-based evaluations

Normal CI validates metadata, fixture schemas, relative references, packaging,
read-only helper behavior, missing metrics, error handling and redaction through
the existing offline tests. This is free of model API calls and production access.

The existing `evals/` directories retain historical paired agent reports and human
assertion grades. They are not rerun or relabeled as current results merely because
CI checks their JSON. Synthetic incidents remain the basis for behavioral tests.

## Optional real-agent workflow

**Optional model evaluations** runs only through manual dispatch on the default
branch with `MODEL_EVALS_ENABLED=true`. First configure a protected `model-evals`
environment, restrict it to the default branch, and add an environment-scoped
`ANTHROPIC_API_KEY`. Approve a budget before enabling it. No secret is inherited by
PR workflows. Review Anthropic's commercial Claude Code terms before use; its CLI
is an optional evaluation runtime, not a redistributed open-source dependency.

The pinned Claude Code runtime executes paired baseline and with-skill tasks against
temporary copies of synthetic evidence. The baseline receives no skill directory.
The skill condition can progressively read its `SKILL.md` and supporting files.
Only the built-in Read tool is available; shell/write/network/MCP/cluster tools are
absent, and repository/user customizations are disabled. No kubeconfig, GitLab
token, deployment repository or production environment is supplied.

Cases in `tools/model_cases.json` exercise missing telemetry, config-change
correlation, query completeness, malicious log instructions and read-only boundaries.
Each call has a $1 stop budget, eight-turn limit and 240-second timeout. One selected
skill currently runs two calls. Provider enforcement can allow the final request to
cross a budget slightly; also configure account-level spending limits.

Reports preserve model identity, Git SHA, raw output/usage/cost metadata, wall time,
condition and prewritten assertions. Workflow artifacts retain them for 30 days.
Download an accepted run as a baseline and compare both the paired task outputs and
human assertion pass counts when reviewing a regression. Commit sanitized reviewed
results under the appropriate skill's `evals/` directory when they warrant a durable
baseline. Do not promote a candidate baseline automatically.

These are actual agent tasks, rather than a model asked to judge prose. Assertion
grading remains human-reviewed, matching the existing Skill Creator workflow; the
job reports successful execution as **needs-human-review**, never semantic success.
Authentication, provider, timeout or malformed output errors produce a failed job
classified as infrastructure/provider error, not a behavioral regression. No paid
evaluations are required for routine PRs. For a high-risk change, run this workflow
after merging only when approved, or reproduce locally on an explicitly reviewed
branch with the same tool restrictions and budget before merge.

For local execution after explicit budget approval:

```sh
npm ci --ignore-scripts --prefix .github/model-evals
python -m tools.run_model_evals kubernetes-troubleshooter
```

Supply the API key through your process environment; never put it in commands or
committed files. Running without a key fails clearly before any model call.

## Framework choice

Anthropic's pinned `run_eval.py` was inspected: it measures description triggering,
creates temporary commands, and stops on first tool selection. It is useful for
future routing evaluation, but does not grade incident investigation. Its default
CLI invocation also lacks the offline tool restrictions needed here, so it is not
executed automatically. Skill Creator's human rubrics and existing fixture/report
format are retained.

Promptfoo's Claude Agent SDK provider supports real agent evaluation, cost tracking
and assertions; DeepEval supplies another model evaluation stack. Either could be
useful at greater scale. Installing both, or adding a full grading framework for two
initial canaries, would duplicate the existing assertion review workflow. The small
adapter only orchestrates the official CLI and records outputs; it does not implement
a grading framework. Future automated semantic grading should adopt one maintained
framework, use blinded reviewed baselines, and explicitly distinguish service
failures from behavioral failures.

The current canaries do not measure automatic skill selection, run mocked kubectl
commands, or prove production safety. Extend the suite with an allowlisted mock-tool
environment before using it as a required production-investigator benchmark.
