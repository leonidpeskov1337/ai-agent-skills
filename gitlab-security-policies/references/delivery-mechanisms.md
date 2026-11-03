# Delivery mechanisms


GitLab sees only two things:


1. **policy documents**: `.gitlab/security-policies/policy.yml` on the default branch of a policy
  project;
2. **links** between a namespace (group or project) and that policy project.


Every mechanism is a different way to produce those two things. Whatever you use, keep the
following invariant.


> One reviewed source of truth → rendered document → schema validation → non-prod apply →
> GitLab verification → production apply → GitLab verification.


## Contents


1. [Choosing a mechanism](#choosing-a-mechanism)
2. [Terraform / OpenTofu](#terraform--opentofu)
3. [API scripts (REST + GraphQL)](#api-scripts-rest--graphql)
4. [Policy-as-code repository with CI](#policy-as-code-repository-with-ci)
5. [UI policy editor](#ui-policy-editor)
6. [Drift and ownership](#drift-and-ownership)


## Choosing a mechanism


| Mechanism | Strengths | Weaknesses | Fit |
|---|---|---|---|
| Terraform/OpenTofu | Plan/diff review, inventory-driven, links and docs in one state | Provider gaps (resync, some settings), and type coercion traps | Estates already provisioning GitLab as code |
| API scripts | Full API coverage, including resync and verification | You build idempotency, diff and validation yourself | Small estates, glue and verification steps |
| Policy repo + CI | Plain YAML MRs, CODEOWNERS on policy files | Linking still needs API or IaC, and cross-file validation is DIY | AppSec-owned policies in an otherwise manual estate |
| UI editor | Fast, schema-aware form | No review of the rendered YAML diff unless you use MR mode, and it drifts from code | Experiments on a sandbox only |


## Terraform / OpenTofu


The GitLab provider (`gitlabhq/gitlab`) offers:


- `gitlab_repository_file`, which writes `policy.yml`;
- `gitlab_group_security_policy_attachment` and `gitlab_project_security_policy_attachment`,
 which create the links;
- `gitlab_project`, which creates the policy project itself.


Check the current provider docs for your provider version. Resource names and arguments change.


Practices:


- Build the document as a native object, and `yamlencode` it once.
- **Never put differently shaped objects in one conditional.** Terraform unifies types and turns
 integers into strings, and GitLab then silently rejects the document. Use homogeneous maps and
 join them with `concat`.
- `sort()` converts numbers to strings. Sort the string forms, then `tonumber`.
- `for_each` keys must be known at plan time. Derive them from config, not from IDs computed at
 apply time.
- Fail the plan for these:
 - more than 5 policies per type;
 - more than 5 rules per policy;
 - empty `including` lists;
 - untagged actions when runners need tags;
 - invalid exceptions.


 Use `check`, `precondition` or variable `validation`.
- There is no resource for `resyncSecurityPolicies`. Run the GraphQL mutation from a
 `terraform_data` provisioner whose trigger is the content hash. Pass the token through the
 provisioner `environment` (marked `sensitive`). Never put it in the command string, because it
 would end up in state and logs.
- Order matters. Link override projects before you exclude projects from the group policy.


## API scripts (REST + GraphQL)


Key calls (details in [runbooks](runbooks.md)):


- Commit `policy.yml`: `POST /projects/:id/repository/commits` with an `update` or `create`
 action, on the default branch, or through an MR.
- Link: the GraphQL mutation `securityPolicyProjectAssign(input: {fullPath, securityPolicyProjectId})`.
 Unlink with `securityPolicyProjectUnassign`.
- Create a policy project: `securityPolicyProjectCreate(input: {fullPath})`, or create a normal
 project and assign it.
- Resync: `resyncSecurityPolicies(input: {fullPath, relationship})`.
- Verify: query the namespace's `scanExecutionPolicies`, `approvalPolicies`,
 `pipelineExecutionPolicies` and `vulnerabilityManagementPolicies`.


Make scripts idempotent: read, diff, then write only on change. Run `--dry-run` by default, and
log the diff.


## Policy-as-code repository with CI


- Keep policy sources in a repository protected by CODEOWNERS (AppSec plus platform).
- A CI pipeline then:
 1. renders the document;
 2. validates it against the schema at the instance's version;
 3. lints it with `scripts/lint_policy.py`;
 4. on merge, commits to the policy project using a narrowly scoped token, such as a project
    access token on the policy project only;
 5. resyncs and verifies.
- Linking is a one-off per namespace. Script it and record it. Do not click it in the UI.


## UI policy editor


- Use it on a sandbox to discover the YAML GitLab expects, then copy the result into the real
 source.
- If production is UI-managed, use **"Configure with a merge request"** so changes get reviewed.
 Export `policy.yml` regularly to detect drift.


## Drift and ownership


- Compare the rendered source against the policy project's default-branch `policy.yml`, and
 against what GraphQL reports as loaded. These are three distinct states, and any of them can
 differ.
- When drift is found, treat the source as authoritative. First find out who changed the policy
 project and why, from its commit history and audit events.
- Restrict write access to policy projects. Developer access to a policy project is effectively
 the power to disable security scanning for every linked namespace.
