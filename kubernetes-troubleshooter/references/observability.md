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
