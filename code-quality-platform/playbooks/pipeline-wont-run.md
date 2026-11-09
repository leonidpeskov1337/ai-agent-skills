# Pipeline will not start / job stuck / component not resolved / version job fails


| Symptom | Likely cause | Check / fix |
|---|---|---|
| "This job is stuck because the project doesn't have any runners online assigned to it" | No untagged runners; job lacks tags | Set `runner_tags` input / `job_tags`; verify runner tags via API |
| `Unknown interpolation key` / `$[[ inputs.x ]]` syntax error | Input syntax used outside a component file | Replace with literal or CI variable |
| Component version not found | Wrong tag or unreleased version | List project tags/releases; pin an existing one |
| `component … project/ref not accessible` | Visibility/permissions of the component project | Check the caller's access to the catalog project |
| Version bump job: `committer email … not allowed` / push rejected | Bot identity violates push rules (legacy component) | Migrate to the maintained versioning component; set bot username variable |
| Release job runs without a bump | Missing guard | Run release only when the bump output says bumped |
| Pipeline created but all jobs skipped | `workflow:rules` or `exists:` filtering | `glci show` / CI Lint with the real context |
| Includes fail only in a child pipeline | Rules missing child source | Add `parent_pipeline`/`pipeline` contexts |


Verify any fix with component lint and, for CI config in a project, the CI Lint API or `glci`
before pushing.
