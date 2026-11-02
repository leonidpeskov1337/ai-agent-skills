# Change attribution: who or what changed it

## Trigger and relevant resources
"Is anyone experimenting?", a value or certificate reverted, a resource resized
or failed over unexpectedly, or drift appeared in a plan. Start with the release
history of the affected chart, deployments/replicasets revisions, and events.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource replicasets --selector app=APP
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource events
```
Use existing read-only tooling for `helm --kube-context CONTEXT history RELEASE -n NS`, IaC pipeline
job lists for the window, cloud audit-trail lookups by resource name, and
provider event streams.

## Metrics and historical comparison
```promql
changes(kube_deployment_status_observed_generation{namespace="NS"}[1h])
kube_horizontalpodautoscaler_status_desired_replicas{namespace="NS"}
```
Build a single UTC timeline: release revisions, pipeline applies (with module
version and commit), audit-trail write events, provider events, symptom onset.

## Logs and events
Release revision timestamps and descriptions; pipeline apply logs showing the
module/version applied; audit-trail `Modify*`, `Update*`, `Put*` events with the
principal; provider events such as automatic failover.

## Hypothesis branches
- **Automatic provider action** (failover, maintenance, credit exhaustion):
 affirmative provider event present; no matching human write found within verified
 account/region/window/retention/filter coverage is supporting context, not proof.
- **IaC apply from an old branch/version** re-publishing stale data (for example an
 old certificate or config): pipeline apply at T using an older module version.
- **Manual patch**: field manager is `kubectl-*`, no matching release revision.
- **Controller decision**: HPA/provisioner events explain it with no human actor.
- **Secret/credential rotation** triggering reloads: secret version metadata
 (not values) changed at T; reloader annotations in plan diff.

## Confirmation criteria
An actor (human, pipeline or controller) with a timestamped write matches onset
and the changed field; competing actors ruled out in the same window.
An API principal identifies the credential/session, not necessarily the person
behind a CI job. Correlate pipeline provenance and delegation before attributing
an action to a person; otherwise retain actor uncertainty.

## Recommended remediation
Fix the source of truth (pin module versions, block applies from stale
branches, remove manual patches via IaC), not just the symptom.

## Risk and rollback
Reverting may fight an automatic controller; confirm ownership first.

## Post-fix validation
The next plan shows no unexpected diff; repeat events stop.
