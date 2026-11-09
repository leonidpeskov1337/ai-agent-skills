# Testing


## Strategy


- **Unit-test the canonical module** and the **embedded template scripts** against the same
 fixtures. A helper extracts each embedded script from its template (YAML parse → script block →
 python body) and runs it, so drift fails a test.
- **Context matrix tests** for baseline/diff logic: build the CI env (`CI_PIPELINE_SOURCE`,
 `CI_COMMIT_BRANCH`, `CI_DEFAULT_BRANCH`, `CI_MERGE_REQUEST_*`) per scenario in a temp git repo and
 assert baseline ref, diff command and resulting status.
- **Adversarial/false-green tests**: missing manifest, empty report, malformed report, excluded
 package, empty diff, unavailable baseline, expired exception, duplicate exception key.
- **Regression test first** for every bug: reproduce with the production env, watch it fail, fix.
- **Fixture projects** in the repo exercise the real pipeline on the platform's own CI, including
 the dedicated-profile mechanism.


## Structural verifier


A script run in CI (`verify-components`) that fails on contract drift in the templates themselves.
Implement at least:


- façade declares and documents every forwarded input; README lists every public input;
- each analyzer's health source pattern equals its job `rules:exists` globs;
- consumer-job `needs:` are `optional: true`;
- every downloaded archive has a version and sha256 input and is verified before execution;
- every job that runs git uses an image input that provides git;
- the profile completeness guard lists every file in `profiles/`; only allow-listed executables;
- exactly one profile-version literal (bumped by the release tool);
- baseline artifacts use the long retention input; gate safety rails (config errors exit in every
 mode, block mode is the only one that fails on violations);
- fingerprint disambiguation for identical siblings exists.


## Mutation-style tests


For each safety rail, mutate the template text in a test (drop `optional: true`, change a glob,
remove the sibling salt, swallow a config error) and assert the verifier or behaviour test fails.
A test that cannot fail is not evidence.


## Commands (adapt to repo)


```sh
python3 -m venv /tmp/venv && /tmp/venv/bin/pip install PyYAML   # test deps only, pinned in repo
/tmp/venv/bin/python -m unittest discover -s tests              # full suite
python3 scripts/verify-components.py                            # component/spec verification
glci lint -f .gitlab-ci.yml  # or the CI Lint API; validates includes, rules, inputs
```


Report counts honestly (`N OK, M skipped`); skipped tests that need external tools must be named.


## Component verification


- Lint every template with realistic inputs; confirm `spec:inputs` defaults, required inputs and
 `rules:` evaluate in MR, branch, child-pipeline contexts.
- Check that every `needs:` target exists or is `optional: true`.
- Check no unpinned download, no `latest`, every archive has a checksum input.


## Platform repo's own pipeline


Green MR pipeline is mandatory before any consumer pilot. Inspect the resulting
`quality-summary.json` and gate log, not just job colours.


## Reading a consumer pipeline


Use the read-only API: project → pipeline → jobs → job trace and artifacts
(`quality-summary.json`). Take care with the user's token: read from a local untracked file or env
var, never echo it, never write it to a report.
