# Three complete example investigations

These are **synthetic offline investigations**, not live observations or executed
remediations. Context `prod-eu`, namespace `payments`, 2026-10-31 UTC. Evidence IDs
refer to the raw fixtures in `evals/fixtures.json`. Values below are provided fixture
observations; no network or Kubernetes operation was executed to obtain them.

## 1. Checkout latency, CPU throttling and a compute regression

**Summary/impact.** Fixture 3 reports checkout p95 rising at 09:00; user-visible latency
degradation is supported, affected user count/severity is unknown. Compare 08:30-09:00
with 09:00-09:30. Historical metrics are available through approved Mimir tenancy.

**Findings.** E1 identifies tenant `eu-prod`, cluster `prod-eu` and a single kubelet
scrape. E2 reports p95 0.12s -> 0.8s, CFS throttled-period ratio .01 -> .60, application
CPU .48 cores against a .5-core limit and stable 200 RPS. E3 places added duration
in the compute span (50ms -> 650ms), while DB duration remains 30ms, node CPU 40%,
and HPA desired/Ready both 3. E4 dates compression revision 22 to 09:00; revision 21
under comparable traffic on the same node is unthrottled with p95 .12s.

**Metrics.** Latency p95 increased .68s (567%); time-series peak/mean and request p50/p99
are not supplied and cannot be computed. The .60 ratio is fraction of CFS periods
throttled, not 60% CPU lost. The .48/.5 comparison suggests sustained constraint but
needs per-container history. A next read, after verifying actual namespace/pod/job
labels in E1, is a scoped range query for each serving pod/container, for example:

```promql
sum by (namespace,pod,container) (
  rate(container_cpu_usage_seconds_total{cluster="prod-eu",namespace="payments",pod="VERIFIED_POD",container="VERIFIED_APP"}[5m])
)
```

Use the analogous scoped CFS-period ratio in the cookbook. Set the historical API
base to the approved Mimir prefix, use existing bearer/tenant configuration and
query both equal windows with sufficient scrape samples. The placeholder labels
must be resolved first; do not claim these exact reads have run.

**Assessment.** High confidence in revision 22's changed compute path as the likely
cause; throttling is a supported mechanism/contributor. DB latency (E3), node-wide
saturation (E3), HPA failure (E3) and traffic surge (E2) are weaker competing explanations.
The matched old revision (E4) supplies independent discrimination. Controlled
post-change recovery has not been observed, so intervention confirmation is absent.

**Remediation/risk.** First review revision/image/config and schema compatibility:
`kubectl --context prod-eu -n payments rollout history deployment/checkout`.
If revision 21 is compatible and explicitly approved, propose
`kubectl --context prod-eu -n payments rollout undo deployment/checkout --to-revision=21`.
The deployment name is illustrative and must be verified against owner references.
Capture current revision 22 first; returning to it is a potential rollback of the
intervention only if still compatible. A higher CPU limit is an alternative temporary
mitigation after node-capacity review; it does not remove the compute regression.
Risks include schema incompatibility, rollout disruption and shifting CPU pressure
to other pods. No change was executed.

**Verification/prevention.** At comparable 200 RPS, verify p95 approaches .12s,
compute span falls, errors remain acceptable, throttling declines and nodes/HPA
retain headroom for at least 30 minutes and multiple scaling cycles. Use a reviewed
SLO as the rollback trigger. Add revision-aware latency/compute comparisons to canaries.
Limits: synthetic summaries, no raw sample freshness/quantile buckets or post-fix data.

## 2. Slow dependency despite normal CPU

**Summary/impact.** Fixture 4 describes checkout latency at 09:00; compare 08:30-09:00
and 09:00-09:30. Checkout p95 .1s -> 1.5s affects its serving path; exact impacted
users and severity are unknown.

**Findings/metrics.** E1 shows CPU .1 cores unchanged, throttling .001 unchanged and
100 RPS stable; p95 increased 1.4s (1400%). E2 puts inventory GET critical-path time
at 40ms -> 1400ms, with checkout compute 20ms unchanged. E3 shows inventory connection
pool wait p95 1.3s and pool cap 10, while DB query duration stays 40ms. Actual metric
names, labels and raw series are not supplied: discover them before writing executable
PromQL. Peak/time mean/p50/p99 cannot be derived from the supplied summaries.

**Assessment.** Strong evidence for downstream inventory pool wait as the current
bottleneck (E2/E3). Checkout CPU constraint is contradicted by E1/E2. Slow DB execution
is less likely (E3), but the underlying cause of pool demand or connection retention
remains unresolved. Missing deployment history precludes a deployment-cause claim.
Next discriminate leaked/long-held connections vs increased concurrency or changed
pool configuration using approved pool in-use/waiter/timeouts telemetry, request
concurrency, connection hold spans and a non-sensitive config/revision diff.

**Remediation/risk.** Prioritize investigating connection lifecycle and safe
concurrency bounds; do not recommend checkout CPU changes as an established fix.
Any pool increase needs DB connection-capacity evidence and explicit approval.
Capture original cap 10 and relevant deployment configuration before a reviewed
change; restore that configuration/revision if DB saturation or errors increase.
Exact patch target/key is unknown, so no speculative patch command is provided.
Increasing the cap can overload the DB; scaling checkout could worsen the bottleneck.

**Verification/prevention.** Observe inventory wait, hold times, DB capacity, checkout
p95 and errors at comparable 100 RPS for at least 30 minutes. Recovery requires low
pool wait and restored checkout SLO without a new DB bottleneck. Alert on pool wait
and saturation, retain traces and config history. Limitations: no raw metrics, deployment
history, precise connection-lifecycle evidence or recovery; underlying root cause is open.

## 3. Restarts yesterday without historical telemetry

**Summary/impact.** Fixture 12 asks about three restarts yesterday (2026-10-30 around
09:00 UTC); current health cannot establish yesterday's impact or severity.

**Findings.** E1 finds Metrics Server plus node-exporter/kube-state-metrics endpoints,
with no approved historical query API. E2 records restartCount 3 and last termination
ReasonError/exit 1 yesterday09:00; previous logs expired. E3 records expired events,
current `kubectl top` CPU20m/memory80Mi, last rollout two days ago.

**Metrics analysis.** Metrics Server supplies current snapshots. Exporter presence
does not grant historical querying. There is no basis for CPU/memory peaks, trends,
baseline deviation or cause at yesterday's termination. Do not query an exporter
as though it offered `/api/v1/query_range`. Absence of history is a visibility limit.

**Assessment.** Observed nonzero exit is the available termination mechanism; cause
is unresolved. Misconfiguration, dependency failure, an application exception and
other external failures remain plausible. No positive evidence confirms OOM, CPU
constraint or yesterday's health. Last rollout time alone does not disprove a delayed
regression. Next seek retained sanitized app/error logs or trace IDs covering the
actual previous pod UID, and any approved historical metrics route/config supplied
by the operator. Do not repeat expired-log requests or scrape every exporter.

**Remediation/risk.** No cause-specific mutation is justified. Preserve existing
artifacts; propose retained logs/events/metrics through the normal approved process.
Installation or retention changes would need explicit approval and cost/privacy review.
No change was made, so rollback is not applicable; capture prior retention configuration
before any later change.

**Verification/prevention.** Watch new restarts and readiness through a representative
load interval, collect the next termination reason and bounded timestamped log if it
recurs. No new restarts would show current stability, not confirm yesterday's cause.
Improve retention and revision correlation. Limits: missing historical data and impact;
this investigation ends with ranked possibilities and a precise evidence request.
