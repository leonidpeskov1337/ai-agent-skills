# Release and propagation


## Delivery chain


```text
platform repo release  →  intermediate consumer component bump  →  project pin bump
(codequality 1.x.y)       (java/kotlin publish component)          (developer's CI include)
```


A fix does not reach any project until each link is released and the project bumps its pin.
After a platform fix always report: released version, whether the intermediate component default
was bumped, and the exact version developers should take.


## Release-driven versioning


- Conventional/commitizen commit messages drive the bump (`fix:` patch, `feat:` minor,
 `BREAKING CHANGE`/`!` major). Hotfix branches use `fix:`.
- Prefer a maintained versioning component over bespoke scripts. Typical contract: a committed
 version file (`.version`) plus the tool config (`.cz.toml` `version_files` listing it), a bump
 job on the protected branch, a tag, then a release job that runs only when a bump actually
 happened.
- Non-release pipelines get pre-release identifiers (`-dev.<pipeline_id>`, `-alpha`, `-rc`,
 `-SNAPSHOT` for Maven); confirm the formats with the tool, do not guess.


## Pitfalls (met in practice)


- **Bot identity vs push rules.** The bump job commits as a bot; push rules that require the
 committer email to belong to a known user reject it (`committer email not allowed`). The
 versioning component's bot username variable must exist as a CI variable and the identity must be
 allowed. A legacy component with a different hard-coded bot identity fails after the repo's push
 rules change.
- **Invalid input interpolation.** `$[[ inputs.x ]]` is valid only inside files that declare
 `spec:inputs` (component templates). In a project's own `.gitlab-ci.yml` it is a syntax error;
 use a literal or a CI variable.
- **Stage names are owned by the component** (for example it may force `init`); declare them.
- **Runner tags.** Estates without untagged runners need explicit tags on every job including the
 versioning component's (`job_tags` or equivalent), otherwise jobs stay pending forever.
- **Release job guard:** run the release step only when the bump job reports a bump, else you create
 duplicate or empty releases.
- **Variable visibility.** Some tokens may be unable to read project variables (403); do not claim a
 variable exists or is missing without evidence — ask the owner or read the job log.


## Verifying a release


1. Main pipeline: bump → tag → release jobs all green.
2. Tag and release exist at the expected version.
3. Intermediate component default input points at the new version; its own pipeline is green.
4. A consumer MR (unmerged) including the new pin passes component resolution.


## Telling developers


State: what changed, which version to bump to, where (the include line), and what behaviour
differs. Link the migration guide for breaking moves.


## Release ordering for profiles


A version must not exist as a tag before everything it references is published. The pipeline on
the default branch runs `test:profiles` and then `publish:profiles` (idempotent, and it refuses
differing bytes). Only after that does it create the release tag. The bundle version and the
component version come from the same literal that the release tool bumps.
