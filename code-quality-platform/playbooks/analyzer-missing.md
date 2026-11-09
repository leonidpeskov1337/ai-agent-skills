# Analyzer did not run / `no_health_evidence` / `report_missing`


1. Is the job absent from the pipeline? Then rules: check `CODE_QUALITY_DISABLED`, the `exists:`
  glob versus the project's real file extensions and layout, `enable_*` input, and the pipeline
  source (MR / push / child). Child pipelines need `parent_pipeline`/`pipeline` rules.
2. Job present but failed? Read the trace: pinned download/checksum failure (registry proxy), image
  pull, runner tags, analyzer crash. No manifest is expected after a crash; that is what
  makes the summary report `no_health_evidence` instead of a clean result.
3. Summary reports `no_health_evidence`/`report_missing` although the job ran? `needs:` lists the `:report` job optional? job-prefix
  mismatch between the summary and the analyzer include?
4. Bytecode-based analyzer (compiled classes)? Producer job name input correct, artifacts present,
  build tool/JDK compatible. If it is flaky for this project, the documented opt-out flag is the
  support answer, not a platform patch.
5. Confirm with the contract test: missing manifest → configuration error in every mode. If the gate
  passed despite a missing analyzer, that is a platform bug — fix with a failing test first.
