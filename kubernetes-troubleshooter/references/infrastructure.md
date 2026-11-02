# Targeted infrastructure expansion

## Nodes and platform discovery

Use implicated pod `spec.nodeName`, then scoped `get nodes NODE -o json` through the
helper. Inspect conditions/transition times, taints, allocatable, nodeInfo, providerID
and relevant zone/pool labels via narrow JSONPath. ProviderID/distribution hints
need confirmation; do not assume AWS from an image name. Inspect node lease
renewTime if allowed, affected DaemonSets and same-node healthy workloads. Kubelet,
runtime, kernel, host disk and cloud instance events may require an authorized host
or provider log source; do not use privileged debug pods automatically.

Discover relevant DNS, CNI and CSI by system DaemonSet/Deployment images, Service
selectors, CSI driver/storage class names and implicated pod events. Inspect API
resources only for relevant CRDs (Gateway, mesh, KEDA, VPA, Karpenter). Missing CRDs
or RBAC denial are capability limits, not an error to bypass. Follow workload owner
chains across Deployments/ReplicaSets, StatefulSets, DaemonSets, Jobs and CronJobs;
for Jobs check failure policy, retries and schedule timestamps.

## Network path

Follow client -> DNS -> Service -> EndpointSlice -> ready Pod target port -> CNI ->
node/zone -> dependency. Inspect selectors, readiness/serving/terminating conditions,
address family, named target ports, internal/external traffic policies, topology and
session affinity. EndpointSlice data is preferred over assuming legacy Endpoints.
For Ingress/Gateway inspect controller identity and accepted/resolved/programmed
conditions, route attachment, backend references and TLS hostname/expiry metadata.
Do not read TLS private-key Secrets. For policies evaluate both source egress and
destination ingress, namespace/pod label selectors, ports/protocols and additive
allow rules; include DNS egress. Mesh mTLS, authorization and retries can alter the
path. Use existing flow/trace evidence before requesting scoped active probes.

## Storage

Trace pod -> PVC -> PV -> StorageClass -> CSI controller/node -> volume attachment
and provider volume. Inspect claim phase, access modes, zone/affinity, binding mode,
capacity, mount/attach events and node pressure. PVC Bound does not prove mount or
application write success. Distinguish byte exhaustion, inode exhaustion, filesystem
read-only, I/O latency and provider throughput/IOPS throttling. Avoid filesystem
repair, detach/reattach, PV deletion or reclaim-policy edits without an explicit
change plan; rollback may not restore lost data.

## Scaling

For HPA inspect scaleTargetRef, metrics sources, requests, current/desired replicas,
conditions, events, min/max and behavior/stabilization. A missing Metrics Server is
relevant to resource metrics; custom/external metrics use separate adapters. VPA
recommendations and update policies may interact with HPA CPU/memory targets. KEDA
requires trigger health, authentication wiring and external adapter evidence;
do not retrieve credential contents. Pending capacity differs from utilization:
inspect scheduler constraints, taints, affinity, topology, quota and fragmentation.
Karpenter/Cluster Autoscaler require provisioner/node pool constraints, daemonset
overhead, provider quota/capacity, consolidation and disruption evidence.
Read NodePools/NodeClaims through the helper (`nodepools.karpenter.sh`,
`nodeclaims.karpenter.sh`). A `Launched=False` condition with a quota or capacity
reason can identify a failed launch. No current NodeClaim alone is inconclusive:
check controller health/RBAC, pool limits, constraints, events and deleted claims. Consolidation `WhenEmpty` never
repacks partly used nodes; `WhenEmptyOrUnderutilized` can churn pods without PDBs.
Pinning instance CPU so that one pod fits per node multiplies node churn with every
HPA step. Check allocatable after daemonset and kubelet overhead, not instance size.

## Cloud-specific evidence

Use provider read-only tools only when cluster identity/account/project/region and
authorization are known. Suggested existing CLI reads (substitute reviewed IDs):

- EKS: `aws eks describe-cluster --name CLUSTER --region REGION`; implicated EC2
 instance status, node group health, VPC CNI IP/ENI capacity, routes/security groups,
 EBS zone/attachment and control-plane logs if already enabled.
- AKS: `az aks show --resource-group RG --name CLUSTER`; nodepool/VMSS health,
 subnet IP availability, NSG/UDR, managed identity and disk/controller events.
- GKE: `gcloud container clusters describe CLUSTER --location LOCATION --project PROJECT`;
 nodepool/MIG health, quota, alias IP exhaustion, firewall and PD zone/attachment.

AWS reads that repeatedly decided incidents (approved read-only profile; substitute IDs):

```sh
aws cloudwatch get-metric-statistics --namespace AWS/ElastiCache --metric-name CPUCreditBalance \
 --dimensions Name=CacheClusterId,Value=CLUSTER_ID Name=CacheNodeId,Value=NODE_ID --start-time START --end-time END --period 300 --statistics Minimum
aws elasticache describe-events --source-type cache-cluster --start-time START --end-time END
aws rds describe-events --source-type db-instance --source-identifier DB --start-time START --end-time END
aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue=RESOURCE \
 --start-time START --end-time END --query 'Events[].{t:EventTime,n:EventName,u:Username}'
aws service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A
aws ec2 describe-instance-types --instance-types TYPE --query 'InstanceTypes[].{v:VCpuInfo.DefaultVCpus,m:MemoryInfo.SizeInMiB}'
```

`L-1216C47A` is the standard on-demand vCPU quota family; confirm the code for the
instance families in use. Provider events (failover, maintenance, credit
exhaustion) can provide independent evidence. Verify account, region, retention,
query filters and ingestion coverage before reporting no matching human write.
An empty audit search cannot prove automatic action or exclude human involvement;
correlate affirmative provider/controller events and actor fields. Burstable instance classes
(t-family) degrade over days as credits drain, so look back further than the
incident.

Project only needed fields; cloud outputs may contain sensitive configuration.
Do not run kubeconfig update, remote command execution, log-enabling or infrastructure
mutation as discovery. Managed control planes can hide etcd/kubelet details; report
this and correlate provider health/service incidents if available.
