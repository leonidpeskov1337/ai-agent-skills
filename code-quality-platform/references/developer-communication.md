# Developer communication


## Shape


1. **Cause in one sentence**, plain words, no internal jargon.
2. **Whose side**: platform bug, consumer config, or expected behaviour.
3. **One next action** (bump to X, remove exclude, give the MR a real diff, set flag).
4. Link the job; quote the one log line that proves it.


Keep it short and human. Say "this was a platform bug, now fixed in X" without hedging when true.
Retract earlier wrong statements explicitly.


## Templates


**Platform bug, fixed.**
> Your pipeline failed because of a bug on our side: on pushes to `<branch>` the gate compared
> against `<default branch>` instead of `<branch>`, so already-reviewed code counted as new. Fixed
> in `<component> <version>`; bump to it and re-run.


**Consumer config.**
> It fails because `<package>` is excluded from the coverage report, so the gate can't measure the
> lines you changed there. Remove the exclude (or disable coverage with `<input>: false`) and it
> will pass.


**Skipped in MR.**
> The gate skipped coverage because this MR only changes CI/config/version files — no production
> code to measure (`not_applicable`). It evaluated normally once real code changed.


**Empty diff.**
> The MR's net diff is empty (the commits cancel out), so there's nothing to compare. Add a real
> change or close it; a platform fallback is planned.


**Why wasn't it caught earlier?** Explain the context difference (MR compares to the target branch,
push compares to its own history) and what was fixed, without blaming the team.


## Rules


- Evidence over assertion: job link + the specific line.
- Don't promise dates for fixes you haven't merged/released.
- Offer the escape hatch only when appropriate (switch to `report` mode) and say what it costs.
- Never paste tokens or private log content into public channels.
