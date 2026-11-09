# CI gotchas


Pitfalls met while building and operating component-based platforms on GitLab.


| Gotcha | Consequence | Rule |
|---|---|---|
| `project.default_branch` ≠ protected release branch | Baseline/diff against the wrong branch after merge | Resolve baseline from the *current* branch's own history on protected-branch pushes |
| Empty net MR diff | `CI_MERGE_REQUEST_DIFF_BASE_SHA` empty → `no_merge_base` | Fall back to target-branch SHA → `not_applicable` |
| `exists:` needs literal globs | Cannot parameterise by input | One rule per language per context |
| Child pipelines have source `parent_pipeline`/`pipeline` | Analyzer never runs via intermediate component if rules omit it | Always include those contexts |
| MR + branch duplicate pipelines | Doubled cost/noise | `when: never` for branch pipelines when `CI_OPEN_MERGE_REQUESTS` |
| `$[[ inputs.* ]]` outside `spec:inputs` files | Pipeline syntax error | Literal or CI variable in project `.gitlab-ci.yml` |
| No untagged runners | Job pending forever ("stuck, no runner") | Tag every job; expose `runner_tags` input |
| Push rules reject bot committer email | Version bump job fails on protected branch | Bot username variable + allowed identity |
| Artifacts expire / not downloaded | Baseline or coverage missing | `when: always`, sane `expire_in`, `needs: artifacts: true` |
| `rules:` evaluated at pipeline creation | `exists:` only sees the repo at the pipeline commit | Don't expect generated files to satisfy it |
| `allow_failure` on analyzers | Hides crashes | Rely on manifest-only-on-success: no manifest → `no_health_evidence` |
| Unpinned/`latest` downloads | Non-reproducible, supply-chain risk | Pin + checksum |
| Token forwarded on redirects | Credential leak to artifact CDN | Use a maintained client or strip auth on cross-host redirects |
| Project variable API returns 403 | Cannot verify a CI variable | Say unknown; ask owner |
| Pipeline execution policy variable override locked | Project CI vars don't reach policy jobs unless excepted | Check policy exceptions before blaming the component |
| Merge-result / detached pipelines | Different SHAs than branch pipelines | Use the documented `CI_MERGE_REQUEST_*` variables, not guessed refs |
| Optional analyzer fails on odd builds (bytecode-based) | Noise for a subset of projects | Provide a feature flag to disable; support points to it |
| Non-optional `needs:` on a job that does not exist | Pipeline **creation** fails for the consumer | `optional: true`; fail inside the job with a clear message |
| Inputs derived through `rules:`-conditional inputs | Values do not chain | Reference root inputs directly |
| `!reference` tags | Plain YAML loaders fail in tests | Register a custom constructor in the test loader |
| Artifacts by ref + job name | Ambiguous if job names repeat across includes | Unique, prefixed job names |
| MR title validation | Non-Conventional-Commit title rejected | Use `type(scope): subject` |
| `[skip ci]` release commit on target branch | Native MR widget has no base report → all findings "new" | Publish only new findings when our baseline exists |
| Slim Python images | No `git` → diff silently impossible | Dedicated git-capable image input; verify statically |
| Coverage regex vs printed value | Widget disagrees with summary | Print one anchored line with fixed decimals from the summary |
| Non-recursive `**` in a consumer glob | Modules silently dropped | Recursive glob; bridge fails on zero matches |
| Docker unavailable locally | Simulate/run tiers do not execute | Report them as not run, never as passed |
