# Too many findings / "are these real?"


1. Bucket findings by `engine_name` and rule from `gl-code-quality-*.json`; look at the top 5 rules.
2. For each top rule decide: real defect, style preference, or miscalibrated threshold.
3. Real → the team fixes. One-off → local exception. Many repos → global exception. Miscalibrated
  → profile change with the sample as evidence ([profiles-and-exceptions](../references/profiles-and-exceptions.md)).
4. "Why was this not caught earlier?" — usually the finding is *new code* only (baseline diff) or
  the analyzer was only recently enabled; show the context difference.
5. Never raise thresholds or disable analyzers to make one pipeline pass.
