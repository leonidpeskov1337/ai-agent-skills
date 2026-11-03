# Scans not running


1. **Confirm the policy job is absent.** List the jobs of the latest MR pipeline and of the
  latest default-branch pipeline. If the jobs exist but failed, go to
  [scan-job-failed](scan-job-failed.md).
2. **Did a pipeline exist at all?** If a push created no pipeline, check:
  - the project's `workflow:rules`;
  - `[skip ci]` in the commit message, against the policy's `skip_ci` setting.


  SEP cannot override either. Owner: the project, or the platform if enforcement must move to a
  PEP.
3. **What did GitLab load?** Query the project's loaded policies with
  `relationship: INHERITED`:
  - Nothing loaded, or the names are stale → step 4.
  - The names are present → step 5.
4. **Document rejected or not propagated:**
  - read the committed `policy.yml` and run it through `scripts/lint_policy.py` and the schema at
    the version tag;
  - check its commit time: less than ~10 min ago means propagation may still be running, so
    resync the group;
  - count policies per type against the limits.
5. **Scope:**
  - read the policy's `policyScope`;
  - is the project excluded, or outside `groups.including`?
  - Is an exception active for it?
6. **Linking.** Was the project created after the policy? Linking runs in Sidekiq; check its
  health if many new projects are affected. Then run
  `resyncSecurityPolicies(project, INHERITED)` (**WRITE**), and check CI lint for the jobs.
7. **Rules.** Do the `branch_type` and `pipeline_sources` match this pipeline? For example,
  default-branch-only rules do not fire on feature branches, and MR rules need
  `merge_request_event`.
8. Verify the fix with a new pipeline from a real push, not the pipelines API (API-created
  pipelines get no policy jobs).
