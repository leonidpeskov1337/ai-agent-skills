# Evidence-driven investigation

Keep a compact ledger in the working report; no need to persist sensitive raw data.

| Evidence ID | Source and exact read/query | Collected UTC | Incident UTC | Observation/units | Coverage/limitations |
|---|---|---|---|---|---|
| E1 | Explicit context, namespace, UID, endpoint/query or log stream | Timestamp | Range | Measured fact | Denied/missing/stale/truncated |

Track hypotheses separately:

| Hypothesis | Predicted evidence | Evidence for/against | Next discriminating test | Confidence/status |
|---|---|---|---|---|
| Resource constraint | Saturation precedes symptom in affected cohort | E IDs | Compare healthy cohort and downstream latency | Open/rejected/supported |

Triage -> targeted diagnostics -> historical metrics -> dependencies -> hypothesis
testing -> proposed remediation -> verification are revisitable stages, not a
command sequence. On each iteration ask which observation would change the ranking.
Use owner references and UIDs to avoid confusing replaced pods with the same name.

Compare rollout revisions, nodes/zones, containers, traffic mix and downstream spans.
Correlation and temporal order support a cause but do not prove it. Independent
evidence may include an explicit runtime termination reason, scheduler explanation,
effective policy, trace bottleneck, or already-observed controlled recovery.
Do not perform an intervention merely to strengthen a diagnosis without approval.

Distinguish symptom (latency), mechanism (throttling), cause (an introduced CPU-bound
code path), and contributor (low limit). A stable limit may become constraining
because traffic or application behavior changed. Compare requests/limits at the
container level before aggregating; a pod can hide one constrained container.

Use a budget and diminishing-return stop rule. Mark failures to read logs or metrics
as limitations and choose another available source. Stop on identity uncertainty.
An unchanged denied request should not be repeated with alternate credentials.
If healthy now, distinguish no current reproduction from proof no incident occurred.
For missing history, request retained event/log/metric artifacts and state exactly
which hypotheses remain indistinguishable.
