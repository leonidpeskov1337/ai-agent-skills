# ImagePullBackOff

## Trigger and relevant resources
Image pull fails before application startup. Start with pods POD; events. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods --name POD
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource events
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
kube_pod_container_status_waiting_reason{namespace="NS",reason="ImagePullBackOff"}
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Image pull reason, registry status and node/runtime logs if authorized. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Missing tag/digest vs registry auth vs TLS vs network/rate limit vs architecture. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

Production-proven discriminators:
- Upstream registry 5xx/429 (public helper or base images): failures only on
 nodes without a cached copy; older nodes keep working. Compare cohorts by node
 age and check the registry status page/token endpoint.
- Mirror/pull-through cache auth expiry affects every workload using it at once.

## Confirmation criteria
Precise registry/runtime error matches resolved image and affected nodes; do not retrieve pull Secret. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Correct image digest or approved registry auth wiring; address registry availability. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Digest rollback can restore old vulnerable app; auth changes affect multiple workloads. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Image resolves and containers start on each affected node class. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
