# Dependency scanning resolution or scan failure


Jobs: `dependency-scanning:<ecosystem>-resolution` runs in `.pre` and produces graph files; then
`dependency-scanning` builds the SBOM, scans it and uploads the report.


1. **Which job failed?** Resolution or the scan. If resolution is green but the scan failed,
  check for a 413 on the CycloneDX upload (admin) or a parsing error (project file format).
2. **Gradle:**
  - `requires at least JVM runtime version N` → the project adds
    `gradle/gradle-daemon-jvm.properties` with `toolchainVersion=N`. That needs a wrapper of
    Gradle 8.8 or later (9.1 or later for JDK 25), and the resolution image must ship JDK N.
  - Toolchain not found or the download fails → provide a multi-JDK image via
    `DS_GRADLE_RESOLUTION_IMAGE` (platform).
  - Gradle older than 7.3 (`Unsupported class file major version 61`) → upgrade the wrapper.
  - A wrapper without the exec bit does **not** break DS v2 resolution, which runs
    `sh ./gradlew`. That error comes from `spotbugs-sast`; see
    [scan-job-failed](scan-job-failed.md).
  - `Java heap space` → `GRADLE_CLI_OPTS: "-Dorg.gradle.jvmargs=-Xmx2g"` as a project CI/CD
    settings variable.
  - Builds that guard files by task name → include `dependencies`, `projects`, `properties`.
  - Nested build (`Project with path … could not be found`, `GradleWrapperMain`) → restructure
    the build, or add a path exception.
  - Missing local files (`local.properties`, `google-services.json`) → commit CI-safe defaults.
  - HTTP 429 from Maven Central → route through the proxy.
  - Plugin not found in the internal repository → publish it or fix the version.
3. **Python:**
  - `No matching distribution found for <internal>` → pin `PIP_INDEX_URL` to an internal
    superset index (platform). `pip-compile` ignores `[tool.uv]` indexes.
  - Absolute constraints path → make it repository-relative.
  - `expected pip-compile lock file but found plain manifest` is a warning; find the real
    error further down.
  - `git+` URLs or native builds failing in `pip-compile` → project fix or path exception.
4. **Maven:** check for repository access or proxy problems and unpublished internal artifacts.
5. **Sidecar script not found after 60 s** → retry manually (policies cannot set `retry`). If it persists, check the runner's resources.
6. **Verify** after the fix:
  - the graph file contains the expected package;
  - the scan job uploaded `dependency_scanning` and `cyclonedx` artifacts;
  - the findings appear in the pipeline's Security tab.
7. **Survey for siblings.** The same plugin or convention usually fails in many projects. Fix it
  once at the shared convention.

8. **Slow resolution delaying builds?** Measure the `.pre` job's critical-path impact first;
  jobs using `needs` may start independently. If the project already builds the same dependency
  scope, evaluate exporting its graph there and disabling only that ecosystem's automatic
  resolution. Use the checklist below; do not trade runtime for missing transitive coverage.

## Graph in the build job

For a Gradle canary (Maven uses its own supported export format):

1. Generate `gradle.graph.txt` in the existing build job. For multiple modules, register a
   `DependencyReportTask` per project with a reviewed init script, writing each graph into
   that module's directory. Run included builds separately (`-p <dir>`); a root-only
   `dependencies` invocation does not establish complete coverage.
2. Check every expected module graph for non-empty, successfully resolved dependencies and
   representative direct/transitive packages. Upload `**/gradle.graph.txt` as artifacts.
3. Inspect the merged pipeline: the producer must finish before the scan, in an earlier stage
   or through supported explicit artifact dependencies. Verify actual artifact downloads.
   An injected `scan-policies` stage can precede all project stages if `build` is absent.
4. Set `DS_DISABLED_RESOLUTION_JOBS: gradle` only for pipelines that reliably produce the graph,
   through the owning policy/configuration mechanism. Preserve any other disabled-ecosystem
   entries deliberately. If only MR pipelines build graphs, a tested
   `workflow:rules:variables` condition can leave default-branch resolution enabled. Confirm
   policy variable locking does not override the intended value.
5. Compare SBOM component sets, transitive scope, finding UUIDs/states and counts against the
   same revision and advisory data before and after. Equal counts alone do not prove parity.
   Test MR, default branch, merged results/train and scheduled sources that are in scope.
6. Record critical-path improvement, failures and ingestion evidence. On missing/incomplete
   graphs, fail visibly and restore the automatic resolver rather than accept manifest fallback.

Both approaches execute project build tooling. Keep platform secrets out of the producer.
The supplied 19.4.5 Android example reports 899 seconds in `.pre` versus project jobs starting
in about five seconds with graph generation moved into the build. This is attributed canary
evidence, not a guaranteed speed-up or a complete scan-duration comparison.
