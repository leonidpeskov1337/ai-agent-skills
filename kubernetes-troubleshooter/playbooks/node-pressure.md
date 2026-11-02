# Node pressure and evictions

## Trigger and relevant resources
MemoryPressure, DiskPressure, PIDPressure or evicted pods. Start with nodes NODE; pods; events. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodes --name NODE
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource events
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Kubelet eviction thresholds/reasons, filesystem and process telemetry. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Memory vs disk bytes vs inode vs PID vs ephemeral storage requests. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

Production-proven discriminators:
- Evictions with memory request below representative usage suggest under-reservation;
 verify aggregate node demand and actual pressure. With a workload controller,
 HPA and a provisioner, test whether this contributes to a churn loop
 (see [churn loop](resource-churn-eviction-loop.md)).

## Confirmation criteria
Pressure transition and threshold breach match eviction timestamps and implicated resource. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Address bounded source growth or add capacity; propose safe retention changes. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Cleanup risks data loss; no automatic deletion; restore limits/retention where reversible. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Pressure clears sustainably; no new evictions under normal load. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
