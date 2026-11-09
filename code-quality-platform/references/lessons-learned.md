# Lessons learned


Each entry comes from a real incident in building and rolling out a code-quality platform. They are
written as **symptom → root cause → fix → rule**. Use them as review questions when designing or
changing anything similar.


## Correctness: false green


| # | Symptom | Root cause | Fix | Rule |
|---|---|---|---|---|
| 1 | Analyzer "succeeded" with 0 findings while it actually crashed | Success inferred from report presence; an empty report was written on failure | Scan manifest written only after exit 0; summary derives health from manifests | Success needs positive evidence, not absence of errors |
| 2 | Enabled analyzer silently missing from gate | Job `rules:exists` glob differed from the summary's source detection (`*.kt` vs `*.kts`) | One literal pattern per analyzer; structural test asserts rules glob == health glob | Two copies of a pattern will drift; test equality |
| 3 | Gate passed in report mode with a broken exception file | Config errors treated as policy violations | Config/health errors fail in every mode | Platform errors are not subject to policy mode |
| 4 | Profile files missing → analyzer used defaults → fewer findings | Download fallback | Completeness guard fails on any missing/empty file; verifier checks guard covers whole bundle | A fallback that reduces findings looks like improvement |
| 5 | Multi-module coverage looked fine but excluded modules | Non-recursive glob; bridge accepted zero matches | Recursive glob; bridge fails when nothing matches | Validate the input set, not just the parse |
| 6 | Missing baseline reported "0 new" | Absent baseline treated as empty | `baseline.status: missing`, baseline criteria `SKIPPED baseline_missing` | Missing ≠ zero |
| 7 | Gate passed although the new-code metric could not be computed | Missing git object turned into "no changes" | Explicit `unavailable:<reason>`; fails in block mode | Never guess when git history is incomplete |


## Correctness: false red


| # | Symptom | Root cause | Fix | Rule |
|---|---|---|---|---|
| 8 | Release-branch push (`develop` → `master`) failed with many "new" findings and 0.0% new coverage | Non-default protected branch was compared against the default branch; already reviewed code counted as new | Default **and protected** branches use their own previous summary and `HEAD^` | Model the team's branching model, not just `main` + features |
| 9 | Cosmetic edit above a finding made it "new" | Line numbers in fingerprint | Fingerprint on rule + path + normalized source context; ordinal salt for siblings | Identity must survive code motion |
| 10 | MR with only CI/version changes demanded 80% coverage | Non-production files counted as relevant change | Only production sources count; others → `not_applicable` | Gate on what the metric can measure |
| 11 | Import-only change failed coverage | Changed lines had no executable code | `no_covered_executable_lines` → skipped | Distinguish "nothing to measure" from "unmeasured" |
| 12 | MR widget labelled every finding as new | GitLab base pipeline skipped (`[skip ci]` release commit) so it had no base report | Publish only new findings when the native base is missing and our baseline exists | Know the native feature's comparison semantics |
| 13 | Empty MR diff failed closed with `no_merge_base` | Diff-base SHA unusable for an empty diff | Fallback to target branch SHA → `not_applicable` | Each edge case of the diff needs an explicit status |
| 14 | Changed files under consumer coverage excludes → `unavailable` | Build excludes (`**/config/**`) the files from the report | Documented; consumer aligns excludes or accepts skip | Consumer config can make data legitimately absent |
| 15 | Pipeline could not be created in consumer projects | Non-optional `needs:` on a consumer job name that differed (`check:unit_and_integration` vs `test:unit`) | `optional: true`; job fails inside with clear message | Pipeline-creation errors are the worst UX; fail in the job |


## Noise and adoption


| # | Observation | Fix | Rule |
|---|---|---|---|
| 16 | ~80% of findings in one language came from tests | Exclude tests only for production-convention rules; bug-finding rules stay on everywhere | Tune with per-rule evidence, by scope |
| 17 | CPD on generated/build code dominated duplication | Auditable exclusion list passed to CPD, count printed | Exclusions must be visible in the log |
| 18 | Size thresholds (method length) far below real code norms | Raised with sampled evidence, documented per rule | Defaults are migration candidates, not truth |
| 19 | Teams asked for project-level analyzer configs | Refused; local exceptions + profile variants instead | Central profile is non-negotiable or there is no standard |
| 20 | Developers read logs, not JSON | Summary prints `Findings against <ref>: N new, …` and lists new findings; gate prints offending findings | Every decision must be explainable from the job log |
| 21 | "Why wasn't this caught in the MR?" | Defect #8; MR pipelines were correct, the push pipeline was not | Test MR **and** push pipelines on every protected branch type |


## Supply chain and release


| # | Symptom | Root cause | Fix | Rule |
|---|---|---|---|---|
| 22 | Consumers pinned to a version whose profile bundle did not exist | Tag created before bundle publish | Publish before release; release job depends on publish | Everything a version references exists before the tag |
| 23 | Same version, different profile bytes | Mutable upload | Deterministic tarball; publish refuses differing bytes | Immutability is enforced, not promised |
| 24 | Fix released but developers still broken | Wrapper component pinned the old version | Release chain: platform → wrapper bump → consumer bump; track each | A fix is done when it reaches consumers |
| 25 | Release job failed after migrating version tool | Bot identity vs push rules / outdated version component | Migrate to supported release component; verify on a branch | Release automation is part of the product |
| 26 | Maintained third-party package abandoned | Library choice | Small stdlib client kept; dependency removed | Prefer stdlib over abandoned deps |
| 27 | Custom HTTP/redirect/token code for the GitLab API | Reinvention | Replaced with maintained pinned API client | Use the platform client for the platform API |


## Implementation


| # | Lesson | Rule |
|---|---|---|
| 28 | Logic embedded in YAML templates drifted from the reference Python module | Execute embedded scripts in tests by extracting them from the templates; reference module is the spec |
| 29 | Tests passed when the code was mutated | Add mutation-style tests: flip a condition in the template, expect failure |
| 30 | Simplification attempts removed validation | Simplify by deleting capability/duplication, never by weakening checks |
| 31 | Slim images lacked `git` → silent `git_missing` | Structural check that every git-using job uses a git-capable image |
| 32 | `$[[ inputs.* ]]` used outside a spec file | Only in component templates; verifier rejects elsewhere |
| 33 | Rules-derived inputs did not chain | Reference root inputs directly |
| 34 | Local runs missed tiers (no Docker) | Report un-run tiers explicitly; never claim green |
| 35 | Stray work on the default branch locally | Move to a feature branch before anything else |


## Process


- Sequential phases with explicit stop points; never trigger consumer pipelines before the platform
 repo's own pipeline is green.
- Baseline proof requires a real default-branch checkpoint — the user merges, the agent waits.
- Pilots use unmerged MRs in `report` mode; review findings per rule before proposing `block`.
- Staged rollout MRs per wave; record what was opened, pipeline status and failure class.
- In support, first classify: **real finding** / **missing consumer artifact** / **platform bug**.
 Reply in one sentence first, details after.
