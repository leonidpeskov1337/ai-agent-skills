# Deployment regressions

## Trigger and relevant resources
Intermittent failures after rollout or only one revision fails. Start with deployments DEPLOY; replicasets; pods. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource deployments --name DEPLOY
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource replicasets
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
sum by(pod)(rate(http_requests_total{status=~"5.."}[5m]))
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Revision timestamps, pod owner UIDs, readiness/restarts and per-revision logs. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
New image/config vs mixed revisions vs topology/traffic bias vs unrelated dependency. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Same traffic/node cohort differs by revision and onset follows rollout; rule out confounding placement. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Propose known-good revision rollback or narrowly scoped fix. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Schema migration may prevent rollback; preserve image digest/config and assess data compatibility. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
All serving endpoints on validated revision; errors disappear across rollout and normal traffic. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
