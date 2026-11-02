# Select a playbook by symptom

Choose one or two likely starting points, then follow evidence across domains.
These are hypothesis branches, not a checklist to execute in full.

For linked GitOps sync/source/component symptoms, start with
[Argo CD relevance and routing](../ArgoCD/README.md) before deeper investigation.

- [CrashLoopBackOff](crashloopbackoff.md): Repeated restarts and backoff after container starts.
- [OOMKilled](oomkilled.md): Last termination reason OOMKilled or exit 137.
- [ImagePullBackOff](imagepullbackoff.md): Image pull fails before application startup.
- [Pending pods](pending-pods.md): Pod remains Pending, including init/volume waits.
- [FailedScheduling](failed-scheduling.md): Scheduler reports no feasible nodes.
- [NodeNotReady](node-not-ready.md): Ready condition False/Unknown or lost heartbeats.
- [Node pressure and evictions](node-pressure.md): MemoryPressure, DiskPressure, PIDPressure or evicted pods.
- [CPU throttling](cpu-throttling.md): High latency or CFS throttling.
- [Memory growth and excessive usage](memory-growth.md): Working set/RSS grows or high memory utilization.
- [DNS failures](dns-failure.md): Name lookup timeouts, SERVFAIL or unexpected NXDOMAIN.
- [CNI and pod networking](cni-networking.md): Cross-pod/node packet loss, sandbox creation failures.
- [Service and EndpointSlice routing](service-routing.md): Service fails while some backend pods appear healthy.
- [Ingress and Gateway failures](ingress-gateway.md): External 404/502/503, route rejected or load balancer failure.
- [TLS and certificate issues](tls-certificates.md): Expired certificate, handshake error or hostname mismatch.
- [NetworkPolicy restrictions](network-policy.md): Only selected clients, namespaces or ports fail.
- [PVC and storage failures](pvc-storage.md): Pending claim, FailedMount, attach failures or slow writes.
- [HPA VPA and KEDA failures](workload-scaling.md): Replica demand unmet, metrics unavailable or oscillating.
- [Karpenter and Cluster Autoscaler](node-autoscaling.md): Pending pods persist despite autoscaler.
- [Control-plane and API server failures](control-plane.md): API timeout, 429/5xx or slow admission.
- [etcd-related issues](etcd.md): Control-plane latency with storage/leader symptoms.
- [Application latency and 5xx errors](application-latency.md): Latency percentile or error rate rises.
- [Service mesh failures](service-mesh.md): Proxy 503, mTLS/authorization or sidecar readiness errors.
- [Deployment regressions](deployment-regression.md): Intermittent failures after rollout or only one revision fails.
- [RBAC and authorization errors](rbac-authorization.md): Forbidden/Unauthorized from user or controller.
- [Resource quota and LimitRange failures](quota-limitrange.md): Admission rejects pods or rollout creates no pods.
- [Webhook and admission failures](admission-webhooks.md): FailedCreate, admission timeout or rejected objects.
- [GPU scheduling and utilization](gpu.md): GPU pod Pending or allocation/utilization failure.

Production-derived playbooks (cross-cutting; start here when the symptom matches):

- [Managed dependencies](managed-dependencies.md): Pods slow/NotReady with low CPU; cache/DB/pooler saturation, burst credits, failover.
- [CI runner jobs](ci-runner-jobs.md): Job pods Pending/timeouts, runner tags, request shapes, account vCPU quota.
- [Resource churn and eviction loops](resource-churn-eviction-loop.md): Short pod lifetimes, evictions, daily node churn, HPA oscillation.
- [Change attribution](change-attribution.md): Unexpected change; who or what changed it.
- [Capacity review](capacity-review.md): Proposals to raise max replicas, node limits or sizes.

Quick routing for ambiguous symptoms:

| Observation | Start with |
|---|---|
| Ready pods drop, HPA desired unchanged | Pod/controller availability; managed dependencies if timeout/wait evidence links them |
| Pods short-lived, no restarts, evictions | Resource churn and eviction loops |
| Jobs Pending, provisioner quota/capacity errors | CI runner jobs, then Karpenter |
| "Not yet valid"/stale certificate after an apply | TLS, then change attribution |
| HPA at max every working day | Capacity review |
| Probe slow, processing phase dominates | Application latency |
