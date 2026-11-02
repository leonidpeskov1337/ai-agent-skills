# Evidence-driven investigation

Keep a compact ledger in the working report; no need to persist sensitive raw data.

| Evidence ID | Source and exact read/query | Collected UTC | Incident UTC | Observation/units | Coverage/limitations |
|---|---|---|---|---|---|
| E1 | Explicit context, namespace, UID, endpoint/query or log stream | Timestamp | Range | Measured fact | Denied/missing/stale/truncated |

Track hypotheses separately:

| Hypothesis | Predicted evidence | Evidence for/against | Next discriminating test | Confidence/status |
|---|---|---|---|---|
| Resource constraint | Saturation precedes symptom in affected cohort | E IDs | Compare healthy cohort and downstream latency | Open/rejected/supported |

Track claims made to the user, so corrections are explicit:

| Claim ID | Claim as stated | Evidence | Status |
|---|---|---|---|
| C1 | "Cap only reached during incidents" | E4 (14-day mean) | Retracted by E9 (hours at cap per weekday) |

Triage -> targeted diagnostics -> historical metrics -> dependencies -> hypothesis
testing -> proposed remediation -> verification are revisitable stages, not a
command sequence. On each iteration ask which observation would change the ranking.
Use owner references and UIDs to avoid confusing replaced pods with the same name.

Compare rollout revisions, nodes/zones, containers, traffic mix and downstream spans.
Correlation and temporal order support a cause but do not prove it. Independent
evidence may include an explicit runtime termination reason, scheduler explanation,
effective policy, trace bottleneck, provider event, audit-trail record or
already-observed controlled recovery. Do not perform an intervention merely to
strengthen a diagnosis without approval.

Distinguish symptom (latency), mechanism (throttling), cause (an introduced CPU-bound
code path), and contributor (low limit). A stable limit may become constraining
because traffic or application behavior changed. Compare requests/limits at the
container level before aggregating; a pod can hide one constrained container.

## Discriminating questions that repeatedly decide incidents

| Question | Read | If yes |
|---|---|---|
| Did desired replicas change, or only Ready? | HPA desired vs deployment available over time | If only Ready fell: distinguish probes, crashes, evictions, rollout, Pending replacements and node loss |
| Is the pod working or waiting? | Pod CPU vs latency vs thread/worker busy | Waiting: go to dependency |
| Did a resource run out that is not CPU/memory? | Burst credits, connection count, quota, IP/ENI, disk | Managed-dependency or quota branch |
| Did the controller try and fail, or not try? | Retained NodeClaim/provisioner/scale events plus controller health | Distinguish failed launch from limits/constraints/controller faults; current claim absence is inconclusive |
| Is the request shape causing the waste? | Requests vs p95/p99 usage per dimension incl. ephemeral storage | Right-size before adding capacity |
| Who changed it? | Release history, pipeline runs, cloud audit trail | Attribute before blaming |
| Is the metric what its name suggests? | Units, help text, label values, cross-check | Re-derive before alerting/reporting |
| Is the signal a direct symptom? | Evictions, OOM, MemoryPressure, throttle series | Derived ratios alone are not risk |

## Cross-checks before stating risk

- Cross-check derived headroom against RSS/cache, reclaimability, cgroup events,
 MemoryPressure, evictions, OOM kills and restarts. Cache can explain high working
 set; neither cache presence nor absence of recorded failures proves no risk.
 Separate measured exhaustion from prospective risk, including missed scrape peaks.
- A fleet mean can hide one saturated node or pod; also report the busiest unit.
- A 14-day mean can hide a daily pattern; also report working-hours behavior and
 time-at-limit per day.
- When the user reports an observation that contradicts your summary, re-query at
 the resolution the user observed before replying.

Use a budget and diminishing-return stop rule. Mark failures to read logs or metrics
as limitations and choose another available source. Stop on identity uncertainty.
An unchanged denied request should not be repeated with alternate credentials.
If healthy now, distinguish no current reproduction from proof no incident occurred.
For missing history, request retained event/log/metric artifacts and state exactly
which hypotheses remain indistinguishable.
