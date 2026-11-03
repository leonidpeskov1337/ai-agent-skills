# Policy job stuck pending


1. Get the job's `tag_list` (`GET /projects/:id/jobs/:job_id`).
2. Compare it with the online runners available to the project. Do any accept those tags, or
  untagged jobs?
3. Untagged policy job, and no runner runs untagged jobs → add `tags` to every scan action
  (platform). Use one tag that is valid everywhere the policy applies.
4. An untagged DAST job from a SEP `dast` action → there is no validated site profile. Move DAST
  to a pipeline execution schedule policy.
5. Tags are correct but runners are saturated → this is capacity (infra). Check queue duration
  across projects.
6. Cancel and re-run after the fix. Pending jobs do not pick up policy changes.
