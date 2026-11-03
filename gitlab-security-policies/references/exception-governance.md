# Exception governance


An exception is a **time-bound, owned risk acceptance**. The point of the process is to keep
every exception:


- **narrow**: it covers only what was approved;
- **traceable**: it has a ticket, an owner and an approver;
- **self-expiring**: it ends without anyone remembering to remove it.


These rules hold whatever tooling stores and applies the exceptions.


## Contents


1. [Kinds, narrowest first](#kinds-narrowest-first)
2. [Record schema](#record-schema)
3. [Identifier rules](#identifier-rules)
4. [Path rules](#path-rules)
5. [How each kind is applied in GitLab](#how-each-kind-is-applied-in-gitlab)
6. [Expiry and revocation](#expiry-and-revocation)
7. [Review checklist](#review-checklist)
8. [Anti-patterns](#anti-patterns)


## Kinds, narrowest first


| Kind | Effect | Use for |
|---|---|---|
| **Finding** (`vulnerabilities`) | The scan still runs; the named findings are auto-dismissed | False positives, accepted risk, mitigating controls |
| **Finding + paths** | As above, only within the listed paths | Rule-title, CWE or wildcard identifiers; test fixtures |
| **Scanner + paths** | The scanner runs but skips the paths | Vendored or generated content with unfixable findings |
| **Scanner** | The scanner does not run for the project | The repository structurally cannot produce the report (no image, no manifest) |


Choose the first kind that works. A scanner exception removes the project's coverage for every
future finding too, so it needs the strongest justification.


## Record schema


The schema is tool-neutral. Store records as YAML or JSON in a reviewed repository.


```yaml
- name: log4shell-accepted-risk         # unique, kebab-case
 project: group/subgroup/app           # full path; resolves to exactly one project
 vulnerabilities: [CVE-2021-44228]     # XOR scanners
 # scanners: [container_scanning]
 paths: []                             # optional narrowing, repository-relative
 dismissal_reason: acceptable_risk     # finding kinds only
 notes: Mitigated by WAF rule 1234; upgrade tracked in ticket.
 ticket: SEC-1234
 owner: team-payments                  # accountable for remediation
 approved_by: appsec                   # risk owner; not the requester
 expiration_date: "2026-11-30"         # ISO date, <= max_exception_days from approval
```


Validate before anything reaches GitLab, and fail the change when a check fails:


- Every required field is non-empty, and names are unique.
- Exactly one of `vulnerabilities` and `scanners` is set.
- `dismissal_reason` is one of `acceptable_risk`, `false_positive`, `mitigating_control`,
 `used_in_tests` or `not_applicable`.
- `expiration_date` is no further away than the organisation's maximum, for example 90 or 180
 days. A new or changed entry must expire in the future.
- Checks against live state (project resolves, scanner applies) run on **active** entries only.
 An expired entry is inactive and must never block an unrelated deployment, for example after
 its project is archived or deleted.
- Every scanner name is known. Scanners without a path concept (container scanning, DAST) reject
 `paths`.
- The project resolves, and it belongs to the business unit that owns the file.
- **Unknown keys are rejected.** Otherwise a misspelt `paths` silently widens the entry to the
 whole project.


## Identifier rules


Copy the identifier **exactly** as it appears under *Identifiers* on the vulnerability page.


| Finding source | Identifier form | Project-wide allowed? |
|---|---|---|
| Dependency/container advisories | `CVE-YYYY-NNNN`, `GHSA-xxxx-xxxx-xxxx`, `GMS-…`, `Gemnasium-<uuid>` | Yes, exact IDs only |
| CVE wildcards | `CVE-2023-*`, `CVE-2023-45*` (full year required) | **No**, `paths` required |
| GHSA/GMS/Gemnasium wildcards | Never: these IDs are random, so a prefix means nothing | Rejected |
| KICS (IaC) | Rule title, e.g. `Missing User Instruction` | **No**, `paths` required |
| Secret detection | `Gitleaks rule ID <rule>` (not the display title) | **No**, `paths` required |
| Semgrep SAST | `SAST Rules ID - <rule>` | **No**, `paths` required |
| CWE / OWASP | `CWE-79`, `A03:2021` | **No**, `paths` required |


A rule title, CWE or OWASP category names a **class** of flaw, not one flaw. If it applies
project-wide, it dismisses every future instance of that class. Reject bare `*` and leading
wildcards.


## Path rules


- Paths are repository-relative. Reject absolute paths, `..`, commas, and bare `*` or `**`.
- Match each path as a file *and* as a directory: `docs` covers `docs` and `docs/**/*`.
- Glob semantics follow `File.fnmatch` with `FNM_PATHNAME`: `*` stays within one directory and
 `**/` spans directories.
- For dependency findings, scope the exception to the manifest or lockfile that reports them,
 for example `package-lock.json` or `app/build.gradle.kts`.


## How each kind is applied in GitLab


| Kind | Mechanism |
|---|---|
| Finding | A `vulnerability_management_policy` with an `identifier` criterion (plus `file_path`) and `auto_dismiss` with the reason, scoped to the project by integer ID |
| Scanner | Add the project to `policy_scope.projects.excluding` of that scanner's scan execution policy. Exclude it from the gate **only** if no other scanner feeds that gate, because fail-closed gates otherwise demand approval forever |
| Scanner + paths | GitLab presets `*_EXCLUDED_PATHS` (`SAST_EXCLUDED_PATHS`, `SECRET_DETECTION_EXCLUDED_PATHS`, `DS_EXCLUDED_PATHS`) and only a policy can override them. Use a per-project override policy project with a copy of the scanner policy, setting the variable to the default list plus the exception paths. Exclude the project from the group policy for that scanner only. Never exclude it from the gates |


**Capacity.** A policy project holds at most 5 vulnerability management policies and 5 scan
execution policies, and a policy holds at most 5 rules. With a dedicated override policy project
per project, one project can use every dismissal reason. Group-level dismissal policies run out
quickly.


**Propagation.** After creating or changing dismissal policies:


1. Resync the group.
2. Resync each affected project with `INHERITED`.
3. Resync each affected project with `DIRECT` if it has its own policy project.


Then verify. See [gitlab-behaviour](gitlab-behaviour.md#policy-loading-and-propagation).


**Merge requests.** Auto-dismiss acts only at default-branch ingestion. For approved exceptions
to clear MR gates, you need automation that:


- reads a published exception manifest;
- dismisses the covered findings in MR pipelines, with an audit note;
- never bypasses a policy itself.


**Order of operations.**


- On add: create the override project and its link **before** excluding the project from the
 group policy, so coverage never drops.
- On removal: reverse the order.


## Expiry and revocation


- Expired entries stop taking effect at the next deployment, and a scheduled job runs that
 deployment and removes them. Expiry should not wait for the next manual change.
- Structural scanner exceptions ("no image", "Terraform module only") still expire. Give them a
 renewal process, or replace them with automatic detection, so renewal does not become a
 rubber stamp.
- GitLab never reverts an auto-dismissal. Automation must re-open the findings dismissed under an
 expired or removed exception, at end of day UTC on the expiry date. It should only touch
 dismissals made by the policy or the bot, never human decisions.
- When a project's last exception expires, delete its override policy project, so the group
 policy applies again.
- Publish active exceptions, including expired ones, with the effective mode as a machine-readable
 manifest. That lets you tell "no exceptions" apart from "not deployed".


## Review checklist


- [ ] The requester is not the approver. The approver is the risk owner for that system.
- [ ] The narrowest kind is used. A scanner exception is justified structurally ("no image"), not
     by convenience ("too noisy").
- [ ] Identifiers are copied exactly. Non-advisory identifiers and wildcards have `paths`.
- [ ] The expiry is within the maximum. A remediation ticket exists for accepted risk.
- [ ] For SAST/IaC scanner exceptions, both are listed, because they share a gate.
- [ ] Compensating controls are named for `mitigating_control`.
- [ ] Production-exposed, internet-facing or regulated systems carry the stricter approval the
     organisation requires.


## Anti-patterns


- Lowering a business unit's mode to relieve one project.
- Dismissing findings by hand at scale. That has no expiry or ticket, and the audit trail is
 scattered.
- Wildcards on random advisory IDs, or rule titles applied project-wide.
- Exempting a project from gates "temporarily" without an expiry.
- Editing generated policy files by hand. The next deployment overwrites them, and nothing is
 reviewed.
