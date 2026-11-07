# Kubernetes Troubleshooter

An installable Agent Skill for hypothesis-driven production incident investigation,
with 32 targeted playbooks and executable read-only evidence/metrics helpers.
Includes conditional [Argo CD investigation](ArgoCD/README.md), safe Application/
ApplicationSet evidence projection, and local deployment-repository correlation.

## Installation and prerequisites

Copy this directory, keeping its name, into your host's skill directory (for Codex,
`~/.codex/skills/kubernetes-troubleshooter`). Alternatively unpack the generated
`.skill` ZIP there. Reload skills as required by the host. The package is instructions,
references and scripts, not a standalone autonomous daemon or a grant of access.

Runtime: Python 3.10+, kubectl when using Kubernetes helpers, host execution tools,
approved network routing/credentials, and namespace-scoped read-only RBAC. Start
with get/list for implicated resource types and optional get pods/log. Cluster
resources need separate read permissions. `auth can-i` uses access reviews; the
helpers do not install RBAC or request administrative privileges. No Python package
dependencies are needed at runtime. Never bundle kubeconfig, tokens or real logs.

## Invocation

Copy [prompt.md](prompt.md) to describe symptoms, known cluster/metrics access,
Terraform/Helm/GitOps repository paths, scoped read-only token-file locations and
optional Argo CD context. Unknown fields can stay empty. Do not commit the filled-in
copy here. The host interprets it; helpers do not automatically load prompt files or
consume repository token files. Argo CD presence triggers a bounded relevance check,
not an automatic assumption that it manages the affected workload or caused failure.

```text
Use $kubernetes-troubleshooter to investigate checkout p95 latency since
09:00 UTC in context prod-eu, namespace payments. Read-only investigation.
Our approved metrics API is https://metrics.example/prometheus (Mimir).
```

From this skill directory:

```sh
python scripts/discover_cluster.py --context prod-eu --namespace payments
python scripts/collect_evidence.py --context prod-eu --namespace payments --resource pods --selector app=checkout
python scripts/discover_observability.py --context prod-eu --namespace monitoring --monitors
python scripts/query_metrics.py --help
```

Supply approved auth using existing environment-variable names (`--token-env`,
`--tenant-env`), not literal tokens on command lines. Use the complete API prefix
in `--base-url`. Scripts emit JSON to stdout and never write cluster evidence to
disk automatically. Review and sanitize logs/labels before sharing or persisting.
Discovery returns candidate infrastructure, not permission to connect to it.

The agent chooses next diagnostics based on evidence, compares historical telemetry
and competing hypotheses, and reports limitations when access/metrics are missing.
Mutating remediation always requires explicit approval for the specific action.

## Validation and packaging

```sh
python -m unittest discover -s kubernetes-troubleshooter/tests -v
python tools/package_skill.py
```

Run these from the repository root. Packaging uses the repository development dependencies,
includes a single top-level skill folder, excludes caches and working evaluation runs, and writes
`dist/kubernetes-troubleshooter.skill` plus SHA-256. Development tests/evals stay in the repository; use `--include-dev` to include them.
For formal frontmatter validation use the host Skill Creator `quick_validate.py` or
Anthropic's same-named validator; those developer tools require PyYAML.

See [evaluation scenarios](https://github.com/leonidpeskov1337/ai-agent-skills/blob/main/kubernetes-troubleshooter/evals/evals.json), [offline fixtures](https://github.com/leonidpeskov1337/ai-agent-skills/blob/main/kubernetes-troubleshooter/evals/fixtures.json),
[evaluation results](https://github.com/leonidpeskov1337/ai-agent-skills/blob/main/kubernetes-troubleshooter/evals/results.md) and [worked reports](examples/investigations.md).
The upgrade adds [incident-pattern evaluation scenarios](https://github.com/leonidpeskov1337/ai-agent-skills/blob/main/kubernetes-troubleshooter/evals/real-incident-evals.json)
and [user-supplied sanitized case summaries](examples/real-incident-patterns.md).
Probe projections keep timing, handler shape and HTTP paths while omitting exec
commands, HTTP header values and URL query/fragment values. They are deliberately
partial; inspect any further required non-sensitive field separately.
Offline HTTP tests run only against a local mock server. No tests use a live cluster.
The scenario rubric tests reasoning separately from transport correctness; do not
treat mock helper coverage as evidence of real-world autonomous incident accuracy.

See [source provenance and limitations](references/sources.md) for gated-source
coverage, supported adapters, sanitization limits and future work.
