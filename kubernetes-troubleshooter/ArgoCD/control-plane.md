# Argo CD component and shared delivery failures

## Trigger and targeted reads

Use when multiple relevant Applications stop reconciling, there is a confirmed
repository/controller/API error, or Argo CD itself is the failing service. An unrelated
unmanaged application's runtime outage does not justify this branch.

Discover actual controller names/images in the known install namespace; deployments
vary. With the explicit control-plane context, use `collect_evidence.py` for named
Deployments/StatefulSets/pods, then scoped events and opt-in bounded container logs.
Inspect only components implicated by Application conditions/operation timestamps:

| Component | Hypotheses and discriminating observations |
|---|---|
| application-controller | Queue/reconcile delay, destination connectivity/auth, sharding, resource pressure; compare affected apps/destinations and reconcile timestamps |
| repo-server | Git/Helm access, missing revision/dependency, render/plugin failure, cache/timeout/resource pressure; tie logs to exact repo/revision/app |
| applicationset-controller | Generator/SCM API errors, template/render problems, invalid owner-generated apps; correlate named ApplicationSet condition and controller logs |
| argocd-server/Dex/SSO | User-facing API/TLS/auth/RBAC vs actual reconciliation; failed login does not establish controller outage |
| Redis/cache | Dependency availability/latency vs source or destination errors; correlate client errors and component readiness, do not flush cache automatically |

Investigate DNS/network/TLS/CPU/memory using normal playbooks only when component
evidence supports them. A healthy Argo API does not prove controller/repo-server
health; unavailable UI does not prove previously deployed workloads are broken.
Remote cluster access, project restrictions and destination ServiceAccount RBAC
need separate evidence; successful operator `kubectl` access does not prove the
controller has the same rights. Do not read Argo's cluster/repository credential Secrets.

## Historical metrics and confirmation

Check discovered controller/version metric names and label populations first:

```promql
histogram_quantile(0.95, sum by (le) (rate(argocd_app_reconcile_bucket[5m])))
sum(rate(argocd_git_request_total[5m]))
```

Add the verified installation/job/cluster and application/repository matchers where
available. A request counter alone is not an error counter; inspect labels before
selecting failures. Compare queue/reconcile latency, repo calls, CPU/throttling,
memory/restarts and app sync outcomes before/during/after. Exporter availability is
not historical API availability. Confirm a common failing component through aligned
logs/status/metrics across relevant apps; distinguish regional destination outage
from a control-plane-wide failure.

## Remediation, rollback and validation

Propose the proven repo/trust/identity/render/config/capacity correction with owning
source and exact scope. Controller/server/cache restarts, scaling, source commits,
repo credential rotation and changing ApplicationSet selectors require explicit
approval. Risks include global reconciliation load, fan-out deployments/deletion,
cache cold starts and user lockout. Preserve prior component revisions/policies and
compatible recovery paths; do not disable TLS or auth checks to test a theory.

Validate both delivery (fresh reconciliation, successful renders/syncs for affected
apps) and runtime recovery where there was runtime impact. If only delivery was
affected, state that existing apps may have continued serving. Record permissions,
missing logs/history, scope and what remains unconfirmed.
