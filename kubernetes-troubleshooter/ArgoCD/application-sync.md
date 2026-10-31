# Application, sync, health and ApplicationSet failures

## Trigger and first reads

Use for a verified managed workload with unexplained revision/drift, failed/stuck
sync, degraded resources, or a missing/incorrectly generated Application. Read the
named Application with the collector described in [routing](README.md). Inspect:

- Destination cluster/namespace, project, owner ApplicationSet, generation and
  reconciliation timestamp.
- `spec.source` or **every ordered `spec.sources` entry**, including chart/path/ref
  and targetRevision. Compare `status.sync.revision`/`revisions`, operation syncResult,
  history, actual resource revision/image and incident time. A branch name or chart
  version is not necessarily a Git SHA. Multi-source status arrays must be mapped
  to their matching source positions; values can come from a different repository.
- Sync and health separately; conditions, operation phase/start/end/message and
  per-resource sync/hook results. Failed sync can leave a partially changed app.
- Resource hooks and sync-wave annotations, Job/pod status and scoped events/logs.
  An early failed hook/unhealthy wave can prevent later resources from progressing.
  Do not re-run hooks automatically; they may migrate databases or write data.
  A Job's `FailedCreate` can mean admission rejected its Pod before migration code
  ran; distinguish that from a failed execution and inspect earlier attempts.

## Competing hypotheses and confirmation

| Branch | Evidence needed to distinguish it |
|---|---|
| Render/source failure | Comparison/manifest-generation error plus repo-server error for the exact source/revision; check chart dependencies, Kustomize paths, values refs and plugin availability |
| Repository access/TLS/revision missing | Named repo/revision error plus repo-server log/approved provider read; do not print auth or inspect credential Secrets |
| Sync/apply rejection | Resource result + Kubernetes admission/RBAC/quota/immutable-field error at the same time; verify controller destination access versus operator access |
| Hook/wave stuck | Hook Job failure or first unhealthy wave and operation timestamps explain the blocked later resource; stale UI alone is insufficient |
| Runtime failure after successful sync | Desired/applied revision agrees, but pod/events/metrics show app/network/storage/dependency fault; follow normal playbooks |
| Benign drift or competing writer | Non-sensitive field-specific difference, HPA/operator ownership and ignore-difference rules explain OutOfSync; drift alone is not outage causality |
| ApplicationSet generation failure | Owner reference and named ApplicationSet conditions/controller errors identify failing generator/template/SCM selection; missing Application alone does not prove why |
| App-of-apps/parent reconciliation | Owner/source evidence links a parent that overwrites the child; do not patch the child spec as a durable source fix |

For ApplicationSets, collect the named CR and controller logs. The helper deliberately
emits only generator **types**, conditions and safe template source pointers. Inspect
only relevant sanitized selector/ref/template fields separately. Generators may use
SCM/cluster credentials and values; never dump the whole generator or Secret data.

## Metrics

Discover names/labels and API history using [metrics guidance](../references/metrics.md).
Examples only when present, scoped to the actual installation/cluster/Application:

```promql
argocd_app_info{name="VERIFIED_APP",namespace="APP_NAMESPACE"}
increase(argocd_app_sync_total{name="VERIFIED_APP",phase="Failed"}[30m])
```

`argocd_app_info` carries sync/health labels; a value of 1 is informational, not
availability. Confirm the metric's namespace denotes the Application namespace in
this version. A failed-operation count is not an application 5xx rate. Match operation
times to rollout, traffic, errors and trace evidence; verify scrape freshness/deduplication.

## Remediation, risk and verification

Propose the smallest source/config/access correction supported by evidence and
identify its owning repository/revision. A Git write can trigger auto-sync and must
be treated as a production change. A direct live patch may be reverted by self-heal;
a child Application edit can be regenerated. Exact commands need verified target,
source of truth, auto-sync policy and separate approval. Do not automatically sync,
refresh, prune, disable self-heal or roll back. Reverting Git or sync history may be
unsafe after schema/volume/hook changes; record a compatible prior revision and
data recovery constraints before suggesting rollback.

Verify source and applied revisions converge, errors/blocked hooks clear, and the
actual affected workload/dependency meets readiness and request SLOs at comparable
load. Observe multiple reconciliation/scrape cycles. Synced/Healthy alone does not
verify recovery. Report missing desired/applied history and untested alternatives.
