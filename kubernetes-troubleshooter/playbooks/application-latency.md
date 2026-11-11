# Application latency and 5xx errors

## Trigger and relevant resources
Latency percentile or error rate rises. Start with pods; deployments; services; horizontalpodautoscalers. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource deployments
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource services
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
histogram_quantile(0.95,sum by(le,service)(rate(http_request_duration_seconds_bucket[5m])))
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Ingress/app errors, existing traces, rollout events and dependency logs. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
CPU/throttling vs downstream latency vs queueing vs traffic mix vs deployment vs storage/network. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

Production-proven discriminators:
- Synthetic probe slow: split by phase; if DNS/connect/TLS are small and
 processing is large, investigate the time to first response byte, including
 request transmission, proxies, backend work and response transit. Traces or
 server/network evidence are needed to locate the delay.
- Working vs waiting: per-pod CPU low, worker/thread busy high and request queue
 growing = blocked on a dependency (see [managed dependencies](managed-dependencies.md)).
 CPU high on the busiest node with several replicas per node = node CPU contention.
- Segment working hours vs off-hours and look at the busiest pod's queue, not the mean.
- Align probe spikes with the server request queue (for example Puma
`puma_queued_connections`) with matched timestamps, scrape coverage and step.
Matching spikes with healthy dependency signals strengthen local queue/capacity
hypotheses; they do not exclude an uninstrumented backend or a shared bottleneck.
- Attribute load by endpoint mix when request logs are unavailable: a burst of
per-resource GETs (hooks, variables, approval rules, access tokens) on workdays
only is consistent with IaC/provider refresh, but UIs, pollers and other automation
can produce similar patterns. Correlate authorized job schedules, source/workload
identity and revisions before attribution. Use low-cardinality route/operation
labels, not raw URLs, resource IDs or tokens. Compute server-time share from matched
request-duration sum rates for the operation and total; state the denominator and
that concurrent request time is not CPU time or wall-clock utilization.
- Compare several same-weekday/time-of-day windows when available, with matched
traffic/revision/coverage; one offset week can be atypical.
- After a fix plus an upgrade on the same day, report the improvement as
 confounded and provisional.

## Confirmation criteria
Compare time windows/cohorts and critical path; require independent evidence beyond correlation. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Fix demonstrated bottleneck; propose canary/rollback or capacity action with evidence. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Scaling can overload dependency; rollback may conflict with schema. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
p50/p95/p99, errors, RPS and queue depth recover at comparable load with healthy dependencies. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
