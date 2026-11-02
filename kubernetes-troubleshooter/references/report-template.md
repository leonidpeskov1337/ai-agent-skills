# Incident report template

## Incident summary
Symptom, context/cluster, namespace/workload, incident UTC interval and user timezone.
State whether investigation is live, offline fixture, historical or unexecuted plan.

## Impact and severity
Affected requests/users/services/nodes, comparison cohort, severity basis or unknown.

## Findings
Facts with E IDs, exact source/command/query, timestamps, object UIDs and scope.
Separate logs/events/config observations from interpretations; redact sensitive data.
When Argo/source evidence is relevant, record the management/relevance decision,
control-plane versus destination identity, ordered desired/applied source revisions
and local checkout differences. State when Argo was checked and found unrelated.

## Metrics analysis
Backend and approved query route; available/missing names/labels; exact PromQL,
window/step/units, freshness, duplicate policy, baseline/during/after values, peaks,
means and relevant quantiles. Show gaps/warnings and affected vs healthy cohorts.
For a positive baseline B and incident I, deviation = (I-B)/B; if B=0, report absolute
change rather than inventing a percentage. Label time-sample and request percentiles.

## Root-cause assessment
Ranked hypotheses with supporting/disconfirming E IDs, independent confirmation,
contributing factors, alternatives, confidence and next test. Say unresolved when
causality cannot be established. Never promote simulated evidence to live fact.

## Recommended remediation and risk
Prioritized action, exact scoped command/YAML when known, approval status, blast
radius, capacity/cost/data risk, recorded pre-change state and rollback command or
explicit reason rollback needs more information. Recommendations are not executed.

## Verification
Read-only checks, expected signals, observation window spanning normal traffic and
multiple scrape/scaling cycles, recurrence criteria and rollback trigger.

## Prevention
Relevant alerting, rollout checks, capacity or application improvements.

## Investigation limitations
Access denials, retention gaps, missing telemetry, incomplete scope, stale samples,
query truncation, untested hypotheses, budget consumed and required follow-up.

## Condensed format (short-answer, standup or chat)

Use when the user asks for a message, not a report. 5-8 numbered points, each one
fact with its number, window and source; then a one-line decision and the
re-check condition. Keep corrections visible ("Correction: ..."). Example shape:

1. Desired replicas stayed at 8 from 13:54 to 14:09 UTC; available dropped to 1 (E3, E4).
2. Pods were NotReady with CPU about 5%; thread/trace evidence located cache waits (E6).
3. Cache node had 0 burst credits; provider failed over at 14:06 (E7, E8).
Decision: resize the cache first; re-check scaling in 1-2 weeks.
