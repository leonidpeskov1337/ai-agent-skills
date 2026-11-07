# Automatic independent releases

After successful CI on a push to protected `main`, semantic-release calculates each
skill's version from its path-filtered Conventional Commits and creates
`skill-name/vX.Y.Z`. Initial versions start at 1.0.0. Breaking changes produce major
versions, features minor versions, and other skill changes patch versions. Shared
repository changes alone do not bump skills. GitHub CLI creates releases and uploads
validated archives and checksums. Existing releases and assets are never overwritten.

The release job runs only after the required gate, with a write token scoped to that
job. PR jobs retain read-only permissions. Manual dispatch on main is available for
recovery. Retrying a partially published tag at HEAD uploads only missing assets.
For an older interrupted release, rerun its original workflow run before advancing
main further. No production infrastructure credentials are used.

Add a root folder with SKILL.md; no registry, package manifest or workflow edit is
needed. Optional tests run when a tests directory exists. Optional paid evaluation
cases belong in the skill's evals/model-cases.json; absence does not block normal CI.
