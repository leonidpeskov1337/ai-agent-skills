# Ingress and Gateway failures

## Trigger and relevant resources
External 404/502/503, route rejected or load balancer failure. Start with ingresses; gateways.gateway.networking.k8s.io; httproutes.gateway.networking.k8s.io; services. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource ingresses
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource gateways.gateway.networking.k8s.io
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource httproutes.gateway.networking.k8s.io
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Controller events/logs, Accepted/ResolvedRefs/Programmed conditions. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Route/host/path vs backend health vs LB provisioning vs controller/class mismatch. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Route conditions or controller error match request host/path and unhealthy backend hop. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Correct proven route/class/backend reference or provider LB issue. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Exposure/routing changes affect external users; preserve prior routes. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Route programmed; original host/path succeeds with healthy backend and expected TLS. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
