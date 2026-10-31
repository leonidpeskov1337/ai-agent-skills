# PVC and storage failures

## Trigger and relevant resources
Pending claim, FailedMount, attach failures or slow writes. Start with persistentvolumeclaims PVC; storageclasses; csidrivers; pods POD. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource persistentvolumeclaims --name PVC
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource storageclasses
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource csidrivers
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
kubelet_volume_stats_available_bytes / kubelet_volume_stats_capacity_bytes
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
PVC/pod mount and attach events, CSI logs, provider volume status. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Binding/zone/access mode vs CSI auth vs attach limit vs bytes/inodes vs I/O throttling. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Trace claim to volume/node and correlate explicit controller/provider error; Bound alone insufficient. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Correct proven capacity/zone/driver issue without deleting data resources. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Volume edits can lose data or require downtime; snapshot/backup and rollback feasibility required. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Claim bound, mount usable and application writes/latency healthy; no repeat attach errors. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
