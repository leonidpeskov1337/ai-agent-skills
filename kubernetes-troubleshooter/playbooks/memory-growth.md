# Memory growth and excessive usage

## Trigger and relevant resources
Working set/RSS grows or high memory utilization. Start with pods POD; nodes NODE. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods --name POD
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodes --name NODE
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
container_memory_rss{namespace="NS",container="APP"}
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
OOM/restart history, application GC/heap telemetry if already available. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Leak vs cache warming vs traffic growth vs native allocation vs node pressure. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

Production-proven discriminators:
- High working set on I/O-heavy workloads may include active page cache; compare
 RSS, reclaimability, cgroup events, limits and pressure. Absence of OOM/eviction
 evidence does not prove safe headroom.
- Per-worker growth bounded by an application memory guard (worker killer) that
 is disabled by a chart default can contribute to node-pressure eviction or
 container/node OOM depending on limits, growth and available capacity.

## Confirmation criteria
Growth persists across comparable load and GC cycles; independent heap/native evidence needed for a confirmed leak. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Fix proven allocation source; temporary sizing only with node-capacity review. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Extra capacity can defer failure; profiling can be intrusive and needs separate approval. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Growth stabilizes through multiple workload/GC cycles without OOM or node pressure. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
