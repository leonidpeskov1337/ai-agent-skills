00# Playbooks


Pick the playbook by **symptom**, then follow its steps in order. Each step names the cheapest
decisive check first. Signature details are in
[troubleshooting](../references/troubleshooting.md), and the commands are in
[runbooks](../references/runbooks.md).


| Symptom | Playbook |
|---|---|
| No policy jobs, "scans are missing", or a policy change has no effect | [scans-not-running](scans-not-running.md) |
| A policy job is stuck `pending` | [job-pending](job-pending.md) |
| A policy job failed (any scanner) | [scan-job-failed](scan-job-failed.md) |
| A dependency scanning resolution or scan job failed | [dependency-resolution](dependency-resolution.md) |
| An expected finding does not appear | [findings-missing](findings-missing.md) |
| Too many findings, or "are these real?" | [findings-noisy](findings-noisy.md) |
| Gate blocks unexpectedly, does not block, or the wrong people can approve | [gate-behaviour](gate-behaviour.md) |
| An exception is not applied or not removed | [exception-not-applied](exception-not-applied.md) |
| How many policy jobs fail across the estate | [estate-survey](estate-survey.md) |
