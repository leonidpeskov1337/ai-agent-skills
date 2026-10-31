# Decide whether Argo CD is relevant

Use this branch when deployment/reconciliation evidence, a supplied Application, or
an Argo component failure warrants it. Installation and workload management are
different facts. `argocd.enabled` in [the prompt](../prompt.md) is a hint, not proof
of ownership or cause.

| Evidence | Next step |
|---|---|
| Enabled, affected workload has verified matching Application inventory/tracking | Inspect that Application's destination, desired/applied revisions and timing; deepen only along a plausible incident link |
| Enabled, workload is Helm/manual/another operator managed and no implicated Argo-managed dependency | Continue Kubernetes/metrics investigation; do not investigate unrelated Argo health |
| Disabled/unknown, but workload tracking or an implicated dependency points to Argo | Reconcile the contradiction; investigate the authorized remote/local control plane if accessible |
| No tracking annotation or denied Application access | Ownership unresolved; custom label tracking, missing visibility or remote management may explain it |
| Application Synced/Healthy but requests fail | Continue application/dependency diagnostics; these states do not prove SLO health |
| Application OutOfSync without incident-time change | Treat drift as a separate observation until its resource diff/timing explains the symptom |

## Bound the ownership check

1. Follow the affected Pod's owner chain to the controller. The generic evidence
   helper now retains only the known tracking/installation/hook annotations and the
   conventional instance label. All are untrusted data. A label alone can also be
   set by Helm or custom tooling. Custom tracking keys require a narrow metadata
   read after verifying the installation's tracking configuration.
2. Match tracking identity to the actual group/kind/namespace/name. A copied annotation
   pointing at a different object does not prove management. Account for installation
   ID, multiple Argo instances, Applications in non-installation namespaces and a
   control plane on a different cluster. Do not scan all clusters/namespaces.
3. Inspect the candidate Application's destination and resource inventory. Map a
   named destination/server to the verified affected cluster using approved existing
   configuration; do not read Argo cluster credential Secrets. Inventory may be
   stale: retain `reconciledAt`, operation times and source revisions.
4. Record management as confirmed, unsupported, or unresolved, with evidence IDs.
   If no deployment link exists, only pursue Argo if it manages an implicated
   shared dependency such as DNS, ingress, CNI or a backend. Otherwise stop this branch.

## Read-only collection

Use the same bounded collector, with explicit **control-plane** context and
Application namespace (substitute verified identifiers):

```sh
python scripts/collect_evidence.py --context ARGO_CONTEXT --namespace APP_NAMESPACE --resource applications.argoproj.io --name APP_NAME
python scripts/collect_evidence.py --context ARGO_CONTEXT --namespace APPSET_NAMESPACE --resource applicationsets.argoproj.io --name APPSET_NAME
```

The collector projects status/revision/inventory and safe source pointers; it omits
inline Helm values, parameters, plugin environments, generated manifests, ApplicationSet
generator data and Secret contents. It does not classify causality or resolve ownership
automatically. Use narrow allowed-field reads for remaining evidence, and bounded logs
from the implicated controller/repo-server/container only. Kubernetes and Argo API
RBAC are separate; denied reads are limitations, not a reason to escalate privileges.

If an existing authorized Argo CLI/API is used instead, get only needed fields and
keep the context/server explicit. Do not use `app manifests`, `--show-params`, broad
JSON dumps or diffs without Secret-aware filtering: generated resources/config may
contain sensitive values. `app get --refresh` and `--hard-refresh` request reconciliation
work; they are not passive reads and require explicit approval. Likewise no automatic
sync, prune, terminate-operation, action, rollback, app/project edit or controller restart.

Choose [application/sync investigation](application-sync.md),
[Argo component investigation](control-plane.md) or
[repository/revision investigation](repositories.md) only as evidence requires.
