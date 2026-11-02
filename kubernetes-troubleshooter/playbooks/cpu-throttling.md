# CPU throttling

## Trigger and relevant resources
High latency or CFS throttling. Start with pods POD; horizontalpodautoscalers; nodes NODE. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods --name POD
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource horizontalpodautoscalers
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodes --name NODE
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
sum by(namespace,pod)(rate(container_cpu_cfs_throttled_periods_total{namespace="NS"}[5m])) / clamp_min(sum by(namespace,pod)(rate(container_cpu_cfs_periods_total{namespace="NS"}[5m])),1e-9)
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Resource limit/revision changes, HPA events, application saturation/trace evidence. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
CPU-bound app vs traffic growth vs HPA failure vs node saturation vs slow dependency. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

Production-proven discriminators:
- No container CPU limit: check pod/ancestor cgroup quotas and historical limits
 before interpreting missing/zero throttle rates. Also inspect hosting-node CPU
 contention; cumulative counters can retain earlier throttling.
- A limit that the IaC never set: an out-of-band patch survives upgrades; check
 the field manager and remove it through IaC (see [churn loop](resource-churn-eviction-loop.md)).

## Confirmation criteria
Throttling and latency align in affected containers with CPU demand; compare unthrottled replicas and downstream spans before assigning cause. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Propose measured CPU/code/scaling change appropriate to confirmed bottleneck. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Higher limits shift saturation to nodes; preserve old resources and revision. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Latency/error SLO recovers at comparable RPS; node headroom and HPA stay healthy. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
