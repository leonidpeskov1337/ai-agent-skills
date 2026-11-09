# Gate shows SKIPPED / not_applicable and the user expected a check


`SKIPPED <metric>: not_applicable` with `Quality Gate PASSED` means no analyzable production
source changed in the diff.


1. List the MR's changed files. If they are only CI config, docs, version files, build scripts or
  tests, `not_applicable` is correct.
2. If production code did change: check the language/extension is in the analyzable set and the
  source-path inputs cover it; check the diff base is the right one.
3. If a later push of the same code fails (for example after merge), compare contexts: see
  [gate-fails-after-merge](gate-fails-after-merge.md).
4. Answer plainly: "the gate skipped coverage because this MR changes no production code."


## `SKIPPED <metric>: baseline_missing`


No usable baseline summary exists for the reference branch (first run, expired artifacts, last
pipeline failed before the summary, or a fingerprint schema change). New-finding counts and the
overall coverage drop cannot be compared, so they are skipped rather than reported as zero. The
next successful pipeline on the reference branch creates the baseline; check the retention input
if this recurs.
