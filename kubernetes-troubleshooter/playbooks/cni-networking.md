# CNI and pod networking

## Trigger and relevant resources
Cross-pod/node packet loss, sandbox creation failures. Start with pods POD; daemonsets; nodes NODE. Substitute verified names/context; run only the
read that discriminates the current hypotheses. NS is ignored by Kubernetes for
cluster-scoped resources. Use narrow field queries for related resources not exposed
by the helper; no raw Secret or configuration dumps.

## Initial read-only diagnostics
```sh
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource pods --name POD
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource daemonsets
python scripts/collect_evidence.py --context CONTEXT --namespace NS --resource nodes --name NODE
```
For events, scope by involved object name/UID via `--field-selector` when known.

## Metrics and historical comparison
Starting expression (use only after discovery and adapt names/labels):
```promql
rate(node_netstat_Tcp_RetransSegs[5m])
```
Read [metrics guidance](../references/metrics.md). Add verified cluster/workload,
job/device matchers, eliminate duplicate scrapes and check freshness. Compare
before/during/after; absent series means a visibility gap. Use snapshots and events
if historical metrics are unavailable. Do not infer causality from this metric alone.

## Logs and events
CNI pod logs, sandbox events, authorized flow verdicts and provider IP evidence. Use bounded timestamped logs from the affected container (previous instance
for restarts), retain UTC and owner/revision, and redact before saving. Controller,
node or provider logs require their own existing authorization.

## Hypothesis branches
IP exhaustion vs overlay/routing/MTU vs policy vs node conntrack vs cloud firewall. Choose the cheapest discriminating next observation. Inspect both
supporting and contradictory signals and compare an unaffected cohort.

## Confirmation criteria
Local/cross-node comparison and flow/runtime evidence locate failing hop; node-wide retransmits alone insufficient. Link conclusions to evidence IDs; if the required evidence is missing,
report a ranked hypothesis and the next test, rather than a confirmed root cause.

## Recommended remediation
Repair confirmed routing/IP/capacity/config issue. Propose exact reviewed commands/YAML only once targets and prior state
are known. Require explicit approval before execution; these diagnostics do not
provide change authorization.

## Risk and rollback
CNI rollout can disconnect nodes; preserve plugin config and staged rollback. Record the pre-change revision/config and concrete reversal before a change;
if reversal is unsafe or impossible, state that and require a recovery plan.

## Post-fix validation
New pod sandbox succeeds; affected cross-node/zone flows recover without drop increase. Observe for multiple scrape/controller cycles and comparable load;
watch recurrence and unintended effects. Recovery remains unverified until observed.
