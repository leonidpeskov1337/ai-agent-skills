# Metrics analysis and adaptable PromQL

Read the relevant section only: [preconditions](#preconditions-and-interpretation),
[CPU/memory](#cpu-and-memory-starting-points), [network/storage](#network-dns-and-storage),
[application/scaling](#application-scaling-and-control-plane),
[incident patterns](#patterns-from-the-supplied-incident-summaries),
[statistics](#execution-and-statistics).

## Preconditions and interpretation

Discover metric names/types and label sets first. All examples below assume those
series exist; scope to the selected cluster, namespace and workload before running.
`namespace` and `pod` alone are unsafe in a multi-cluster backend. Add an actual
cluster matcher when available or use a verified tenant with only the target cluster.
OTel/cloud/native histograms may need different names, units and labels.

Inspect raw series for `job`, `instance`, `endpoint`, `service`, `cluster`, replica
and container identity. Select one authoritative scrape path; use backend HA
deduplication where configured. Do not blindly sum duplicate kubelet/cAdvisor
scrapes or use `max` to hide duplicate topology. Remove terminated/stale container
identities only with evidence; pod reuse can mix historical series.

Choose a rate window with several scrapes (normally at least four intervals) and
a range step that resolves the incident. Compare equal before/during/after windows
and comparable traffic. Keep timezone/clock skew and deployment changes in view.
`rate` handles counter resets; rate before sum. Missing samples, NaN, Inf, reset
artifacts, downsampling and retention affect confidence. Do not replace absent or
undefined denominators with zero. The epsilon in the throttling example prevents a
division failure but a zero periods denominator still means unobservable activity.

Join only compatible label sets and units; verify uniqueness before `group_left`.
Requests and limits are usually kube-state-metrics gauges; names can vary by version.
Do not average pod utilization ratios for HPA: inspect HPA spec, per-container
requests, missing samples, readiness, stabilization and controller conditions.

## CPU and memory starting points

The following are starting templates. Add verified cluster/job/scope matchers to
both sides of each ratio and keep container granularity when identifying a bottleneck.

```promql
sum by (namespace, pod) (
 rate(container_cpu_usage_seconds_total{container!="",container!="POD"}[5m])
)
```

Units: CPU cores (multiply by 1000 for millicores), not percent. Compare to requests
and limits in cores, including sidecars, using matched populations.

```promql
sum by (namespace, pod) (
 rate(container_cpu_cfs_throttled_periods_total{container!="",container!="POD"}[5m])
)
/
clamp_min(
 sum by (namespace, pod) (
   rate(container_cpu_cfs_periods_total{container!="",container!="POD"}[5m])
 ), 1e-9
)
```

This measures fraction of CFS periods with throttling, not percent CPU lost or
throttled seconds. Check both counters exist and share labels. Inspect individual
containers and `container_cpu_cfs_throttled_seconds_total` where available. Runtime,
cgroup version, OS and exporter configuration affect availability and interpretation.
Correlate with application CPU demand, request volume, latency, node saturation,
HPA and downstream spans; no universal threshold establishes cause.

```promql
sum by (namespace, pod) (
 container_memory_working_set_bytes{container!="",container!="POD"}
)
```

Working set is bytes; it is not RSS, a precise live heap size or proof of a leak.
Compare RSS/cache/usage, limit and termination reason. OOM can be cgroup-local or
node-level. Peaks can disappear between scrapes; no observed peak does not rule out OOM.

Requests/limits (check names and unit labels):

```promql
sum by (namespace,pod) (kube_pod_container_resource_requests{resource="cpu",unit="core"})
sum by (namespace,pod) (kube_pod_container_resource_limits{resource="memory",unit="byte"})
increase(kube_pod_container_status_restarts_total{namespace="payments"}[30m])
max_over_time(container_memory_working_set_bytes{namespace="payments",container!="",container!="POD"}[30m])
1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))
1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
```

Node non-idle includes I/O wait; inspect individual CPU modes and run queue before
calling CPU saturated. Match exporter instance to Kubernetes node and topology.
Fit a memory growth slope over multiple load/GC cycles; a two-point increase alone
cannot distinguish leaks, caches and changed workload.

## Network, DNS and storage

```promql
sum by (namespace,pod) (rate(container_network_receive_bytes_total{namespace="payments",interface!="lo"}[5m]))
sum by (instance) (rate(node_network_receive_drop_total{device!="lo"}[5m]))
rate(node_netstat_Tcp_RetransSegs[5m])
sum by (rcode) (rate(coredns_dns_responses_total{rcode!="NOERROR"}[5m]))
histogram_quantile(0.99, sum by (le) (rate(coredns_dns_request_duration_seconds_bucket[5m])))
1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}
node_filesystem_files_free / node_filesystem_files
rate(node_disk_read_time_seconds_total[5m]) / rate(node_disk_reads_completed_total[5m])
rate(node_disk_written_bytes_total[5m])
kubelet_volume_stats_available_bytes / kubelet_volume_stats_capacity_bytes
```

Container network metrics may belong to a shared pod network namespace: sum only
after checking sandbox/container duplication. Node virtual interfaces can count the
same traffic twice. Retransmissions are node-wide unless flow metrics exist. NXDOMAIN
may be normal search-path traffic; compare query mix and successful traffic. DNS
histograms require consistent buckets. Disk mean time is seconds/operation, not p99;
zero completed operations is undefined. Select actual devices/mountpoints; cloud
volume throttling needs provider metrics. PVC gauges may not be exported by the CSI.
Node drops do not establish a NetworkPolicy deny; use effective policy or authorized
flow verdicts. Cross-zone conclusions require topology and flow labels.

## Application, scaling and control plane

```promql
sum(rate(http_requests_total{service="checkout",status=~"5.."}[5m]))
/
sum(rate(http_requests_total{service="checkout"}[5m]))
histogram_quantile(0.95, sum by (le,service) (rate(http_request_duration_seconds_bucket{service="checkout"}[5m])))
kube_deployment_status_replicas_available{namespace="payments"}
kube_horizontalpodautoscaler_status_desired_replicas{namespace="payments"}
histogram_quantile(0.99, sum by (le,verb) (rate(apiserver_request_duration_seconds_bucket[5m])))
histogram_quantile(0.99, sum by (le,instance) (rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m])))
```

HTTP names/status labels are application-specific. Guard the error ratio with
request volume; zero traffic gives no availability evidence. For classic histograms,
sum bucket rates preserving `le` then quantile; never average per-pod p95s. For native
histograms use the appropriate histogram expression instead. Compare p50/p95/p99,
RPS, error rate, queue depth and trace critical paths. Scheduling latency and queue
metrics depend on scheduler/exporter version; discover them rather than assume names.
Control-plane/etcd absence is common in managed clusters, not proof of health.

## Patterns from the supplied incident summaries

### Segment by time of day and by unit

Fleet-wide 7/14-day means hide daily saturation. Report working-hours and
off-hours separately and the hours per day at a limit:

```promql
# approximate daily hours at max from regularly sampled, complete data
avg_over_time((kube_horizontalpodautoscaler_status_desired_replicas{cluster="CLUSTER",namespace="NS",horizontalpodautoscaler="HPA"}
 >= bool on(cluster,namespace,horizontalpodautoscaler)
 kube_horizontalpodautoscaler_spec_max_replicas{cluster="CLUSTER",namespace="NS",horizontalpodautoscaler="HPA"})[1d:5m]) * 24
```

Check coverage before converting samples to hours: scrape gaps and lookback
reuse bias the estimate; report approximate duration over the covered interval.
Use the busiest pod/node (`max`, `topk`) beside the mean. Define actual business
hours and timezone, including DST; `day_of_week()`/`hour()` are UTC, not local time.
Resolve "today"/"yesterday" to actual dates before choosing comparison days.
Verify weekday/holiday and sample-window claims against timestamps; if dates are
missing, qualify the comparison rather than asserting matched days or full coverage.
For 14-day analysis, query bounded chunks compatible with the helper's seven-day
range limit. Do not average daily p95 values to claim a full-window p95.

### HPA utilization is relative to the request

`target utilization = usage / request`. A pod running at 100% of a small request
can drive HPA demand toward max even when user-facing concurrency is low;
verify the target ratio, tolerance, other metrics and scaling conditions. Before concluding "needs
more replicas", compare: usage vs request, node CPU, application concurrency
(worker/thread busy ratio, queue depth) and latency. Raising the request makes the
HPA less eager and changes bin-packing; raising the target does the same for the
same request. HPA desired vs current:

```promql
kube_horizontalpodautoscaler_status_desired_replicas{namespace="NS"}
kube_horizontalpodautoscaler_status_current_replicas{namespace="NS"}
kube_deployment_status_replicas_available{namespace="NS"}
```

Desired unchanged while availability drops is not evidence of scale-down.
Inspect probes, crashes/OOM, rollout, eviction, Pending replacements and node loss
before choosing a dependency explanation.

### No container CPU limit does not exclude CPU pressure

Without a container quota, inspect pod/ancestor cgroup limits, historical limit
changes and counter rates before dismissing throttling. Zero or absent series do
not prove CPU is plentiful: the pod still competes for the node. Check node CPU on
the nodes that host the workload. Join node-exporter (`instance` = IP:port) to
pods via kube-state-metrics `host_ip`:

```promql
max by (node) (
 label_replace(1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])),
               "host_ip", "$1", "instance", "([^:]+):.*")
 * on (host_ip) group_left(node)
 max by (host_ip, node) (kube_pod_info{namespace="NS",created_by_name=~"WORKLOAD.*"})
)
```

Pods per node matters: four CPU-bursting pods on one node saturate it even with
low requests.

### Working set is not RSS

`container_memory_working_set_bytes` includes active page cache. I/O-heavy
workloads (git storage, databases, search) can have cache-heavy working sets,
but reclaim may be slow or insufficient. Compare RSS/cache, usage/limits,
cgroup pressure/events, OOM and node signals; cgroup OOM can occur without
node MemoryPressure. Missing failures do not prove safe headroom.

### Counting nodes and avoiding double counts

Autoscaler gauges can be emitted by several controllers or clusters in one tenant.
Count distinct nodes from pod placement, scoped to the cluster:

```promql
count(count by (node) (kube_pod_info{cluster="CLUSTER",namespace="NS",node!=""}))
```

NodeClaim/node churn per day (Karpenter-style, names vary by version):

```promql
sum(increase(karpenter_nodeclaims_created_total{nodepool="POOL"}[1d]))
sum by (reason) (increase(karpenter_nodeclaims_disrupted_total{nodepool="POOL"}[1d]))
```

If unavailable, use retained UID/name/creation histories for unique nodes across
each day, not one instant count. A range query samples membership and may miss
short-lived nodes; state coverage and keep concurrent-node counts separate from
creations. Exclude unscheduled pods and verify cluster/job deduplication.

### Pod lifetime and replacement reasons

```promql
count by (reason) (kube_pod_container_status_last_terminated_reason{namespace="NS"})
sum(increase(kube_pod_container_status_restarts_total{namespace="NS"}[1d]))
time() - kube_pod_start_time{namespace="NS"}
```

A low current age with zero restarts suggests recent creation/replacement; it
does not exclude a first startup failure or prove a historical lifetime. Track
UID creation/deletion intervals and reasons across replacements. Correlate with eviction events and node
pressure, then with autoscaler events.

### Requests vs usage per dimension (including ephemeral storage)

Right-size every requested dimension with p95/p99 over a representative window:

```promql
quantile_over_time(0.99, max by (pod) (container_memory_working_set_bytes{namespace="NS",container="C"})[7d:5m])
quantile_over_time(0.95, max by (pod) (container_fs_usage_bytes{namespace="NS",container="C"})[7d:5m])
```

`container_fs_usage_bytes` alone is not total pod ephemeral storage: verify
coverage of writable layers, logs and disk-backed emptyDir volumes across all
app/helper/service containers (memory-backed emptyDir is accounted as memory).
The example is a container-filesystem diagnostic, not a safe request-sizing
denominator by itself. Use supported kubelet/provider volume accounting and
check exporter/device semantics before adding series.

An oversized ephemeral-storage or memory request can force very large instances
with low CPU use and exhaust account-level vCPU quota; CPU usage looks fine.

### Metric provenance and semantics

Before trusting a metric, confirm the exporter, units, and whether it is a
timestamp, a duration or a remaining time (a "licence" gauge may be seconds
remaining, not an epoch). Read HELP text where the backend exposes it
using `query_metrics.py --base-url URL --mode metadata --selector NAME` and
cross-check one value against a known fact. Check type, help and unit when present.
Application-level queue metrics may come from a separate exporter, not the app.

### Blackbox probe phases

```promql
avg by (phase) (probe_http_duration_seconds{instance="URL"})
```

Small DNS/connect/TLS phases make connection setup less likely to dominate.
Large `processing` measures time until the first response byte after connection
acquisition: request transfer, proxies, server work and network transit may all
contribute. Correlate with server traces/queues and network evidence before
calling it a backend cause. Inspect individual target probes as well as means.

## Execution and statistics

```sh
python scripts/query_metrics.py --base-url https://approved-gateway/prometheus --mode range --query 'rate(container_cpu_usage_seconds_total{namespace="payments",pod="api-abc",container="api"}[5m])' --start 1793444400 --end 1793448000 --step 60
python scripts/analyze_metrics.py sanitized-response.json
```

The summarizer computes finite-sample mean, peak, nearest-rank time-sample p95,
endpoint change and change/second per series. It drops non-finite values explicitly.
Use rate-derived data for counters. Its p95 is not request p95; gaps and uneven
sample spacing bias summaries. Compare matching baseline/incident summaries and
report both absolute change and deviation (undefined if baseline zero). Retain exact
queries/time windows in the report, and assess raw sample freshness separately.
