# Karpenter and Cluster Autoscaler

## Trigger and relevant resources
Pending pods persist despite autoscaler. Start with pods; nodes; events. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodes
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource events
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodeclaims.karpenter.sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodepools.karpenter.sh
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
kube_pod_status_unschedulable{namespace="NS"}
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Existing autoscaler logs, node pool/claim conditions and provider quota/capacity errors. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Pool limits/constraints vs quota/capacity vs IP exhaustion vs daemon overhead vs not scale-triggering. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

Production-proven discriminators:
- Read NodeClaims (`--resource nodeclaims.karpenter.sh`): `Launched=False` with
 `VcpuLimitExceeded` = account quota; `InsufficientInstanceCapacity` = family/zone
 capacity. No current NodeClaim can also reflect controller/RBAC/pool-limit
 problems or deleted failed claims; inspect logs/events before selecting a cause.
- Launched vCPU near quota with low CPU use: oversized pod requests (often
 ephemeral storage or memory) are choosing large instances (see [CI runner jobs](ci-runner-jobs.md)).
- Daily NodeClaim churn: one pod per node or wrong consolidation mode
 (see [churn loop](resource-churn-eviction-loop.md)).

## Confirmation criteria
Controller reason and provider capacity/quota/constraint evidence match unschedulable pod. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Propose eligible pool capacity or corrected constraint within budget. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Capacity costs, consolidation and disruption; preserve pool configuration. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Eligible node becomes Ready and pod schedules without violating constraints. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
