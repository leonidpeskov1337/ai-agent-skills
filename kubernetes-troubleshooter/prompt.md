# Kubernetes incident prompt template

Copy the block below into your request and fill in what you know. The symptom is
enough to start; leave unknown fields `null` or lists empty. This is a prompt for
the host agent, not a configuration file automatically loaded by the scripts.
Use paths to credentials, never their contents. Do not commit filled-in incident
details, credentials or sensitive repository information to this skill repository.

```yaml
skill: kubernetes-troubleshooter
prompt: |
  Describe what is failing, expected behavior, observed errors, and affected users.
  Example: Checkout p95 latency rose after a rollout; some requests return 503.

cluster:
  context: null                  # Exact kubeconfig context, if known
  name: null
  provider: null                 # EKS, AKS, GKE, on-premises, other
  namespaces: []
  workloads_or_services: []       # Kind/name, pod UID or label selector if known
  environment: null              # production, staging, etc.

incident:
  started_at: null               # ISO 8601 with timezone, or approximate time
  ended_at: null                 # null when ongoing
  timezone: null
  impact_and_severity: null
  recent_changes: []             # Revision, chart, infrastructure or config changes
  healthy_comparison: null       # Healthy revision/node/zone/environment
  sanitized_errors_or_request_ids: []
  already_checked: []            # Checks, timestamps and actual observations

cluster_metrics_endpoint: null   # Approved query base, e.g. https://metrics.example/prometheus
metrics:
  backend: null                  # Mimir, Prometheus, Thanos, VictoriaMetrics, cloud, unknown
  cluster_label_selector: null    # e.g. cluster="prod-eu"; verify actual labels
  token_env: null                 # Existing environment VARIABLE NAME, not a token
  tenant_env: null                # Existing Mimir tenant VARIABLE NAME
  ca_bundle_file: null
  logs_or_traces_endpoints: []    # Approved endpoints only; no credentials in URLs

local_cluster_deployment_repos:  # Terraform, Helm, values, Kustomize, app source, GitOps
  - local_path: null              # Absolute existing checkout path; do not change it
    role: null                   # infrastructure, charts, values, GitOps, application
    relevant_paths: []            # Narrow folders/files to inspect
    expected_cluster_or_environment: null
    expected_revision: null      # Commit SHA/tag; local HEAD may not be deployed
    remote_url: null             # Optional approved repository URL without credentials

repository_access:
  credentials:                   # Optional, separate token for each approved host/scope
    - provider: null             # github or gitlab, including self-hosted installations
      approved_host: null        # e.g. gitlab.example.com
      allowed_repositories: []
      read_only_token_file: null # Absolute file path only; do not paste or print the token
  allow_remote_reads: false       # true only for listed hosts/repositories
                                 # Does not authorize checkout changes, pushes or PRs

argocd:
  enabled: null                  # true, false, or null when unknown; a discovery hint
  control_plane_context: null    # Can differ from the affected workload's cluster
  namespaces: []                 # Install namespace and/or Application namespaces
  server: null                   # Approved Argo API URL, if available
  token_env: null                # Existing auth VARIABLE NAME for an approved adapter
  ca_bundle_file: null
  applications: []               # namespace/name; multiple sources/apps are possible
  application_sets: []
  installation_id: null          # Useful with multiple Argo installations
  affected_workload_managed_by_argocd: null  # true/false/null; verify with evidence

constraints:
  mode: read-only
  investigation_budget_minutes: 15
  maximum_diagnostic_calls: 20
  excluded_targets: []
  additional_constraints: []
```

## Instructions to the investigating agent

Use `$kubernetes-troubleshooter`. Interpret the symptom and pursue competing
hypotheses with timestamped evidence; select the next read by expected diagnostic
value. Treat supplied context, repository revisions, metric labels and Argo flags
as leads to verify. Unknown fields are not blockers unless they affect target
identity, safety or interpretation. Do not silently turn an unknown into `false`.

Read supplied repositories only where relevant to this incident. Compare effective
deployment source/revision and live state; do not assume a local checkout or Terraform
code is applied state. Follow [repository guidance](ArgoCD/repositories.md) for
safe credentials and multi-repository correlation. File paths identify approved auth
inputs, not permission to dump credentials into chat, logs, command arguments or URLs.
If secure credential consumption is unavailable, report the access limit.

If Argo CD is present, check whether it manages the affected resource or an implicated
dependency before deep investigation. If unrelated, continue the normal Kubernetes
and telemetry loop. If management is uncertain or the user flag conflicts with
tracking evidence, state the uncertainty and do a bounded relevance check using
[Argo CD routing](ArgoCD/README.md); a remote Argo installation may manage this cluster.
Presence, `Synced`, `Healthy` and `OutOfSync` alone do not establish incident cause.

All cluster, repository and cloud changes require separate explicit authorization
for the exact action. No automatic sync/refresh/prune/restart/rollback, Terraform
apply, Helm changes, Git checkout/reset/pull, commits or pushes during investigation.
Return findings, metrics/time windows, ranked causes and alternatives, recommended
fixes with risks/rollback, recovery checks, and missing evidence. Never invent results.
