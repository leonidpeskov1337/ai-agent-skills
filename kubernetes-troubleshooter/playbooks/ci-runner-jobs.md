# CI runner jobs: Pending, stuck or slow job pods

## Trigger and relevant resources
CI jobs fail with "timed out waiting for pod to start", "stuck: no runners
online", helper image pull errors, or jobs wait minutes before starting. Start
with pods in the runner job namespace; events; nodeclaims.karpenter.sh;
nodepools.karpenter.sh; the runner Deployment/ConfigMap fields that set job
requests, tags and helper image.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace RUNNER_NS --resource pods --field-selector status.phase=Pending
python scripts/collect_evidence.py --context CONTEXT --namespace RUNNER_NS --resource events --field-selector reason=FailedScheduling
python scripts/collect_evidence.py --context CONTEXT --namespace RUNNER_NS --resource nodeclaims.karpenter.sh
python scripts/collect_evidence.py --context CONTEXT --namespace RUNNER_NS --resource nodepools.karpenter.sh
```
NodeClaims/NodePools are cluster-scoped; NS is ignored. Read job pod requests
for every dimension: cpu, memory **and ephemeral-storage**, plus helper/service
containers.

## Metrics and historical comparison
```promql
sum(kube_pod_container_resource_requests{namespace="RUNNER_NS",resource="ephemeral_storage"}) by (pod)
quantile_over_time(0.95, max by (pod) (container_fs_usage_bytes{namespace="RUNNER_NS"})[7d:5m])
sum(kube_node_status_capacity{resource="cpu"} * on(node) group_left(label_karpenter_sh_nodepool) kube_node_labels{label_karpenter_sh_nodepool="POOL"})
```
Treat container_fs_usage_bytes as partial until writable layers, logs and
disk-backed emptyDir across job/helper/service containers are covered; max by
pod can undercount multi-container demand. Do not reduce pod requests using that
partial statistic alone. Compare requested vs total measured usage and regional
account vCPU usage (including other clusters/VMs) versus the correct quota family.
Include the failed launch size: current usage below quota may still lack room.

## Logs and events
Karpenter controller logs/events with `VcpuLimitExceeded`,
`InsufficientInstanceCapacity`, `MaxSpotInstanceCountExceeded`; scheduler
`Insufficient ephemeral-storage`; runner logs with pod start timeouts; image pull
errors for helper images from an upstream registry (503/429).

## Hypothesis branches
- **Request shape forces huge nodes.** Ephemeral storage or memory request far
 above p95 limits jobs per node by disk/memory; the provisioner picks large
 high-vCPU instances that run at low CPU. Account vCPU quota fills; new
 NodeClaims fail; jobs time out Pending.
- **Single instance family.** `InsufficientInstanceCapacity` in one family/zone.
- **No matching runner.** Jobs without required tags stay pending when no
 runner accepts untagged jobs; this is a job config issue, not capacity.
- **Overrides.** Pipeline variables may override cpu/memory requests within
 allowed maxima but not every dimension (for example ephemeral storage).
 Verify which dimensions are overridable before calling a fix futile.
- **Upstream registry outage.** Helper/service images pulled from a public
 registry fail; cached nodes keep working (cohort split by node age).

## Confirmation criteria
Provisioner events show the quota/capacity error at the times jobs were
Pending; launched vCPU approaches quota; job pods' requests divided into node
allocatable explains instance choice; usage percentiles show the over-request.

## Recommended remediation
Right-size job requests to measured p95/p99 per dimension with headroom; widen
instance families/generations; request a quota increase as a buffer, not the
fix; alert at 85% of quota; mirror helper images to an internal registry.

## Risk and rollback
Lower requests risk eviction for outlier jobs; keep per-job override maxima so
heavy pipelines can opt up. Record previous runner config and revision.

## Post-fix validation
Launched vCPU peak and instance sizes drop, no quota/capacity errors for a week of
working days, job start latency normal, eviction count unchanged.
