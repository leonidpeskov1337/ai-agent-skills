# Coverage


## Contract


- Ingest the project's **existing** coverage output (JaCoCo XML, LCOV, …); do not rerun tests.
- Normalize to a per-file, per-line artifact; compute overall coverage and **new-code coverage**
 (coverage of changed executable lines).
- Publish native GitLab coverage visualization (Cobertura-style) where supported so the MR diff
 shows covered/uncovered lines.
- Producer job names are inputs (`coverage_job_name`, `*_bytecode_job_name`). An empty
 `coverage_job_name` removes the bridge (coverage criteria become unavailable, so such projects
 stay in report mode or set coverage thresholds empty). Build wrappers expose their own
 producer-job toggle.


## Metric statuses (what the gate sees)


| Situation | Status |
|---|---|
| Changed lines exist in files present in the coverage report | available |
| No analyzable production source changed (CI config, docs, version files, tests only) | `not_applicable` |
| Changed production lines are non-executable (imports, declarations) | `no_covered_executable_lines` |
| Changed production source file absent from coverage data | `unavailable` |
| No coverage report at all but production code changed | `unavailable` |


## The excludes trap


Consumers often exclude packages from the coverage tool (`**/config/**`, `**/service/**`,
generated code). Those classes are **absent** from the report, so any change to them makes
new-code coverage `unavailable` and fails closed in block mode. This is correct behaviour and a
consumer configuration cause. Resolution options:


1. Remove the exclude so the code is measured (preferred).
2. Clear the coverage thresholds for the project and accept the lost signal.
3. Platform-level: narrow what counts as "analyzable production source" if the exclusion is a
  common, legitimate pattern — a change to the contract, review it as such.


## Multi-module and path mapping


Coverage report paths are package-relative; map them to repository-relative paths using the
declared source roots. Cover Gradle/Maven multi-module layouts and Kotlin/Java mixed roots in
tests. A path-mapping bug shows up as "unavailable" for files that clearly have coverage.


## Quick triage


1. Is the changed file under an exclude pattern in the build's coverage config?
2. Is the file in the coverage XML (search by package/class)?
3. Did the coverage producer job run and upload on this pipeline (artifact present)?
4. Is the diff base available (see baseline contract)?


## Producer and visualization design


- The build owns tests. Add a dedicated **coverage producer job** in the build component that
 turns raw execution data into XML plus compiled classes using the consumer's own JDK/toolchain
 image. A build that only ships binary execution data (for example `test.exec`) cannot be
 consumed reliably by a generic image.
- Two independent GitLab features, both fed from the same numbers:
 - `artifacts:reports:coverage_report` (Cobertura) for line annotations in the MR diff; LCOV is
   converted first.
 - the job `coverage:` regex for the MR widget and pipeline badge. The summary prints exactly one
   anchored line (`<Org> overall instruction coverage: 83.32%`, two decimals) and the regex
   matches only that line, so widget and JSON cannot disagree.
- Metric: JaCoCo `INSTRUCTION` counters (not line coverage like some legacy tools; numbers will
 differ, say so in docs); LCOV `DA` lines. Drop vs baseline only within the same metric.
- Multi-module: recursive glob, aggregate all reports; the bridge **fails when the glob matches
 nothing**. GitLab annotations cannot disambiguate duplicate relative paths across modules.
- LCOV scope: a changed file absent from the tracefile is `not_applicable` (outside the runner's
 coverage scope), unlike JaCoCo where it is `unavailable`.
