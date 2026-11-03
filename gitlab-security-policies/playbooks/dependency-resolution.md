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
