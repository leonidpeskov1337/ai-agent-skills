# Service mesh failures

## Trigger and relevant resources
Proxy 503, mTLS/authorization or sidecar readiness errors. Start with pods; services; deployments. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource services
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource deployments
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Existing proxy/control-plane logs, config distribution status and certificate metadata. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
mTLS identity vs auth policy vs stale xDS vs retries/circuit breakers vs app backend. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Proxy response flags/trace and effective policy identify failing hop; compare app metrics. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Correct mesh policy/routing/cert wiring or reviewed proxy revision. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Mesh-wide rollout affects many services; preserve revision/policy. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Proxy/app success agrees; mTLS identities and distribution status healthy. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
