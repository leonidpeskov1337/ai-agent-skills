# Real incident patterns (sanitized)

User-supplied sanitized summaries described as production investigations of a self-hosted Git platform on a
managed Kubernetes cluster with a node provisioner, managed cache, managed
relational database, connection pooler and shared file storage. Names, numbers
rounded; underlying artifacts/outcomes were not independently verified here.
Use them as reported reasoning patterns, not thresholds or this skill's live
findings. Offline evaluation fixtures are explicitly synthetic.

## 1. Slow application and node churn: eviction loop

- Symptom: intermittent slowness; 186-291 nodes created per week for one pool.
- Evidence: web pod memory request 4 GiB vs p95 working set 5.6 GiB; the
 application's worker memory guard was disabled by a chart default; evictions
 named memory; the workload controller replaced pods; HPA desired-count changes must be
 distinguished separately; the provisioner added nodes; the pool was
 pinned so one pod fitted per node; consolidation removed nodes later.
- Also found: readiness delay rendered into `periodSeconds`; a second workload's
 HPA min wired to the wrong variable and max unset (chart default); a misspelled
 values key silently ignored; an out-of-band CPU limit throttling 37-59% that
 survived upgrades and took two releases to remove (declare, then delete).
- False alarm avoided: storage pods' working set near limit was page cache;
 no reported MemoryPressure, evictions or OOM. This explains the suspected
 high working set but does not by itself prove zero future memory risk.
- Fix: memory request >= p95 with limit above peak, memory guard below the
 limit, instance sizes fitting 2+ replicas, memory-suited families, PDBs,
 conservative HPA behavior, chart-native metrics.
- Outcome: node creations -88% to -94%, cost -39%, zero evictions.

## 2. CI jobs Pending: account vCPU quota exhausted

- Symptom: jobs fail "timed out waiting for pod to start"; provisioner events
 `VcpuLimitExceeded`; some `InsufficientInstanceCapacity` in a single family.
- Evidence: job pods requested 20 GiB ephemeral storage (p95 used 2 GiB) and
 16 GiB memory (p99 3.3 GiB); only about 7 jobs fitted per node's disk, so the provisioner
 launched 48-64 vCPU nodes at about 13% CPU requested; launched vCPU peaked at 800-990
 against a quota of about 1,400. Those pool snapshots alone do not account for
 the full regional quota or failed launch size; reconcile other clusters/VMs,
 quota-family scope and timestamps before claiming they demonstrate exhaustion.
- Fix: right-size requests per dimension from 7 days of usage (8,100 pods);
 widen instance families; quota increase as buffer; alert at 85% of quota.
- Lesson: pipeline variables may override cpu/memory but not ephemeral storage;
 check which dimensions are overridable.

## 3. "Webservice scaled 8 -> 1 -> 6"

- Evidence: HPA desired stayed 8 throughout; available dropped; pods NotReady
 with CPU about 5%; worker threads blocked on the cache; the managed cache was a
 burstable micro instance with 0 CPU credits, 98% memory and swap; provider
 failed over automatically; audit trail had no human writes; connections to
 the cache rose from 1.2k to 2.8k during the stall.
- Conclusion in the supplied summary: availability loss, not a matching HPA
 scale-down; provider events support failover, while audit absence alone cannot
 exclude human involvement. Proposed fix: non-burstable cache for confirmed
 sustained credit-bound demand.

## 4. Database memory pressure feedback loop

- Evidence: database freeable memory low, swap growing, query latency up;
 pooler server connections climbed while client connections stayed flat; then
 failover.
- Lesson: in transaction mode, slower queries hold server connections longer,
 so the pooler opens more; more replicas would have worsened it.

## 5. Signing failure "certificate not yet valid"

- Evidence: client clock correct; served certificate NotBefore in the future
 relative to the job; an IaC pipeline applied an older module version that
 re-published a stale certificate.
- Lesson: attribute via pipeline history and module versions before blaming
 the signing tool or clocks.

## 6. "Should max replicas go from 8 to 12?"

- First answer claimed the cap was only reached during incidents (14-day mean
 4.4). The user reported 8 replicas every working day; re-measurement showed
 about 8 h/weekday at max. The claim was retracted explicitly.
- Layers measured: app thread busy p50 4% / p90 33%; pod CPU at about 100% of a
 1.5-core request (HPA denominator); no container CPU limit and no observed throttle rates (pod/ancestor quota
 and history still require checking); busiest
 node CPU p90 98% with 4 pods per node; memory 82-88% of request.
- Decision: raise CPU request and HPA target rather than max; fix cache and
 database first; re-check after 1-2 weeks.

## 7. Upstream registry outage

- Evidence: helper image pulls failed with 503 from a public registry token
 endpoint; nodes with cached images unaffected.
- Fix: mirror helper images internally.

## 8. Verifying a fix confounded by an upgrade

- Probe average 0.56 s -> 0.26 s and app p95 1.28 s -> 0.49 s in working hours
 after a cache resize, a DB resize and an application upgrade on the same day.
- Report: improvement real but not attributable to one change; provisional
 until a full working week.

## 9. Probe latency with packed replicas and an ineffective topology key

User-supplied generalized production report; measurements and follow-up outcomes
were not independently reproduced by this repository's maintainer.

- Reported probe processing time was 2.5-3.3 s alongside 100-246 queued requests;
  observed dependency p95 stayed flat. Eight replicas shared three eight-vCPU
  nodes; two nodes were reported at 94-97% busy. CPU mode detail still matters.
- The configured soft anti-affinity used `topology.kubernetes.io/hostname`, which
  was absent on the intended nodes. Verify actual node labels, eligible capacity
  and applied selectors rather than treating a label prefix as universally valid.
- Endpoint mix attributed 34% of measured server request time to provider-refresh
  operations in the supplied report. Similar GET patterns are only attribution
  leads without corroborating automation/source evidence; that share is not CPU.
- One offset week was atypically quiet. Multiple comparable weekdays changed the
  traffic conclusion and required an explicit retraction of the first claim.
- Follow-up: correcting the key alone did not redistribute pods. Soft preferences
  rank feasible nodes for new placements; they do not mandate rebalancing or new
  capacity. In this case, the CPU request change reduced packing. Requests must be
  sized against measured demand, available nodes, Pending risk and cost, not a
  universal high-node-CPU threshold. The supplied result does not validate every
  concurrent change independently.

## 10. Controller backlog with slow client-observed external API reads

User-supplied retrospective report; the repository has not rerun the investigation.

- Reported depth rose from zero to about 300 for roughly ten minutes, once in
  seven days. Adds were approximately 2.7/s and mean reconcile time rose from
  0.5 s to 5.4 s: about 14.6 occupied workers under steady-state assumptions,
  compared with a maximum of ten. This estimates a service-capacity shortfall,
  not the root cause or a safe new worker count.
- Several controllers slowed together but shared one process, making that weak
  discrimination between local and external causes. Scoped metric-name discovery
  found an outbound-call metric: observed read duration rose from 0.26 s to 2.77 s,
  while connect time, process CPU, scheduler latency, restarts and errors were
  reported flat. This supports delay during client-observed calls; instrumentation
  boundaries and runtime resolution still limit the conclusion.
- A peer cloud client spiked in the same minute but also spiked on normal days.
  The remote service versus shared-egress mechanism remained unresolved. Flat
  scheduler latency does not categorically eliminate CPU starvation, GC or locking.
- The supplied investigation treated the alert as informational. Alert-duration,
  concurrency or polling changes require independent impact/recurrence and quota
  evidence; the skill does not automatically suppress or tune alerts from this case.
