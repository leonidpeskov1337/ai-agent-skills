# Source provenance

## Incident-pattern upgrade — 2026-11-02

Applied the user's supplied ready-to-use file replacements/additions, retaining
the incident-specific playbooks, mode budgets, claim ledger, detailed metrics and
expanded read-only projection. The supplied case outcomes are attributed to the
user; underlying production artifacts were not independently retrieved. Added
offline replay inputs are explicitly synthetic, including counterexamples.

Concrete corrections to the suggestions were checked against
[HPA behavior](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/),
[pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/),
[pod resource accounting](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/),
[probe configuration](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/),
[disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/),
[Karpenter NodeClaims](https://karpenter.sh/docs/concepts/nodeclaims/),
[ElastiCache host metrics](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/CacheMetrics.HostLevel.html),
[CloudTrail coverage](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html)
and the [blackbox HTTP probe implementation](https://github.com/prometheus/blackbox_exporter/blob/master/prober/http.go).

In particular, HPA does not replace evicted pods; unchanged desired replicas do
not identify an availability failure's cause; missing NodeClaims/audit results
are not proof of constraints/automatic action; cache-heavy memory and absent
container limits do not prove resource safety; partial filesystem accounting
cannot justify pod storage sizing; and blackbox processing is not solely backend
compute time. Probe projection excludes exec commands, headers and query values
to preserve the original sensitive-data boundary.

## Original build and Argo CD sources

Argo CD extension reviewed 2026-10-31 against official
[resource tracking](https://argo-cd.readthedocs.io/en/stable/user-guide/resource_tracking/),
[multiple sources](https://argo-cd.readthedocs.io/en/stable/user-guide/multiple_sources/),
[sync waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/),
[metrics](https://argo-cd.readthedocs.io/en/stable/operator-manual/metrics/),
[troubleshooting](https://argo-cd.readthedocs.io/en/stable/operator-manual/troubleshooting/)
and [app get flags](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_get/).
Tracking and metric behavior must be checked against the installed version.

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


## Rounds 3-4 investigation feedback

On 2026-11-11 the user supplied generalized probe-latency and controller-workqueue
investigation feedback against d36d359. Patterns 9-10 retain their reported numbers
and corrections as attributed incident observations, not maintainer-run benchmarks.
Offline tests validate metric-summary and transport behavior only.

Technical interpretation was cross-checked against:
- [Kubernetes scheduling and affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/):
  soft scoring versus required placement and missing topology labels.
- [Kubernetes logging architecture](https://kubernetes.io/docs/concepts/cluster-administration/logging/):
  previous-container access, rotation, pod eviction and cluster-level retention.
- [Controller-runtime metrics source](https://github.com/kubernetes-sigs/controller-runtime/blob/main/pkg/internal/controller/metrics/metrics.go)
  and [worker configuration](https://github.com/kubernetes-sigs/controller-runtime/blob/main/pkg/controller/controller.go):
  metric meanings, concurrency and deduplicated work items.
- [Upjet metric definitions](https://github.com/crossplane/upjet/blob/main/pkg/metrics/metrics.go):
  exporter-specific external-call observations; verify the deployed version.
- [Go runtime metrics](https://pkg.go.dev/runtime/metrics): runnable scheduling
  delay is one signal, not a comprehensive exclusion of local contention.
