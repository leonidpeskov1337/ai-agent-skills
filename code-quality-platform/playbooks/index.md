# Playbooks


Pick by **symptom**; follow steps in order, cheapest decisive check first. Contracts are in
[contracts](../references/contracts.md).


| Symptom | Playbook |
|---|---|
| Gate fails after merge/push to a protected branch but passed in the MR | [gate-fails-after-merge](gate-fails-after-merge.md) |
| `metric is unavailable` | [metric-unavailable](metric-unavailable.md) |
| Gate shows `SKIPPED … not_applicable` and the user expected a check | [gate-skipped](gate-skipped.md) |
| An analyzer did not run / `no_health_evidence` / `report_missing` / job absent | [analyzer-missing](analyzer-missing.md) |
| Pipeline will not start, job stuck, component not resolved, version job fails | [pipeline-wont-run](pipeline-wont-run.md) |
| Fix is merged but consumers still fail | [fix-not-propagating](fix-not-propagating.md) |
| Too many findings / "are these real?" | [findings-noisy](findings-noisy.md) |


## Universal first steps


1. Get the **job** URL, not only the pipeline. Note source (MR vs push), ref, and the component
  version actually included.
2. Download the gate job log and run
  `python3 scripts/triage_gate_log.py <log>` (or `--stdin`). It classifies known signatures.
3. Fetch `quality-summary.json` from the quality-summary job artifacts for baseline ref, diff status,
  per-metric statuses and analyzer health.
4. Compare the component version with the latest release before suspecting a new bug.
