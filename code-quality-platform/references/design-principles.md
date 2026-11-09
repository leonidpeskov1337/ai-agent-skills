# Design principles


The full list with the public API, schemas and build order is in [blueprint](blueprint.md). The
core ones:


1. **One façade = one public API.** Wrappers forward inputs unchanged.
2. **The gate decides; the summary is the contract.** The gate never recomputes.
3. **Absence of evidence is a status, never "clean".**
4. **Platform errors fail in every mode; policy violations obey the mode.**
5. **Simplify by removing capability or duplication, never by weakening validation.**
6. **Tune with per-rule evidence, by scope; exceptions are the narrowest tool.**
7. **A fix is done when it reaches consumers** (release → wrapper bump → project bump).


## Prefer the simplest mature solution


Order: **platform-native capability → already-approved library → small standard-library code →
custom framework (last resort)**.


- GitLab API access, redirects, pagination, token handling: use a maintained client
 (`python-gitlab`) instead of hand-rolled `urllib`. Pin it, mirror it in the artifact registry,
 justify it in the change.
- XML: the standard library parser is fine for straightforward reports. No new dependency without a
 demonstrated problem.
- Git semantics (merge base, diff): the native `git` CLI; no Python Git abstraction unless it fixes
 a demonstrated bug.
- Simple explicit Python structures beat a schema framework added for elegance.
- Every new dependency: pinned, mirrored, justified by a correctness/maintenance benefit, listed in
 the final report.


## Duplication control


Runtime code often exists twice (canonical module + embedded template script). Options, simplest
first:


| Option | Use when | Cost |
|---|---|---|
| A. Keep embedded copies + strong equivalence/regression tests | Few functions, stable | Tests must exercise both carriers |
| B. Publish a versioned helper archive to the artifact registry; download pinned at runtime | Large shared logic | Supply-chain surface, checksum handling |
| C. Generate embedded code from the canonical module at validation/release time | Many copies | Build step, generated-file diffs |


Never introduce a custom container image to solve this. Pick the least machinery that makes drift
fail a test. A shared test helper that extracts the embedded script from the template and runs it
against the same fixtures as the canonical module is usually enough.


## Fail closed, but not noisily


- Missing evidence → fail closed in block mode.
- Nothing to evaluate → `not_applicable`, not fail.
- Cap noise at the source: tune the shared profile with evidence (a real false-positive sample)
 rather than letting every team write exceptions.


## Selective and cheap


A consumer must not pay a Docker pull or a job slot for a language it does not have. Rules
`exists:` globs, kill-switch variable first, MR/parent/branch contexts covered.


## Safe defaults, explicit opt-outs


Opt-outs are typed inputs (`*_enable`), not undocumented variables. A feature that can be wrong in
some estates (a bytecode-dependent analyzer, coverage) gets a feature flag; support replies point
at the flag instead of ad-hoc platform patches.


## Keep the public surface small and flat


Consumers see one documented input list at the root. Do not leak internal toggles. Breaking input
changes require a major bump and a migration note.


## Deliberate trade-offs worth copying


- **No runtime checksum for the profile bundle.** Version pin + immutable publish + MR check that
 `profiles/` equals the published bundle gives the same guarantee with less machinery. Third-party
 executable archives stay checksum-verified because they run code.
- **Stdlib client over an abandoned package** for the artifact registry; a maintained client for the
 GitLab API (pagination, redirects, auth on redirects are easy to get wrong).
- **No aggregate complexity gate**: complexity enters through finding severity in the profile.
- **Job artifacts as baseline store**: no database to operate; long retention input for summaries.


## Comments and docs


Comments only for non-obvious constraints. History, evidence and alternatives go in the README,
ADR, commit or MR description.
