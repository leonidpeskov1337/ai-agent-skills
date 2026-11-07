# Automatic independent releases

After successful CI on a push to protected `main`, semantic-release calculates each
skill's version from its path-filtered Conventional Commits and creates
`skill-name/vX.Y.Z`. Initial versions start at 1.0.0. Breaking changes produce major
versions, features minor versions, and other skill changes patch versions. Shared
repository changes alone do not bump skills. GitHub CLI creates releases and uploads
validated archives and checksums. Existing releases and assets are never overwritten.

The release job runs only after the required gate, with a write token scoped to that
job. CI evidence applies to the exact checked-out commit. Manual recovery verifies
a successful Validation gate from the GitHub Actions app on that same SHA. PR jobs retain read-only permissions. Manual dispatch on main is available for
recovery. Retrying a partially published tag at HEAD uploads only missing assets.
For an older interrupted release, rerun its original workflow run, which checks out
that commit and packages the corresponding tag contents. No production infrastructure credentials are used.

Add a root folder with SKILL.md; no registry, package manifest or workflow edit is
needed. Optional tests run when a tests directory exists. Optional paid evaluation
cases belong in the skill's evals/model-cases.json; absence does not block normal CI.

## Runtime package policy

All regular runtime files beneath a skill are included, with their nested paths and
single top-level skill folder preserved. There is no directory or extension registry:
SQL, Terraform, protobuf, templates, PDFs and binary data need no central changes.
SKILL.md metadata is validated with the pinned official validator before building.
Archives use fixed timestamps, sorted members and fixed permissions; SHA-256 files
are generated and ZIP members are verified against the source payload.

Root tests/ and evals/ are omitted by default. `--include-dev` explicitly includes
them. README documentation stays included; development-only README links point to
the repository. A relative reference from any included Markdown file to an excluded
resource fails packaging rather than producing a broken package. Move required
runtime data out of excluded locations or opt in explicitly. Repository validation
still validates development fixtures independently of the runtime archive.

Known virtual environments, caches, build outputs, editor/agent configuration,
compiled Python, temporary files and prior .skill artifacts are excluded. Known
credential containers (.env variants, cloud/kube/SSH directories, private-key
containers, npm/netrc credentials and Terraform state) cause a hard failure. Symlinks,
non-regular files, archive traversal, duplicate entries and output inside the skill
are rejected. Default bounds are 32 MiB per file, 128 MiB total and 10,000 files;
split unusually large resources or deliberately review a bound change. These are
safety limits, not compression-ratio heuristics that reject legitimate binary assets.

Filename policy cannot establish the absence of secrets. PR packaging and trusted
release packaging both run Gitleaks over a temporary copy of the exact selected
payload, with a trusted scanner configuration and redacted output. For the same local
check, install Gitleaks and run `python -m tools.package_skill --scan-secrets`.
The optional local command without that flag does not claim content secret scanning.

Main CI uses the same affected-skill selection as PRs. Releases validate and scan
only a skill being packaged; they reuse CI's test results rather than rerunning
unrelated suites. Complete same-commit release retries do not rebuild or overwrite
assets. Skills with no path-specific commits since their latest merged release tag
skip semantic-release network analysis. Main CI runs are not cancelled by a newer
push; the serialized release group prevents overlapping tag/publish operations.
