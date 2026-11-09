# Rollout


## Principles


- Run **beside** the legacy tool until the agreed decommission date; never disable or modify the
 legacy tool as part of platform work.
- Start in `report` mode; move to `block` per wave once pilot findings are reviewed.
- External pilots only through **unmerged MRs**; the platform's own pipeline must be green first.
- Rollout order is strictly sequential; do not trigger consumer pipelines before the platform's own
 tests and MR pipeline pass.


## Phases


1. Local review + unit tests (green).
2. Platform repo MR pipeline (green).
3. Default-branch baseline checkpoint: the platform needs a baseline summary on the default/protected
  branch. *User action:* the user merges; the agent never merges.
4. Baseline lifecycle proof: demonstrate new / existing / resolved classification on controlled
  changes.
5. Intermediate component integration MR (consumer component wires the platform, coverage and
  bytecode jobs).
6. External pilot MRs per language (for example a Java service and a Kotlin service), reviewed for
  noise, false greens and runtime cost.
7. Waves: team by team, ratchet `report` → `block`; survey failures after each wave.


## Pilot review checklist


- Do all expected analyzers run and report health `succeeded` (or `skipped` with a reason)?
- Findings bucketed by rule: any obviously non-actionable rule? (tune profile with evidence)
- Gate behaviour on a config-only MR (`not_applicable`) and a real code MR.
- Coverage: producer found, excludes understood, new-code coverage available.
- Runtime/cost acceptable; no unpinned downloads; runner tags correct.


## Parity with the legacy tool


Maintain a parity table (capability → platform equivalent → gap/owner). Be explicit about what the
platform does **not** replace (for example a legacy tool's security hotspot or project-wide
dashboards) and where that signal now lives (security scanners).


## Decommission communication


State the deadline, who migrates what (platform migrates platform-owned pipelines; custom pipelines
belong to their owners), and what to do for other CI systems. Keep the platform book/docs and the
README in sync: stale "runs alongside" wording after the deadline is a documentation bug.


## Support loop


Most rollout tickets are one of: old pin (already fixed), consumer excludes, empty/config-only MR,
runner tags, or a flag to disable an optional analyzer. Use the playbooks; answer briefly with the
cause and one next action.
