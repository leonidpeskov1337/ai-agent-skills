# Fix is merged but consumers still fail


1. Was the platform released? Check the main pipeline: bump → tag → release.
2. Does the intermediate consumer component default point at the new release? (Check the file at
  its latest tag, not the branch.)
3. Which version does the failing project include? (Open its CI config / the job's resolved
  includes.) It is almost always an old pin.
4. Tell the developers exactly what to bump and to which version; link the migration note if the
  move changed input names.
5. If the project is already on the fixed version and still fails, it is a *new* problem: restart
  triage with the job log and summary artifact.
