# HPA VPA and KEDA failures

## Trigger and relevant resources
Replica demand unmet, metrics unavailable or oscillating. Start with horizontalpodautoscalers HPA; deployments; pods. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource horizontalpodautoscalers --name HPA
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource deployments
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
kube_horizontalpodautoscaler_status_desired_replicas{namespace="NS"}
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
HPA conditions/events, adapter/controller logs, KEDA trigger status and VPA recommendations. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Metrics API/adapter missing vs request denominator vs stabilization/max vs trigger auth vs unschedulable replicas. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Exact scale condition and metrics source establish blocked stage; desired replicas differs from Ready. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Repair proven metrics/requests/trigger path or reviewed scaling bounds. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Scaling adds cost/load; VPA changes can restart pods; retain old policy and replica baseline. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Valid samples, desired/current/ready converge and SLO recovers across stabilization cycles. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
