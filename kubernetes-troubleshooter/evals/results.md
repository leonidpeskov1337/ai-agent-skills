# Validation and evaluation results

## Maintainer review follow-up — 2026-11-03

An independent reviewer scored randomized A/B pairs for the ten existing incident
fixtures. Each pair contained the saved with-skill report and a fresh report from an
agent given only the fixtures. The reviewer received the rubric and fixtures. The
condition key was held separately until scoring finished. The saved reports and the
fresh baseline came from separate runs, and their formats could provide clues about
condition. This small retrospective comparison measures performance on this rubric.

| Condition | Assertions passed | Rate |
|---|---:|---:|
| With skill (saved reports) | 24/24 | 100% |
| Without skill (fresh baseline) | 21/24 | 87.5% |

The baseline missed an explicit retraction, the names of simultaneous deployment
changes, and controller permissions as an explanation for missing NodeClaims.
See the [baseline reports](real-incident-baseline-reports.json) and
[blind grades](real-incident-blind-grading.json).

The follow-up also adds [three counterexamples](counterexample-fixtures.json) with
a [separate rubric](counterexample-evals.json) for local lock contention, a justified
HPA cap increase, and quota consumed by other clusters. Parent review scored the
[offline reports](counterexample-reports.json) 6/6 against that rubric. The helper
suite passed all 46 tests, including the new metadata request and selector
validation test. Both skill validators passed.

Earlier build results below are retained for provenance. The incident-pattern
upgrade section at the end records the earlier 45-test suite and its scenarios.

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

## Prompt and Argo CD extension — 2026-10-31

Executed the full updated helper suite: **37 tests passed** (original 29 plus 8
Argo tests). Both Anthropic and host Skill Creator validators again returned
`Skill is valid!`. The prompt's YAML block was parsed using the existing temporary
PyYAML dependency; optional/unknown fields and read-only/remote-read defaults have
the intended types. Packaging includes the prompt, ArgoCD folder and new helper.

New transport/projection tests preserve ordered multi-source revisions, remote
destinations, parent Application tracking and ApplicationSet ownership/conditions,
while excluding inline Helm values, plugin data, generator credential data,
manifests and credentials in source/destination URLs. They also cover nullable
optional fields, explicit control-plane context and denied Application reads.
Status/error messages remain subject to best-effort redaction and manual review.

A fresh agent completed six synthetic scenarios using the skill and raw inputs,
without reading expected answers or making external/credential reads. Parent manual
review found **12/12 prewritten assertions satisfied**. Cases covered unrelated Argo
drift, remote management despite a disabled hint, runtime latency despite Synced/
Healthy, multi-source/local-versus-applied revisions, blocked migration hooks and
ApplicationSet ownership, and copied tracking/denied access with scheduler pressure.
The evaluator suggested clarifying that FailedCreate is not evidence of migration
execution; that clarification was applied. No material routing gap was reported.

This was one batched extension run with parent grading, not a repeated independent
benchmark or a new baseline comparison. The initial 15-case model evaluation was
not rerun. No claim of live Argo/GitHub/GitLab integration or token-file authentication
is made; those require authorized host tools/adapters and real environment testing.

- [Extension raw fixtures](argocd-fixtures.json)
- [Extension assertions](argocd-evals.json)
- [Independent agent reports](argocd-reports.json)
- [Parent-reviewed grades with report excerpts](argocd-grading.json)

A static official-framework viewer is generated under the local untracked
`kubernetes-troubleshooter-workspace/argocd/review.html` for optional human review.

## Incident-pattern upgrade — 2026-11-02

Applied all 27 file replacements/additions from the supplied ready-to-use upgrade,
preserving unchanged transport behavior and existing Argo/prompt support. Added
five playbooks (32 total), request modes, claim corrections, business-hour and
busiest-unit comparisons, managed dependency/quota attribution, and expanded
probe/HPA/PDB/placement/NodePool/NodeClaim evidence projection.

Executed checks:

- **45 helper tests passed**: the existing 37, six supplied capacity-projection
  tests and two added regressions for probe credential exclusion and scoped
  read-only collection. Only local mock HTTP networking was used.
- Both official skill validators returned `Skill is valid!`.
- All 32 playbooks are indexed; relative source/package links, evaluation JSON,
  Python compilation and ZIP integrity passed. Prompt/Argo files were retained.
- Existing transport, redaction, tracking and scoped-read function ASTs match
  the previous commit; only the resource projection/allowlist was expanded.

The suggestions were retained except for documented correctness/safety improvements:
HPA versus workload-controller roles; availability versus scale-down; missing-claim
and audit-search uncertainty; memory/cache/ancestor-quota semantics; complete pod
ephemeral-storage accounting; blackbox time-to-first-byte interpretation; cache-node
metric dimensions; safe plan/render handling; and filtering probe exec commands,
HTTP header values and query values. Source provenance lists the official references.
The source case summaries and reported outcomes were not independently verified.

The supplied eight evaluation prompts lacked raw artifacts and some expected outputs
assumed a diagnosis. Added explicitly synthetic replay inputs and made the expectations
evidence-dependent. A fresh agent read only the skill/references and ten raw fixtures
(eight supplied patterns plus two counterexamples), made no external/credential reads
or changes, and produced [ten reports](real-incident-reports.json). Parent manual
review found **24/24 assertions satisfied**; [grades contain report excerpts](real-incident-grading.json).
The evaluator flagged missing calendar dates in a comparison scenario; guidance
now explicitly resolves relative dates and checks actual weekday/holiday/coverage
before declaring windows matched. This clarification followed the replay run.

Inputs and rubric: [raw fixtures](real-incident-fixtures.json),
[evaluation scenarios](real-incident-evals.json). The official static viewer is
generated under local untracked
`kubernetes-troubleshooter-workspace/production-upgrade/review.html`.

Limits: one batched with-skill replay and parent grading, no new baseline or repeated
model runs, no live cluster/cloud/provider integration, and no measured model
latency/token-efficiency claims. Earlier build evaluations were not rerun; the full
helper suite was. These results do not establish production incident success rate.
