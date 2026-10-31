# Metrics analysis and adaptable PromQL

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
