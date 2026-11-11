# Managed dependencies: cache, database, pooler, shared storage

## Trigger and relevant resources
Pods slow or NotReady while their own CPU is low; latency rises across every
replica at once; connection counts jump; readiness flaps with no rollout and no
HPA decision. Start with deployments DEPLOY; pods; horizontalpodautoscalers;
endpointslices. Locate the dependency first: cache/database/pooler/storage may be
managed externally or run inside the cluster. Substitute verified names/context; run only the
read that discriminates the current hypotheses.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource horizontalpodautoscalers --name HPA
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource deployments --name DEPLOY
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource events --field-selector involvedObject.kind=Pod,reason=Unhealthy
```
Then provider reads from [infrastructure](../references/infrastructure.md):
per-node CPU, engine CPU, burst credit balance, memory, swap, connections,
failover/maintenance events and audit trail for the same window.

## Metrics and historical comparison
```promql
kube_horizontalpodautoscaler_status_desired_replicas{namespace="NS"}
kube_deployment_status_replicas_available{namespace="NS"}
sum(rate(container_cpu_usage_seconds_total{namespace="NS",container="APP"}[5m]))
```
Flat desired with falling availability rules out a matching scale-down decision,
not local crashes, evictions, rollout or node failure. Low CPU suggests possible
blocking; confirm through traces, probe errors or thread state. Add the
application's own concurrency signal (worker/thread busy, queue depth) and the
dependency's connection count. Choose sufficient history for the credit pattern (often days); credits can drain
gradually or rapidly. Respect the incident budget and query bounded time chunks.

## Logs and events
Readiness failures with timeouts on dependency calls; application logs naming
the cache/DB host; provider events (failover, node replacement, maintenance);
pooler logs showing growing server connections or waiting clients.

## Hypothesis branches
- **Burstable instance out of credits.** Credit balance at or near 0, CPU pinned at
 the baseline percentage, latency step change. Single-threaded engines (Redis/Valkey)
 saturate one core first.
- **Memory pressure/swap on the dependency.** Memory above 90%, swap > 0, latency
 grows; test whether this is active pressure rather than old inactive swap. For
 databases, slower transactions can make a transaction-mode pooler use more
 server connections while client demand is flat (feedback loop).
- **Connection storm.** Clients reconnect on timeout; connection count doubles
 during the stall. Cause or effect? Check which rose first.
- **Provider failover.** Event at T; brief total outage, then recovery.
- **Slow external API behind a controller.** Workqueue depth rises with flat adds
while reconcile time and the controller's outbound-call latency rise together;
process CPU and Go scheduler latency appear unchanged at sufficient resolution.
These weaken some local saturation hypotheses but do not rule them out: check
throttling, node run queue, GOMAXPROCS, GC and locks, process restarts, active workers
and scrape gaps. Correlated controllers in one process are not independent evidence.
A slower outbound-call metric establishes client-observed call delay; distinguish
client retries/rate limiting/pool waits, network/egress and remote service time.
Compare clients of other
endpoints on the same egress path to separate the remote service from NAT,
proxy or DNS. See controller metrics in [metrics](../references/metrics.md).
- **App regression.** New query pattern after rollout; compare revisions.

## Confirmation criteria
The dependency's saturation signal precedes the pod symptom, both recover
together (or after failover), the application CPU is low during the stall, and the
available provider/controller evidence supports the mechanism. Report audit
coverage and any missing writes as a limitation, not proof of no human involvement. A failover event alone confirms the mechanism
of recovery, not the cause.

## Recommended remediation
For confirmed sustained credit-bound demand, compare non-burstable capacity and
cost with workload changes. Size memory for
the working set with headroom and no swap; cap pooler server connections below
the DB limit. Do not add application replicas while the dependency is the
bottleneck: each replica adds connections and load. Change via IaC.

## Risk and rollback
Class changes can trigger failover or a maintenance window; schedule it and
record the previous class. Larger classes cost more; quote the monthly delta.

## Post-fix validation
Credit balance/CPU/memory/swap and connection counts stable through at least one
full working week; application p95 and readiness stable; no new failover events.
Note confounders (simultaneous upgrades).
