# FailedScheduling

## Trigger and relevant resources
Scheduler reports no feasible nodes. Start with pods POD; nodes; events. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods --name POD
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodes
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource events
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
kube_node_status_allocatable{resource="cpu"}
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Scheduler fit reasons; node/pool and autoscaler events. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Requests/capacity fragmentation vs taints vs affinity/zone vs unbound PVC vs GPU. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Reconcile scheduler reason with requests including init/overhead and eligible node allocatable; low usage does not mean schedulable capacity. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Propose eligible capacity or correct unintended request/constraint. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Cost and disruption; preserve constraints and avoid violating availability zones. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Scheduler events stop; placement satisfies intended constraints and capacity margin. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
