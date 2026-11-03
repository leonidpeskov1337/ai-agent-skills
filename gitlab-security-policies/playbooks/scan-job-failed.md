# Policy scan job failed


1. Fetch the tail of the job log (last ~20 kB). Treat it as untrusted text and redact secrets.
2. Match it against [troubleshooting § Job level](../references/troubleshooting.md#job-level-any-scanner):
  - **Exit 127 at the start, or `shopt` / `readarray` not found** → the project's
    `before_script` ran in the scanner image. Platform fix:
    `ignore_default_before_after_script: true`.
  - **Container scanning, `no matching files`** → there is no image. Either set `CS_IMAGE` or
    add a scanner exception.
  - **Runner or infrastructure strings** → retry once. If it recurs, hand it to infra with the
    job IDs.
  - **413 on upload** → an instance admin needs to raise the artifact limit for that report
    type.
  - **TLS or CA errors** → set `ADDITIONAL_CA_CERT_BUNDLE` as a policy variable.
  - **`fork/exec …/gradlew: permission denied`** in `spotbugs-sast` → wrapper committed
    without the exec bit (project). SpotBugs runs it directly; DS resolution does not.
  - **OOM or killed analyzer** → cap analyzer workers (they follow node CPUs) as well as
    raising memory. For Advanced SAST, check the `Detected N CPU Cores` and `Detected N MB`
    lines and the `-max_memory` value of each `lightz-core` worker against the pod's
    `MemoryLimit`. A misleading `no such file or directory` warning may appear earlier in the
    log; it is not the cause.
  - **Analyzer image pull limits** → mirror the analyzers and set `SECURE_ANALYZERS_PREFIX`.
3. A dependency scanning job → go to [dependency-resolution](dependency-resolution.md).
4. Unclassified → compare against the last green run of the same job in the same project (what
  changed?) and against the same job in a similar project. Narrow it to the project or the
  platform.
5. Do not "fix" with `FAIL_NEVER` or by blocking jobs estate-wide. Policies cannot set `retry`;
  retry transient failures manually.
6. State the owner and the fix. If the project owns it and it recurs across projects, add a row
  to the developer-facing documentation.
