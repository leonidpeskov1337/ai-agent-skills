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
  - **OOM or killed analyzer** → verify effective pod limits and analyzer-specific worker
    sizing. For Advanced SAST, check the `Detected N CPU Cores` and `Detected N MB`
    lines and the `-max_memory` value of each `lightz-core` worker against the pod's
    `MemoryLimit`. A misleading `no such file or directory` warning may appear earlier in the
    log; it is not the cause.
    For KICS (`kics-iac-sast`), the supplied 19.4 incident reports node-level
    `Total memory` output. Check `MemoryLimit overwritten` and the actual pod/cgroup
    limit. A KICS OOM routes to platform for investigation as `kics_resolver_oom`.
    Confirm the cause with effective configuration, input files and resource evidence.
    Inspect downloaded artifacts and YAML/JSON references to large files. On an
    approved sandbox canary, evaluate locked `KICS_MAX_RESOLVER_DEPTH: "0"` against
    the prior setting, comparing exact rule/file/line findings and peak memory.
    Check `ERR Timeout processing the results` even if the job succeeded. Evaluate
    `KICS_TIMEOUT: "300"` against the analyzer version, query completion and job budget.
    For an approved reproduction, use an isolated checkout including the failing
    job's artifacts, inspect archives before extraction and measure on native
    supported architecture. Compare Linux cgroup `memory.peak` or native RSS with
    pod limits, accounting for units and scope. The supplied emulated runs timed
    out and underestimated memory. Apply policy changes through the owning source
    after approval and coverage verification.
  - **Analyzer image pull limits** → mirror the analyzers and set `SECURE_ANALYZERS_PREFIX`.
3. A dependency scanning job → go to [dependency-resolution](dependency-resolution.md).
4. Unclassified → compare against the last green run of the same job in the same project (what
  changed?) and against the same job in a similar project. Narrow it to the project or the
  platform.
5. Do not "fix" with `FAIL_NEVER` or by blocking jobs estate-wide. Policies cannot set `retry`;
  retry transient failures manually.
6. State the owner and the fix. If the project owns it and it recurs across projects, add a row
  to the developer-facing documentation.
