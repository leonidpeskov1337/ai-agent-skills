# Discover the telemetry path

Start in the affected namespace, then a known monitoring namespace from approved
context. `discover_observability.py --context C --namespace monitoring --monitors`
lists projected Services and controller images, and optionally monitor CR names.
Names/images are hints; monitors specify scrape configuration, not proof of ingestion.
The helper intentionally omits raw monitor configuration because it may contain auth.
Inspect only required non-sensitive selectors, target namespaces, paths, ports and
scheme through narrow JSONPath queries when needed. Avoid fetching Secret references
or credentials. Do not scan every namespace by default.

| Component | Role | What to verify |
|---|---|---|
| Prometheus, Mimir query frontend/gateway, Thanos query, VM select/single | Historical metrics candidate | Approved route/prefix, retention, tenant, query support, freshness |
| Metrics Server | Current resource snapshot | metrics.k8s.io available; no historical trends or throttling |
| kube-state-metrics | Object state exporter | Scraped into a backend; requests/limits, states, replicas |
| node-exporter | Node OS exporter | Instance-to-node mapping, host device filters |
| cAdvisor/kubelet | Container resource exporter | Container/cgroup identity, duplicate scrape paths |
| Cilium/Calico or other CNI | Network/controller telemetry | Version-specific metrics and flow visibility |
| OpenTelemetry Collector, Alloy, agent | Collector/forwarder | Receiver -> processor -> exporter health; not assumed durable query storage |
| Loki | Logs API | Approved labels, timestamp range and line budget |
| Tempo/Jaeger | Trace API | Trace sampling, retention, service identity and clock alignment |
| Cloud monitoring | Provider-specific historical API | Account/project/region, time alignment, export delay, query permissions |

Use existing authorized endpoints or tool adapters. Kubernetes Service DNS may be
unreachable from the host. Do not turn an annotation-supplied URL into an HTTP request
with credentials. Do not auto-create port forwarding or expose internal services.
If endpoint configuration is unavailable, report a candidate, not a discovered
working historical API.

Mimir commonly serves reads under `/prometheus/api/v1/`; configure `--base-url
https://approved-gateway/prometheus`, not the distributor write endpoint. Prefixes
are configurable. VM cluster routes may include `/select/TENANT/prometheus`.
An exporter `/metrics`, remote-write endpoint, Grafana UI or OTLP receiver is not a
substitute for the query API. Cross-tenant federation requires explicit scope.

Use a cheap scoped instant query, then bounded `names` and `series` discovery:

```sh
python scripts/query_metrics.py --base-url https://approved-gateway/prometheus --mode names --selector '{__name__=~"container_cpu_.*",namespace="payments"}' --start 1793444400 --end 1793448000 --token-env METRICS_TOKEN --tenant-env MIMIR_TENANT
python scripts/query_metrics.py --base-url https://approved-gateway/prometheus --mode series --selector 'container_cpu_usage_seconds_total{namespace="payments",pod="api-abc"}' --start 1793444400 --end 1793448000
```

Auth flags refer to environment variable names, never token literals. Reuse approved
CA bundles or mTLS certificates via `--ca`, `--cert`, `--key`; TLS is always verified.
Other authentication (SigV4, OAuth refresh, basic auth) needs an existing approved
adapter/proxy; do not invent credential flows. Do not send tokens to unapproved hosts.
Redirects are refused. One bounded query at a time; no broad unfiltered series dumps.

Inspect labels and scrape topology using raw scoped samples before aggregation.
Check `timestamp(metric)` vs evaluation time, `up` for known scrape jobs, data gaps,
query warnings/infos, retention and delayed ingestion. `up` itself may be absent or
stale. An API success with an empty vector is not evidence of health.

## Collector allowlists and chart-native monitors

Collectors such as Alloy/OTel/agent often relabel with `keep` on `__name__`.
A metric visible in `/api/v1/label/__name__/values` can still return no recent
samples if it was ingested once, then dropped. Inspect raw sample timestamps,
`timestamp(metric)` and scrape coverage; `last_over_time` returns a value, not its
original sample age. Where supported, `ts_of_last_over_time` can expose that age.
Read the collector's relabel rules (non-sensitive fields only) before
concluding an exporter is broken.

Prefer chart-native ServiceMonitor/PodMonitor toggles over hand-written scrape
jobs. Before an approved change, inspect existing rendered evidence or separately
approved rendering and confirm the monitor object exists:
charts often require a parent toggle (for example a Service) and silently drop
misnested keys. After enabling, confirm the collector's monitor selector matches
the new object's labels and that series arrive.

Some application exporters expose probe groups on separate paths; a combined
`/metrics` path can run database probes on every scrape. Propose an approved change
to scrape only the needed
path (for example a queue-only path) when the backend is under pressure.

## Cloud provider telemetry for managed dependencies

Provider metrics can expose managed cache/database/load-balancer saturation
missing from Kubernetes telemetry; application/exporter metrics may also observe it. With an approved read-only profile, query per-node statistics at 1-5
minute periods across the incident and an equal baseline window. Typical signals:

| Dependency | Signals that decide incidents |
|---|---|
| Cache (Redis/Valkey/Memcached) | CPU and engine CPU, burst credit balance, memory %, swap, current connections, evictions, replication lag, failover events |
| Relational DB | CPU, freeable memory, swap, read/write latency, connections, IOPS/throughput vs provisioned, credit/burst balance |
| Connection pooler | Client vs server connections, waiting clients, max wait time |
| Shared file storage | Latency per op, throughput vs burst credits, IO limit % |
| Account quotas | Running on-demand vCPU vs quota, IP/ENI availability |
