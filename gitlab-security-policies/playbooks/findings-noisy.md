# Too many findings, or "are these real?"


1. Pull the findings for the pipeline with GraphQL or the vulnerability export.
2. Classify them:
  - by scanner (SCA vs SAST vs secrets vs IaC);
  - by location file or module;
  - for SCA, by configuration (release vs test, lint, debug or annotation processors);
  - by severity;
  - new vs existing.
3. Count the per-module duplicates: unique (package, version, advisory) against total.
  Android: the analyzer treats only `test*`/`androidTest*` configurations as development, so
  variant test configurations are reported as production.
  If almost everything is "new", check the default-branch baseline: a failed resolution there
  leaves a tiny baseline.
4. Report the *shipped* subset first. That is what needs fixing.
5. Explain the rest honestly. The scanner reports what the build resolves, and reachability is
  not assessed. See [developer-communication](../references/developer-communication.md).
6. Reduce the noise centrally if it is systematic:
  - path exceptions for vendored or test trees;
  - scanner settings that limit configurations, where supported.


  Do not lower the gate thresholds.
7. If it is project-specific, remediate (upgrade or constrain), or dismiss with a reason.
