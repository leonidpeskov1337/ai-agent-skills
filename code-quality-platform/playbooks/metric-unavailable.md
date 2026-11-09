# `metric is unavailable`


The gate could not measure a required metric and failed closed (block mode).


1. Read the metric status in `quality-summary.json` and the diff status.
2. Branch on the reason:


| Reason | Check | Owner / fix |
|---|---|---|
| `unavailable:no_merge_base` | MR net diff empty? commits cancel out? | Give the MR a real diff; platform fallback to target SHA → `not_applicable` |
| `unavailable:base_unreachable` | Shallow clone / missing target branch fetch | Fix fetch depth in the job; platform issue if default |
| `unavailable:git_missing` | Image lacks `git` | Platform image/input issue |
| Coverage data missing for changed files | Package excluded from coverage tool? | Consumer: remove exclude or disable coverage ([coverage](../references/coverage.md)) |
| No coverage report at all | Coverage producer job ran and uploaded? job name input correct? | Consumer wiring or `coverage_job_name` |
| Baseline unavailable | Baseline job/artifact on the target branch exists? expired? | Wait for first branch pipeline or fix artifact retention |
| Duplication metric unavailable | CPD job ran? same diff-base issue as coverage | See above |


3. Workaround while fixing: switch the project to `report` mode (says what signal is lost).
4. Do not "fix" by treating `unavailable` as pass inside the platform — that creates false greens.
