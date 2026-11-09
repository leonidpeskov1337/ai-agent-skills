# Profiles and exceptions


## Choosing the narrowest fix


| Situation | Action |
|---|---|
| One finding is a false positive or accepted tradeoff for this repo | Local exception file |
| Same rule is a false positive across many repos | Global exception in the platform repo |
| Rule threshold/config is miscalibrated for how the organisation writes code | Change the shared profile, with evidence |
| A team/value stream has a legitimately different convention | Dedicated profile variant for that scope |


An exception silences a specific finding; a profile change tunes a rule for everyone inheriting it.
Always carry a reason and an owner; prefer expiry dates.


A dedicated profile is **not** a per-project override. It is a profile directory maintained like
the canonical one (ideally a named variant in the platform repo) selected with a profile-path input
that replaces the downloaded bundle with the checkout's own tree. The platform's own fixture
pipelines use the same mechanism to self-test.


## Profiles: single source of truth


- `profiles/` in the platform repo is the **only** editable copy of every rule file, the global
 exceptions file and the profile version. Templates must never embed rule content, and every
 profile file must be consumed by some template. Both are enforced by the structural verifier.
- Project-level analyzer configs (`.detekt.yml`, `ruleset.xml`, …) never replace the central
 profile. Teams use local exceptions or a reviewed dedicated variant.
- Release: one deterministic, immutable `.tar.gz` (sorted members, normalized owner and mode,
 zero timestamps). It goes to the generic registry as `<name>/<version>/<name>-<version>.tar.gz`
 **before** the release tag. **Bundle version = component version**: there is exactly one
 version literal, and the release tool bumps it.
- The publish step refuses to overwrite an existing version with different bytes. An MR check
 rebuilds the bundle and fails if `profiles/` differs from the published bundle of the pinned
 version.
- Runtime: one profiles job downloads the pinned bundle and asserts that every expected file exists
 and is non-empty. The verifier checks that this list covers the whole tree. A silent fallback to
 analyzer defaults produces fewer findings and looks like an improvement. Analyzer jobs get the
 tree as an artifact.
- **No runtime checksum, by design.** The version pin, immutable publish and MR equality check give
 the same guarantee. Third-party analyzer archives stay sha256-verified because they execute code.
- Only exact allow-listed paths may be executable inside the bundle (for example a JS lint config
 module).
- Profile changes are reviewed and released like code, with evidence (sample findings, counts per
 rule).
- Tune by evidence: run the pilot in `report` mode, bucket findings by rule, and retune only rules
 that are non-actionable. Exclude test paths only for production-convention rules; bug-finding
 rules stay active everywhere. Record the rationale next to the rule or in the README.


## Exceptions workflow


1. Get the exact finding from the report: `check_name`, path, engine, fingerprint.
2. Pick the narrowest selector that matches (fingerprint > rule+path > rule > path).
3. Add to the correct file (local vs global); include `key`, `reason`, `owner`, `expires`.
4. Validate against the platform's own loader (do not hand-check); confirm the finding appears under
  applied exceptions in the summary and leaves the gate counts.
5. A selector that matches nothing is silent, so always confirm the finding actually disappeared.


Case-sensitivity and glob semantics (`*` also matches `/`) differ between tools; copy `check_name`
verbatim (for example some linters prefix rule groups). If the repository ships an
exceptions-authoring skill, use it.


## Common mistakes


- Exception with only a broad path glob that hides future real findings.
- Global exception for what is one team's preference.
- Editing profiles to silence one repo.
- Forgetting that expired exceptions stop applying, re-surfacing findings and failing a block gate.
