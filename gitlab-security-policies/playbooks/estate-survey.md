# Estate survey of failed policy jobs


1. Before a migration, survey the current state first to get a baseline failure rate;
  otherwise pre-existing failures are blamed on the change.
2. Fix the window (since the last survey or rollout) and the job-name filter.
3. Run `scripts/survey_failed_jobs.py` with a read-only token, `--fetch-logs` and bounded
  `--max-projects` / `--max-logs`.
4. Summarise with `--summarise`, which gives counts per class, owner and example URLs.
5. Count only the **latest** failure per project and job. Older failures may already be fixed.
  Re-check the classes that have a fix in flight.
6. For the unclassified jobs, sample 10–20 logs, add signatures to both the script and
  [troubleshooting](../references/troubleshooting.md), and re-run the classification offline
  (`--reclassify survey.json`, which needs a survey saved with `--keep-logs`).
7. Route each class:
  - platform → a change through the delivery mechanism;
  - project → the developer documentation, plus notifying the top projects;
  - infra and admin → a ticket with job IDs;
  - product → an upstream issue plus a workaround.
8. Report with the survey table in [report-template](../references/report-template.md), and set
  the re-survey date.
