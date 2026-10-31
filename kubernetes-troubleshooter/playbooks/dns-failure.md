# DNS failures

## Trigger and relevant resources
Name lookup timeouts, SERVFAIL or unexpected NXDOMAIN. Start with services; endpointslices; deployments; networkpolicies. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource services
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource endpointslices
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource deployments
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
sum by(rcode)(rate(coredns_dns_responses_total{rcode!="NOERROR"}[5m]))
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Bounded CoreDNS logs/events, existing query trace and affected client errors. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
CoreDNS saturation/forwarder outage vs DNS egress policy vs wrong search name vs node-local cache. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Compare clients/nodes and response codes; match time/zone/upstream errors and effective DNS traffic path. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Correct proven CoreDNS/upstream/policy issue; propose scoped approved query if passive evidence insufficient. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
DNS changes have cluster blast radius; preserve prior config and replicas. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Lookup success and latency recover for affected and healthy names across nodes. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
