# Expected finding missing


1. **Scan ran and uploaded?** The scan job (not just the `.pre` resolution job, which people
  often mistake for the scan) must be `success`, with the report artifact present. A 413 or a
  failure means nothing was ingested. A failed resolution job silently falls back to direct
  dependencies only, so transitive findings disappear.
2. **Right pipeline?** An MR's findings come from the MR pipeline at its head. Compare them with
  the target branch, where the finding may already exist and is then not "new".
3. **Dependency in scope?** Check that the package and version are in the graph or SBOM. Look for
  version catalogs (`libs.versions.toml`), BOMs, constraints and the configurations resolved.
4. **Advisory matches?** Check the advisory's affected range, not the CVE headline. Was the
  advisory DB date before or after the scan?
5. **Already handled?** Look for state `DISMISSED` (by the policy bot, an exception or a human)
  or `RESOLVED`.
6. **UI truncation?** The MR widget shows a limited number. Use the pipeline Security tab or
  GraphQL.
7. **Suppressed in the repository?** Check `.gitlab/sast-ruleset.toml`, a gitleaks config, and
  `*_EXCLUDED_PATHS` from a path exception.
8. **Canary test:** add a known-vulnerable dependency, then check separately the graph file,
  the scan job's report, and ingestion into the Security tab.
9. **Reproduce** in a sandbox project with the same manifest. Report a product bug only with a
  minimal reproduction.
