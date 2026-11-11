# Capacity review: "should we raise max replicas / add nodes?"

## Trigger and relevant resources
A proposal to raise HPA max, node pool limits or instance size; "runs at max
every day". Start with horizontalpodautoscalers; deployments; nodes;
nodepools.karpenter.sh.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource horizontalpodautoscalers --name HPA
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource deployments --name DEPLOY
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodepools.karpenter.sh
```

## Metrics and historical comparison
Measure each layer for working hours and off-hours over 7-14 days:
1. Time at max per weekday (not just the mean replica count).
2. Pod CPU vs request (the HPA denominator) and vs limit (if any).
3. Application concurrency: worker/thread busy ratio, request queue depth.
4. Node CPU/memory on nodes hosting the workload (busiest node, not mean).
5. Latency p95 and error rate during at-max hours vs off-peak.
6. Dependency headroom: DB/cache CPU, connections, pooler limits.
7. Replicas per node, eligible node capacity and actual placement labels. Compare
   affinity/spread topology keys and nodeSelector keys/values against intended nodes:
   `kubectl --context CONTEXT get nodes -l SELECTOR -L KEY`. The common hostname
   key is `kubernetes.io/hostname`; verify live labels rather than assume a prefix.
   Missing labels can neutralize soft preferences or exclude nodes/block scheduling,
   depending on the rule. Confirm applied selectors, namespace scope and node placement.

## Logs and events
HPA events at max (`ScalingLimited`), scheduler/provisioner events, latency alerts.

## Hypothesis branches
- **Pinned by request sizing.** Pods at about 100% of a small request keep the HPA at max
 while app concurrency is low: tune request/target, not max.
- **Node CPU saturated.** Pods per node burst into each other: more replicas on
 new nodes do add CPU; changing request or spread may do the same at lower cost.
No CPU limit does not provide dedicated CPU: burst uses available node capacity
and competes according to CPU shares/weights. Usage above request plus a busy node
is a contention hypothesis, not proof that a particular request value is correct;
check runnable work, CPU modes, latency and other tenants before sizing.
- **Real demand.** Concurrency, queues and latency high at max with healthy
 dependencies: raise max, check dependency connection budget first.
- **Dependency bound.** Latency driven by DB/cache: more replicas worsen it.

## Confirmation criteria
State which layer saturates first with numbers; show latency impact at max.

## Recommended remediation
Smallest effective change (request/target, spread, instance shape, or max) with
cost delta and dependency connection impact; re-check window defined.

## Risk and rollback
More replicas add connections and nodes; higher requests change bin-packing.

## Post-fix validation
Time at max, latency p95 and node CPU at comparable working-hours load.

Correcting a soft anti-affinity key changes scoring for newly scheduled pods only
among nodes they can fit on; it does not redistribute existing pods automatically
or guarantee autoscaler expansion. Raising requests may reduce packing density,
but can instead leave pods Pending when no eligible capacity exists. Verify placement,
Pending reasons, readiness and node cost after any separately approved change.
