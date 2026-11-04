# Policy authoring


The canonical file is `.gitlab/security-policies/policy.yml`, on the default branch of a security
policy project. Validate it against `ee/app/validators/json_schemas/security_orchestration_policy.json`
**at your instance's version tag**, for example
`https://gitlab.com/gitlab-org/gitlab/-/raw/v19.4.0-ee/ee/app/...`. The published docs sometimes
contradict the schema. When they do, the schema and the instance's observed behaviour win.


## Contents


1. [Document skeleton](#document-skeleton)
2. [Scan execution policy](#scan-execution-policy)
3. [Approval policy (gate)](#approval-policy-gate)
4. [Vulnerability management policy (auto-dismiss)](#vulnerability-management-policy-auto-dismiss)
5. [Pipeline execution policy and schedule policy](#pipeline-execution-policy-and-schedule-policy)
6. [Scoping](#scoping)
7. [Limits](#limits)
8. [Generator pitfalls](#generator-pitfalls)
9. [Review checklist](#review-checklist)


## Document skeleton


```yaml
scan_execution_policy: []        # scanners run
approval_policy: []              # MR gates; the legacy scan_result_policy key is rejected on current versions
vulnerability_management_policy: []   # auto-dismiss
pipeline_execution_policy: []    # inject/override CI content
pipeline_execution_schedule_policy: []  # scheduled PEP pipelines (e.g. DAST)
```


Emit only the keys you use. An unknown top-level key, or a schema violation anywhere in the
document, makes GitLab ignore **the whole document** without reporting an error. Every policy in
the file stops applying.


## Scan execution policy


```yaml
scan_execution_policy:
 - name: SAST
   description: Centrally enforced SAST. Managed by <tool>; manual edits are overwritten.
   enabled: true
   skip_ci: { allowed: false }          # or true; see design-principles
   no_pipeline: { allowed: false }
   rules:
     - type: pipeline
       branch_type: all
       pipeline_sources: { including: [merge_request_event] }
     - type: pipeline
       branch_type: default
       pipeline_sources: { including: [push] }
   actions:
     - scan: sast
       template: latest                 # default | latest; dependency_scanning also v1/v2
       tags: [<runner-tag>]             # omit only if untagged runners exist
       variables:
         AST_ENABLE_MR_PIPELINES: "true"
         GITLAB_ADVANCED_SAST_ENABLED: "true"
       scan_settings:
         ignore_default_before_after_script: true
   policy_scope:
     projects:
       excluding: []                    # see Scoping: never emit an empty list
```


- **Rule types:**
 - `pipeline`: runs when a pipeline runs;
 - `schedule`: needs `cadence`, plus optional `timezone` and `time_window`. Keep `cadence`
   to plain values: cadences whose minute or hour fields used `,`, `-` or `/` were silently
   skipped (19.2);
 - `agent`: for cluster image scanning.
- **Branch selection:**
 - `branch_type` is one of `all`, `default`, `protected`, `target_default` or
   `target_protected`. For MR rules prefer `all`: `target_default` left MRs into non-default
   branches unscanned in production;
 - `pipeline_sources` must be an object (`{including: [...]}`), never a bare list;
 - `branches` takes explicit names and globs;
 - `branch_exceptions` takes names to skip.
- **Action properties.** These are capped per action:
 - 5 for `sast`, `secret_detection`, `dependency_scanning` and `cluster_image_scanning`;
 - 7 for `dast`, which also requires `site_profile`;
 - other scan types are uncapped in the 19.2 schema, so check the schema at your version.


 `scan`, `tags`, `scan_settings` and `variables` already use 4.
- **Variables.** Policy variables override project and group variables for the injected job. Use
 them for anything projects must not change:
 - resolution images and package indexes;
 - `*_EXCLUDED_PATHS`;
 - analyzer toggles.
- **`template`.** Pin it. For example, `latest` was needed for SAST to support Java 21, and
 dependency scanning `v2` switches to the SBOM-based analyzer with resolution jobs. A template
 change is a behaviour change, so roll it out like one.


### KICS resolver and timeout canary

For the IaC-producing action, evaluate the following variables on an approved
non-production canary after confirming the installed analyzer accepts them.
The memory values illustrate the supplied incident's sizing. Check runner override
permissions and capacity, and review other scanners if they share this action.

```yaml
variables:
  KICS_MAX_RESOLVER_DEPTH: "0"
  KICS_TIMEOUT: "300"
  KUBERNETES_MEMORY_REQUEST: "4Gi"
  KUBERNETES_MEMORY_LIMIT: "8Gi"
```

Record effective resolver depth and query timeout, peak memory and runtime, report
ingestion, and exact rule/file/line differences against the previous configuration.
Reducing reference resolution can affect coverage on other inputs. Preserve the
prior settings for rollback and verify query completion alongside job success.

## Approval policy (gate)


```yaml
approval_policy:
 - name: Block new critical/high SAST findings
   enabled: true
   enforcement_type: enforce            # enforce | warn
   fallback_behavior: { fail: closed }
   rules:
     - type: scan_finding
       branch_type: protected
       scanners: [sast]                 # IaC reports as sast
       severity_levels: [critical, high]
       vulnerability_states: [new_needs_triage]
       vulnerabilities_allowed: 0
   actions:
     - type: require_approval
       approvals_required: 1
       group_approvers: [<path/to/security-reviewers>]   # verify eligible set on a real MR
     - type: send_bot_message
       enabled: true
   approval_settings:
     prevent_approval_by_author: true
     prevent_approval_by_commit_author: true
     remove_approvals_with_new_commit: true
     block_branch_modification: true
     prevent_pushing_and_force_pushing: true
     prevent_editing_approval_rules: true
   policy_scope: { projects: { excluding: [] } }
```


- **Approver fields:**
 - `group_approvers` or `group_approvers_ids`;
 - `user_approvers` or `user_approvers_ids`;
 - `role_approvers`, which takes roles such as `developer` or `maintainer`, or custom role IDs.


 Prefer groups whose membership is managed in the IdP.
- Approval-rule `branch_type` accepts only `default` or `protected`.
- `policy_tuning.unblock_rules_using_execution_policies` is experimental. It unblocks a rule whose
 scan is missing when a scan execution policy enforces that scanner but the scan produced no
 artifact because it does not apply to the project. It weakens fail-closed, so enable it
 deliberately.
- `bypass_settings` covers bypass for access tokens, service accounts, users, groups and roles.
 Every bypass is an audited weakening, so document why it exists.
- Use the same `policy_scope` for the gate as for the scanner. A gate that applies to a project
 outside the scanner's scope reports a missing scan, and with fail-closed it then needs approval
 forever.


## Vulnerability management policy (auto-dismiss)


```yaml
vulnerability_management_policy:
 - name: Dismiss accepted-risk findings in group/app
   enabled: true
   rules:                               # max 5 rules
     - type: detected
       criteria:
         - type: identifier
           values: [CVE-2021-44228]
         - type: file_path              # optional; ANDed with identifier
           values: [package-lock.json]
   actions:
     - type: auto_dismiss
       dismissal_reason: acceptable_risk   # acceptable_risk | false_positive | mitigating_control | used_in_tests | not_applicable
   policy_scope:
     projects: { including: [{ id: 1234 }] }   # never empty
```


Auto-dismiss runs **at default-branch ingestion**:


- it is not retroactive;
- it does not act on MR-introduced findings;
- GitLab never reverts it.


Expiry handling and MR coverage therefore need automation. See
[exception-governance](exception-governance.md).


## Pipeline execution policy and schedule policy


```yaml
pipeline_execution_policy:
 - name: Enforced compliance jobs
   enabled: true
   pipeline_config_strategy: inject_policy   # inject_policy | override_project_ci (inject_ci = legacy)
   content:
     include:
       - project: <policy/project>
         file: ci/compliance.yml
         ref: <pinned tag or SHA>
   skip_ci: { allowed: false }
   variables_override: { allowed: false, exceptions: [] }
   policy_scope: { projects: { excluding: [] } }


pipeline_execution_schedule_policy:       # max 5, one schedule each
 - name: DAST weekly
   enabled: true
   content:
     include:
       - project: <policy/project>
         file: dast/web-weekly.yml
   schedules:
     - type: weekly
       days: [Sunday]
       start_time: "02:00"
       timezone: Europe/Berlin
       time_window: { value: 7200, distribution: random }
   policy_scope: { projects: { including: [{ id: 1234 }] } }
```


- **When to choose a PEP over a SEP:**
 - you need custom jobs, such as third-party scanners or DAST against a deployed target;
 - you need enforcement that `workflow:rules` cannot suppress (`override_project_ci`);
 - you need `variables_override: {allowed: false}` to stop projects redirecting jobs.
- **Users need read access to the PEP CI content project.** Either grant it, or enable the
 policy project's "pipeline execution policies" access setting. Scheduled policies run as the
 Security Policy Bot instead.
- **Prefer the structured schedule form** (`daily`/`weekly`/`monthly`) for PEP schedules.


## Scoping


```yaml
policy_scope:
 projects: { including: [{ id: 1 }], excluding: [{ id: 2 }] }
 groups:   { including: [{ id: 10 }], excluding: [{ id: 11 }] }
 compliance_frameworks: [{ id: 5 }]
```


- **An empty `including` list, or an absent scope, means every project under the linked
 namespace.** Never generate an empty `including` list. Drop the policy instead.
- **IDs must be integers.** If a generator emits `"1234"` (a string), the whole document is
 silently rejected. Terraform does this when it unifies conditional branches into `map(string)`
 or calls `sort()` on numbers.
- **Mandatory scanners: `projects.excluding`.** New projects are covered automatically, and
 exceptions add exclusions.
- **Opt-in scanners: `groups.including`** on the subgroups that opted in. Repositories added later
 are covered without anyone enumerating them.
- **Compliance frameworks** suit cross-cutting scopes, such as "all PCI apps", wherever teams
 label projects reliably.


## Limits


Verify each limit on your version. Newer releases make several of them admin-configurable.


| Item | Default |
|---|---|
| Scan execution policies per policy project | 5 |
| Approval policies per policy project | 5 |
| Pipeline execution policies per policy project | 5 |
| Pipeline execution schedule policies | 5 (schema), one schedule each |
| Vulnerability management policies per policy project | 5 |
| Rules per approval / vulnerability management policy | 5 |
| Properties per scan action | 5 (DAST 7) |
| Security policy projects per group/project link | 1 (linking another replaces it) |


A policy beyond the cap is ignored without an error. Validate counts in the generator so the
deployment fails before GitLab is changed.


## Generator pitfalls


- Use a YAML serializer, not string templates. Watch for:
 - YAML 1.1 booleans (`on`, `off`, `yes` and `no` unquoted);
 - integer IDs turning into strings;
 - `null` values.
- Keep shape-different policies in separate homogeneous collections. Concatenate them; don't pick
 between them with a type-unifying conditional.
- Put a "managed by" notice in `description`.
- `newly_detected` was removed in 17.0; one occurrence invalidates the **whole** document. Use
 `new_needs_triage` and `new_dismissed`.
- A gate whose scanners use different project scopes cannot have one correct `policy_scope`;
 split it.
- Write `policy.yml` before you link it, or GitLab briefly applies an empty configuration.
- After a commit, propagation can take up to ~10 min on some versions. Run `resyncSecurityPolicies`
 when timing matters, then verify.


## Review checklist


- [ ] Validates against the schema at the running version tag.
- [ ] No empty `including` lists. All IDs are integers.
- [ ] Every scan action has the required `tags`, `ignore_default_before_after_script: true` and a
     pinned `template`.
- [ ] MR and default-branch rules are both present. `AST_ENABLE_MR_PIPELINES` is set.
- [ ] Gates use `fail: closed`, an accountable approver set and all bypass protections.
- [ ] Gate scope equals scanner scope.
- [ ] Counts are within the limits.
- [ ] Rollout and rollback revisions are identified. A non-prod verification is recorded.
