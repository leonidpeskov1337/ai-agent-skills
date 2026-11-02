# Resource churn: eviction, HPA and node provisioning loops

## Trigger and relevant resources
Application intermittently slow; pods have short lifetimes without crash
restarts; many evictions; NodeClaims/nodes created and removed every day; HPA
oscillates. Start with deployments; horizontalpodautoscalers; poddisruptionbudgets;
pods; events; nodepools.karpenter.sh; nodeclaims.karpenter.sh.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource deployments --name DEPLOY
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource horizontalpodautoscalers --name HPA
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource poddisruptionbudgets
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource events --field-selector reason=Evicted
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodepools.karpenter.sh
```
The deployment projection includes probes, affinity and topology spread; the HPA
projection includes `behavior`; compare them with the intended chart values.

## Metrics and historical comparison
```promql
quantile_over_time(0.95, max by (pod) (container_memory_working_set_bytes{namespace="NS",container="APP"})[7d:5m])
max by (pod) (kube_pod_container_resource_requests{namespace="NS",container="APP",resource="memory"})
sum(increase(karpenter_nodeclaims_created_total{nodepool="POOL"}[1d]))
```
Count distinct nodes per day (see metrics guidance) and replacements by reason.

## Logs and events
Eviction messages naming memory; node MemoryPressure transitions; HPA scale events
following evictions; provisioner events creating nodes right after; consolidation
removing them later.

## Hypothesis branches
- **Memory request below real usage.** Request < p95 working set (and RSS) means the
 scheduler may overpack nodes. Verify kubelet pressure/eviction events; the
 ReplicaSet/workload controller replaces missing pods, while HPA independently
 adjusts desired count. Pending replacements may trigger provisioning; confirm
 consolidation timing before concluding a loop.
- **Application memory guard disabled.** A worker killer or memory-limit
 restart mechanism defaulted off lets workers grow until the node evicts.
- **One pod per node.** NodePool instance size pinned so only one replica fits;
 every HPA step creates or deletes a node.
- **Wrong consolidation mode.** `WhenEmpty` never compacts partially used nodes;
 aggressive underutilized consolidation without PDBs churns pods.
- **Probe mapping errors.** Rendered probe fields differ from intent (for
 example a delay value mapped into `periodSeconds`).
- **Wiring bugs.** HPA min/max taken from the wrong variable; chart default max
 applied because a value was unset; a misspelled values key silently ignored.
- **Out-of-band patches.** A field set by `kubectl patch/edit` (CPU limit,
 replicas) persists across upgrades because the release never owned it, causing
 throttling or ownership conflicts.

## Confirmation criteria
For a churn-loop claim, align eviction/pressure, workload-controller replacement,
HPA intent and provisioner/consolidation timing. Request-versus-usage and node
headroom support or weaken the under-reservation hypothesis. Wiring/probe errors
need a field-specific source/rendered comparison; out-of-band ownership needs
field-manager and deployment-history evidence. These are independent branches,
not a requirement that every listed defect co-occur.

## Recommended remediation
Evaluate request sizing against representative usage/RSS/cache and node pressure,
including bursts beyond p95; a percentile alone is not a safe sizing guarantee.
Choose limits with capacity and application behavior in view;
enable the application's memory guard aligned below the limit; choose instance
sizes that fit 2+ replicas with daemonset overhead; use memory-suited families;
add reviewed PDBs and topology spread (PDBs govern voluntary disruptions, not
node-pressure evictions); fix wiring and probe mapping; conservative HPA
behavior (test stabilization appropriate to the measured workload). Determine
field ownership and deployment-tool behavior before removing out-of-band fields;
a declare-then-remove sequence can help with some Helm three-way merges but is
not universal. Review the rendered diff and data/availability risks before approval.

## Risk and rollback
Larger requests raise node count until bin-packing settles; review cost. Probe
changes can mark pods unready; validate rendered manifests before release.

## Post-fix validation
Zero evictions for a week, NodeClaims/day down, pod lifetime up, latency p95 at
comparable load stable, cost tracked. Expect improvement over days, not minutes.
