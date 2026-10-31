# Validation and evaluation results

Executed 2026-10-31 on Windows, Python 3.14.7. No live cluster, production API or real
credentials were used. Runtime helpers require only Python 3.10+ standard library;
PyYAML 6.0.3 was installed into a temporary validation-only directory.

## Executed checks

| Check | Result | Scope |
|---|---|---|
| `python -m unittest discover -s kubernetes-troubleshooter/tests -v` | 29 passed | Local fake HTTP + mocked/process fixtures |
| Anthropic Skill Creator `scripts/quick_validate.py` | Skill is valid | Downloaded official current validator |
| Host Skill Creator `scripts/quick_validate.py` | Skill is valid | Installed framework validator |
| Python source compilation and fixture JSON parsing | Passed | Scripts and raw fixture/rubric files |
| Static evaluation viewer | Generated with official `eval-viewer/generate_review.py` | Local workspace, 30 per-case outputs plus aggregate reports |
| Correctness aggregation | Generated with official `scripts/aggregate_benchmark.py` | One evaluation run per configuration per case |

Helper tests cover explicit context, resource allowlisting, RBAC failure vs empty
success, invalid Kubernetes JSON, sensitive-field omission, init-container scheduling
capacity, CronJob nesting, event redaction, subprocess timeout/byte bounds, missing
executables, backend classification, Mimir prefix/auth/tenant headers, query/range/series/
name APIs, warnings, empty results, HTTP/API/JSON errors, redirects, header injection,
TLS/URL validation, response byte bounds, slow-trickle elapsed checks and finite-sample
analysis. Loopback HTTP tests require a host execution profile that permits local
networking; sandbox-only attempts initially failed, then all tests ran successfully
with loopback access. An independent review found redaction corruption, pre-redaction
disk spooling and weak elapsed/tree timeout handling; fixes and regression checks
were applied. Detached credential processes and OS DNS deadlines remain host limits.

## Behavioral evaluation

Two fresh agents investigated the same 15 supplied-evidence synthetic incidents,
one with the skill/references and one without them. They did not read expected
answers or each other's outputs. A separate grader then evaluated the two assertions
per case against report content and raw evidence. No helper execution or live data
collection was implied by these reasoning runs.

| Configuration | Assertions passed | Rate |
|---|---|---|
| With skill | 30/30 | 100% |
| Without skill | 29/30 | 96.7% |

The baseline CPU-latency assessment omitted explicit consideration of HPA/scaling
evidence before assigning cause (case 3). Both runs addressed missing history,
limited access, duplicate scrapes, misleading logs, healthy/no-reproduction cases,
and safe proposed remediation. No additional materially unsafe statements were
identified by the grader.

This small, mostly straightforward fixture set produces a near-ceiling baseline.
It does **not** establish a statistically meaningful improvement or production
incident success rate. Cases were batched within each configuration, so they are
not independent per-case model samples. Full framework description optimization,
repeated/blinded comparisons and live disposable-cluster integration were not run.
Token, execution-time and tool-call counts were not exposed by agent notifications;
zeros emitted by the official aggregation defaults are **unavailable**, not measured
cost or latency. No resource-efficiency claim is made.

Raw reproducible records:

- [Requests and grading rubric](evals.json)
- [Synthetic input evidence](fixtures.json)
- [With-skill reports](with_skill-reports.json)
- [Baseline reports](without_skill-reports.json)
- [Independent per-assertion grades and excerpts](grading.json)

The local untracked `kubernetes-troubleshooter-workspace/iteration-1/` holds the
official aggregate JSON/Markdown and static `review.html`. Source grading and reports
above are committed for portable review. The package builder verifies ZIP integrity;
the generated checksum accompanies the local `.skill` artifact.
