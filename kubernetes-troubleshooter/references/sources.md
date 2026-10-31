# Source provenance

Reviewed 2026-10-31. Instructions and playbooks are original. Consult docs matching
the actual server, exporter and controller versions before relying on optional APIs.

- [Anthropic Skill Creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator):
  inspected current SKILL.md and validator; uses SKILL.md frontmatter, progressive
  disclosure, scripts/references and evals/evals.json. Evaluation expectations include
  realistic prompts, independent runs and explicit grading. Host Skill Creator also
  supplies local validation. No runtime dependency on Claude is introduced.
- [PerfectScale troubleshooting guide](https://info.perfectscale.io/kubernetes-troubleshooting-guide):
  public landing page reviewed; covers pod scheduling, crashes, OOM, throttling, DNS,
  storage and CNI. Full ebook is gated and was not retrieved; no claim to have read
  its internal workflows. These broad failure domains inform the playbook coverage.
- [Kubernetes cluster debugging (SIG Node/platform)](https://kubernetes.io/docs/tasks/debug/debug-cluster/)
  and [Service debugging (SIG Network)](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/):
  cluster and service investigation paths.
- [Prometheus HTTP API](https://prometheus.io/docs/prometheus/latest/querying/api/):
  query/query_range/series/label endpoints and warnings/error semantics.
- [PromQL functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
  and [histograms](https://prometheus.io/docs/practices/histograms/): rates and quantiles.
- [Mimir HTTP API](https://grafana.com/docs/mimir/latest/references/http-api/):
  configurable Prometheus read prefix and query frontend versus exporter/write APIs.
- [OpenTelemetry Collector troubleshooting](https://opentelemetry.io/docs/collector/troubleshooting/):
  inspect pipeline stages and internal telemetry; collector presence is not storage.
- [EKS](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html),
  [AKS](https://learn.microsoft.com/en-us/troubleshoot/azure/azure-kubernetes/welcome-azure-kubernetes),
  [GKE](https://docs.cloud.google.com/kubernetes-engine/docs/troubleshooting):
  managed-node, networking, access and provider-level constraints.

Known limits: classification uses name/image hints and misses arbitrary custom names;
helpers never infer an approved endpoint from a name. Generic Prometheus-compatible
reads are supported; Loki, traces and cloud APIs require host tools/adapters. No live
cluster is bundled. Offline tests cannot prove production behavior or arbitrary-incident
reasoning quality. Logs and metric labels need human/agent sanitization beyond the
best-effort redactor. Query budgets bound transport output and evaluation points,
not backend cost; narrow selectors and backend limits remain necessary.
Subprocess output is bounded in memory. Timeouts attempt attached process-tree
termination; detached kubeconfig credential plugins still need host supervision.
HTTP reads enforce elapsed checks between chunks plus a socket timeout (a blocked
read can overrun the 20-second elapsed target by up to one socket-timeout interval;
OS DNS resolution may have its own deadline).

Future improvements: controlled disposable-cluster integration tests, versioned
exporter schemas, approved SigV4/OAuth adapters, trace/log correlation adapters and
repeated blinded behavioral evaluations with real incident artifacts.
