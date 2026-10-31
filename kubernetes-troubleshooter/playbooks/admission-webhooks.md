# Webhook and admission failures

## Trigger and relevant resources
FailedCreate, admission timeout or rejected objects. Start with deployments; events; services; endpointslices. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource deployments
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource events
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource services
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
rate(apiserver_admission_webhook_rejection_count[5m])
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
API/owner events and webhook/controller logs, public cert metadata. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Webhook unavailable/TLS vs explicit policy rejection vs latency vs namespace selection. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Named webhook reason/timeout matches endpoint/certificate/policy evidence; rejection may be intentional. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Repair proven backend/TLS issue or fix rejected manifest; do not bypass policy by default. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
failurePolicy changes can admit unsafe workloads; retain config and explain blast radius. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Intended compliant objects admitted; policy still rejects invalid objects and latency normal. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
