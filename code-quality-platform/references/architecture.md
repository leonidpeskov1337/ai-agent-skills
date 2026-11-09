# Architecture


## Component model


A CI/CD component repo is a **composition root plus self-contained templates**.


```text
codequality (composition root)         declares every public input; includes templates by rule
├── profiles          download + verify the shared rule/profile bundle (unconditional)
├── <analyzer>:scan   run a pinned analyzer, write native report + execution manifest
├── <analyzer>:report normalize to Code Quality JSON, fingerprint, fold manifest -> health file
├── cpd               duplication (one template parameterised by language)
├── coverage          ingest coverage reports -> normalized coverage artifact
├── quality-summary   aggregate analyzers + coverage + duplication + baseline diff
└── quality-gate      evaluate thresholds from the summary; the only job that fails the build
```


Rules of thumb:


- The root re-declares every leaf input so consumers see one flat, documented surface.
- Each analyzer template is self-contained and follows the same shape; shared logic (profile
 download, exception matching, fingerprinting, aggregation) lives once, not per analyzer.
- Analyzer jobs **publish**, only the gate **decides**. Analyzer jobs should not fail the pipeline
 on findings; they fail only when they cannot do their job. The manifest is written only after a
 successful run, so a crash surfaces as `no_health_evidence` in the summary.
- Every job is a pure function of pinned inputs + repository content + CI variables, so it can
 be reproduced from a unit test by constructing the environment.


## Artifacts flow


```text
build/test job ──(coverage xml, compiled classes)──► coverage / bytecode analyzers
analyzer:scan ──raw report + scan manifest──► analyzer:report ──gl-code-quality-*.json,
                                                              quality-analyzer-*.json──► summary
baseline (previous default/protected-branch summary) ─────────────────────────────────► summary
summary ──quality-summary.json──► gate ──decision artifact + exit code
```


- Consume existing build outputs (coverage, bytecode) via `needs:` with `artifacts: true` and
 `optional: true` where the producer may not exist. Do not recompile.
- Keep the producer job *names* as inputs (`*_job_name`) so consumers with different pipelines can
 adapt without forking.


## Contexts the components must handle


| Context | Pipeline source | Baseline | Diff base |
|---|---|---|---|
| Merge request pipeline | `merge_request_event` | MR target branch | `CI_MERGE_REQUEST_DIFF_BASE_SHA` |
| Branch push (feature) | `push` | default/own history | merge base with default |
| Protected/default branch push | `push` | **its own** history | `HEAD^` (the pushed delta) |
| Child/downstream pipeline | `parent_pipeline` / `pipeline` | as above | as above |
| Scheduled / manual | `schedule` / `web` | as above | as above |


Consumers often wrap the platform in an intermediate component that includes it as a child
pipeline, so `parent_pipeline`/`pipeline` rules are mandatory, not optional.


## Single implementation, multiple carriers


Runtime logic exists in (a) a canonical Python module used by tests and (b) heredoc/embedded
scripts inside templates, because templates must run without extra images. Drift between them is
the main maintenance risk. Choose one strategy and enforce it
([design principles](design-principles.md#duplication-control)).


## Container images


Prefer stock pinned images from the organisation's registry mirror. Do not introduce custom
images unless unavoidable; every extra image is a supply-chain and maintenance surface.
