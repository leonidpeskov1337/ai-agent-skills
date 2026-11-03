# Design principles


These are recommended defaults for a production GitLab security-policy programme. Each one gives
the reason for the default and the trade-off. Departing from a default is legitimate if the
reason is recorded in a decision record.


## Contents


1. [Governance model](#governance-model)
2. [Enforcement modes](#enforcement-modes)
3. [Scanner catalogue](#scanner-catalogue)
4. [Pipelines and triggers](#pipelines-and-triggers)
5. [Gates](#gates)
6. [Exceptions](#exceptions)
7. [Tamper resistance](#tamper-resistance)
8. [Supply chain of the scanners themselves](#supply-chain-of-the-scanners-themselves)
9. [DAST](#dast)
10. [Operations](#operations)
11. [Standards mapping](#standards-mapping)


## Governance model


- **Central policy, local findings.** Policies live in dedicated security policy projects owned by
 the platform or AppSec team. Developers own remediation in their own projects. Do not rely on
 project `.gitlab-ci.yml` includes for mandatory scanning: maintainers can remove those.
- **Link at the highest group that shares governance**, usually a business unit or value stream.
 Projects created later inherit the policy without anyone enumerating them.
- **A group has exactly one security policy project.** `securityPolicyProject` is singular, so
 linking a second project to the same group *replaces* the first. Where several independent
 policy sets must apply (scanners plus DAST, or per-project overrides), link the extra policy
 projects to **projects**. Project links are additive with inherited group policies.
- **Generate policy documents from a declarative source.** Use inventory YAML, Terraform variables
 or a policy-as-code repository, with review and plan or diff. Keep UI-edited policies for
 experiments only: they bypass review and drift silently.
- **One writer per policy project.** Mark generated files "managed by <tool>; manual edits are
 overwritten". Restrict maintainer access on the policy projects to the platform identity and
 break-glass admins.


## Enforcement modes


Use one vocabulary across the organisation, ratcheting **upward only**:


| Mode | Scans | Findings visible | Bot comment | Blocks MR |
|---|---|---|---|---|
| `disabled` | – | – | – | – |
| `scan` | yes | yes | – | – |
| `warn` | yes | yes | yes | until bypassed with a reason, or approved |
| `block` | yes | yes | yes | until approved |


- **Platform floor.** Set a minimum mode that business units cannot opt below. A weaker request
 resolves to the floor and a stricter one wins. Without a floor, "opt-in" becomes "never".
- **`warn` is not advisory-only.** GitLab's `enforcement_type: warn` makes the MR show
 `SECURITY_POLICIES_VIOLATIONS`. It stays unmergeable until the author bypasses with a reason or
 someone approves. (This was measured on 19.2; verify on your version.) Communicate this before
 turning it on.
- **Rollout order.** Start at `scan` for visibility, and measure the failure rate and noise. Move
 to `warn` once the false-positive and exception processes work, then to `block`. Move one
 business unit at a time.
- **Per-project relief comes from exceptions, never from the mode.** Modes are per business unit.


## Scanner catalogue


Keep one catalogue that lists, for each scanner:


- the scan action;
- its prerequisites;
- what happens when the prerequisites are missing;
- the shared approval report type;
- its variables.


| Scanner | Missing prerequisite → | Recommended scope |
|---|---|---|
| SAST (Advanced SAST, falling back to Semgrep) | skips silently | mandatory |
| IaC (KICS) | skips silently | mandatory |
| Secret detection | n/a (always runs) | mandatory |
| Dependency scanning | skips silently, or the resolution job fails | mandatory with resolution support |
| Container scanning | **job fails** (`no matching files`) | opt-in per image-building group |
| DAST | needs a deployed target | opt-in per application, via PEP |


- **Opt-in for scanners that fail on missing prerequisites.** Otherwise most projects show a red
 job that nobody can fix. In one estate only ~2.5 % of repositories built images.
- **IaC reports as `sast`.** Excepting one of SAST or IaC but not the other leaves a project that
 is still gated on a `sast` report it no longer produces.
- **Pin `template`** (`latest` or `v2` where needed) deliberately. Templates change analyzers and
 report fields.
- **Centralise resolution infrastructure** for dependency scanning. That means pinned resolution
 images, plus `PIP_INDEX_URL` or Maven/Gradle mirrors pointing at the internal proxy. Lock them as
 policy variables so projects cannot redirect them.


## Pipelines and triggers


Scan on:


- every merge request pipeline (`branch_type: all` + `pipeline_sources.including:
 [merge_request_event]`). Avoid `target_default`: in production it left MRs into non-default
 branches unscanned;
- every default-branch push (`branch_type: default` + `[push]`).


Add scheduled scans for dormant default branches, so new advisories reach unchanged code.


- Set `AST_ENABLE_MR_PIPELINES: "true"` so scanners run in MR pipelines and not only in branch
 pipelines.
- Set `scan_settings.ignore_default_before_after_script: true` on every action. Otherwise scanner
 jobs inherit the project's `default:before_script`. In one estate that killed three scanners
 per project (`shopt: not found`, exit 127) while the pipeline stayed green, because policy jobs
 are `allow_failure`. That is a silent fail-open.
- **`[skip ci]`.** Choose explicitly:
 - Allowing it avoids forcing full project pipelines onto release-bot commits. A policy-forced
   pipeline runs the project's whole `.gitlab-ci.yml`.
 - Blocking it closes a developer self-skip.
 - Allowing it is acceptable only when both of these hold:
   - default-branch pushes are restricted to reviewed paths or bots;
   - MR gates fail closed, so a skipped scan requires approval.
 - Keep `no_pipeline` blocked. It has no common legitimate use.
- **`workflow:rules` gap.** A scan execution policy cannot create a pipeline that the project's
 `workflow:rules` suppress. Where that is unacceptable, use a pipeline execution policy, or
 detect it: compare pushes against pipelines.


## Gates


- **Approval policies, not scan results alone, block merges.** Generate them only at
 `warn`/`block`.
- Default gate:
 - `severity_levels: [critical, high]`;
 - `vulnerability_states: [new_needs_triage]`;
 - `vulnerabilities_allowed: 0`;
 - `approvals_required: 1`;
 - `fallback_behavior: {fail: closed}`, so a missing report requires approval instead of passing
   silently.
- **Approvers are a small, accountable set.** Use `group_approvers` that point at per-team security
 reviewers or AppSec. Avoid `role_approvers: [developer]`. In one MR that allowed 586 people to
 approve the security gate, against 30 for the ordinary code-review rule. Verify the eligible
 set on a real MR: group membership semantics were not as documented in one test. Check the
 real role distribution before using `role_approvers` (with SSO provisioning everyone as
 Developer, `[maintainer]` makes `block` unmergeable). A gate that nobody can satisfy is worse
 than a broad one, so keep a documented fallback.
- **Branch scope.** The scanners must cover at least every branch the gate covers. A gate on
 `protected` targets with scanners on the default branch only fails closed on MRs that were
 never scanned.
- **One project scope per gate.** A gate fed by scanners with different scopes (one `excluding`,
 another `including`) has no correct `policy_scope`. Split the gate or align the scanners.
- **Bypass controls:**
 - `prevent_approval_by_author`;
 - `prevent_approval_by_commit_author`;
 - `remove_approvals_with_new_commit`;
 - `block_branch_modification`;
 - `prevent_pushing_and_force_pushing`;
 - `prevent_editing_approval_rules`.


 `require_password_to_approve` usually conflicts with SSO.
- **Dismissal unblocks** because the gate counts only `new_needs_triage`. This is safe only while
 dismissal itself is restricted. Changing vulnerability status needs Maintainer, Owner or
 Security Manager, so keep developers below Maintainer. Revisit this if that changes.
- **Separate gates per report type.** At most 5 approval policies fit in a policy project.


## Exceptions


See [exception-governance](exception-governance.md). Principles:


- Every exception carries:
 - an owner;
 - a ticket;
 - an approver, who must be the risk owner and not the requester;
 - a reason;
 - an expiry, with a maximum such as ≤ 180 days.
- Use the narrowest kind that works:
 1. dismiss named findings;
 2. skip paths for one scanner;
 3. skip a scanner for a project.
- Exceptions never touch gates' scope except where the scanner is fully excluded.
- Expiry is enforced by the generator, which fails validation, and by automation, which reverts
 dismissals. Do not rely on a calendar reminder.


## Tamper resistance


Projects must not be able to disable enforced scanning. Known escape routes, and what closes
each:


| Route | Closed by |
|---|---|
| Remove the CI include | Policies are injected, not included |
| Override `SAST_DISABLED`, `*_EXCLUDED_PATHS`, images | Policy variables take precedence and are locked |
| `default:before_script` breaks scanner | `ignore_default_before_after_script: true` |
| `[skip ci]` | `skip_ci.allowed: false`, or fail-closed gates |
| `workflow:rules` suppresses pipeline | PEP, or detection |
| Repository rulesets (`.gitlab/sast-ruleset.toml`, gitleaks config) | Locked `SECURE_ENABLE_LOCAL_CONFIGURATION: "false"` (*unverified*), or CODEOWNERS review |
| Unlocked knobs such as `DS_DISABLED_RESOLUTION_JOBS` | Only variables the policy sets are locked. Set every knob you rely on |
| Dismiss own findings | Role design: no Maintainer for authors |
| Edit MR approval rules | `prevent_editing_approval_rules` |
| Retarget DAST via project variable | Target defined in the policy project. `variables_override: {allowed: false}` |


## Supply chain of the scanners themselves


- Pull analyzer and resolution images through an internal registry or proxy. Pin custom images
 by tag, preferably by digest. Scan them with your artifact scanner, and record exceptions for
 the CVEs bundled in build tools.
- Resolution jobs **execute project build scripts** (Gradle, Maven, pip). Treat them as untrusted
 workloads. Project-set `MAVEN_ARGS`, `GRADLE_OPTS`, `JAVA_TOOL_OPTIONS` and init scripts flow
 into them, and `CI_JOB_TOKEN` and masked project variables are in scope. Never give them
 platform secrets.


## DAST


- Scheduled DAST via a **pipeline execution schedule policy**, not a scan execution `dast`
 action. The SEP `dast` action uses on-demand profiles, and active scans need a validated site
 profile. Without one, the job may be created untagged and stay pending forever.
- **No active DAST against production**, and enforce that by validation. Passive scanning of
 production is a separate, explicit decision.
- The target URL lives in the policy project (a `rules:` clause per project ID), never in a
 project variable. Anyone with project settings access could otherwise redirect an active
 attack. `protected` variables do not prevent edits.
- Link DAST policy projects **per project**. Linking them to the group would replace the scanner
 policy project.


## Operations


- Verify every change in GitLab, by checking the loaded policies and a real pipeline.
- Resync after changes when propagation matters. New projects may need an `INHERITED` resync.
- Survey failed policy jobs after each rollout wave, then weekly, as a standing control. Policy
 jobs are `allow_failure`, so a dead scanner leaves the pipeline green and is invisible at
 `scan` and easy to bypass at `warn`. Classify each failure as project, platform,
 infrastructure or product, and drive the classes to zero.
- Do not quiet failures with `FAIL_NEVER=true`, and do not make policy jobs blocking
 estate-wide: both trade a visible coverage gap for an invisible one or for broken merges.
- Before an analyzer or template migration, measure the baseline: ecosystems, wrapper and
 toolchain versions, current failure rate (one estate was already at 32 % failing) and
 finding identity on a canary.
- Publish a developer-facing page covering:
 - what runs;
 - why it runs;
 - how to read the results;
 - how to request an exception;
 - the known project-side fixes.


## Standards mapping


Use the mapping to justify controls to auditors. Cite at the requirement level and verify
against the edition in force.


| Control | NIST SSDF (SP 800-218 v1.1) | ISO/IEC 27001:2022 Annex A | Other |
|---|---|---|---|
| Central, mandatory SAST/IaC/secrets | PW.7 (review/analyse human-readable code), PO.3 (supporting toolchains) | 8.25 secure development life cycle, 8.28 secure coding | OWASP SAMM Verification – Security Testing |
| Dependency scanning/SBOM | PW.4 (reuse well-secured software), RV.1 (identify vulnerabilities continuously) | 8.8 management of technical vulnerabilities | PCI DSS v4 req. 6.3 (incl. software inventory 6.3.2); CIS Software Supply Chain Security Guide |
| DAST | PW.8 (test executable code) | 8.29 security testing in development and acceptance | DORA Art. 25 (testing incl. vulnerability scans, source code reviews) |
| Gates and criteria | PO.4 (criteria for software security checks) | 8.32 change management | PCI DSS v4 6.2 (bespoke software reviewed before release) |
| Exceptions with expiry | RV.2 (assess, prioritise, remediate; RV.2.2 risk responses) | 8.8; risk treatment per clause 6.1.3 | DORA Art. 9 (protection and prevention) |
| Tamper resistance, SoD, four-eyes | PO.5 (secure environments), PO.2 (roles) | 5.3 segregation of duties, 8.4 access to source code | SLSA build-integrity goals |


PCI DSS and DORA apply only where in scope (cardholder data; EU financial entities). Confirm the
applicable regimes in the intake.
