# Gate fails after merge but passed in the MR


**Typical signature:** `minimum_new_code_coverage: 0.0 is below 80.0` or an implausible
`max_new_major: 14` on a push pipeline to a protected branch, with a green MR gate earlier.


1. Is the failing job a push (non-MR) pipeline on the protected branch? (`CI_PIPELINE_SOURCE=push`)
2. Is the project's **default branch different** from that protected branch? (API: project
  `default_branch`.) If yes and the component version predates the protected-branch baseline fix,
  the baseline/diff were taken against the default branch: the whole delta between the two
  branches counted as new.
3. Confirm in `quality-summary.json`: baseline ref and diff base. If they point at the default
  branch while the pipeline ran on `master`/`main`, this is the bug.
4. **Fix:** upgrade to the release containing the fix (protected/default branches use their own
  baseline and a `HEAD^` diff). If the code is not yet fixed, follow *Fix a platform bug* in
  SKILL.md.
5. **Why the MR was green:** MR pipelines compare against the MR target branch, which is correct.
6. Reply: see developer-communication ("Platform bug, fixed").


Blast radius of the fix: only non-MR pushes on protected/default branches change; MR behaviour is
untouched — prove with the context-matrix tests.
