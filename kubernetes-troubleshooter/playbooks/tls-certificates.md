# TLS and certificate issues

## Trigger and relevant resources
Expired certificate, handshake error or hostname mismatch. Start with ingresses; gateways.gateway.networking.k8s.io; pods. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource ingresses
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource gateways.gateway.networking.k8s.io
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
probe_ssl_earliest_cert_expiry - time()
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
Ingress/mesh handshake errors and existing certificate public metadata. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
Expiry vs SAN/SNI mismatch vs trust chain vs mTLS client identity vs clock skew. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Public certificate issuer/SAN/validity or trust error matches client handshake path. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Renew through existing certificate manager or correct trust/SNI wiring; never fetch private keys. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
Trust changes can cut off clients; preserve trust bundle and rotation rollback window. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
Original client completes validated handshake; expiry/trust alerts clear. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
