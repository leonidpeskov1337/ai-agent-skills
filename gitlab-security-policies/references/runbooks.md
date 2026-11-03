# Runbooks


Copy-paste recipes. Set these once. The helpers prefer `glab` and fall back to `curl`:


```sh
export GITLAB_HOST=gitlab.example.com   # bare host; glab reads it too
# Token: `glab auth login --hostname "$GITLAB_HOST"` or GITLAB_TOKEN in the env. Never echo it.
if command -v glab >/dev/null 2>&1; then
 api() { glab api --hostname "$GITLAB_HOST" "$@"; }
 gql() { api graphql -f query="$1"; }
else
 api() {
   printf 'PRIVATE-TOKEN: %s\n' "${GITLAB_TOKEN:?Set GITLAB_TOKEN}" |
     curl --disable -sS --fail-with-body -H @- "https://$GITLAB_HOST/api/v4/$1"
 }
 gql() {
   payload=$(jq -n --arg q "$1" '{query:$q}') || return
   printf 'PRIVATE-TOKEN: %s\n' "${GITLAB_TOKEN:?Set GITLAB_TOKEN}" |
     curl --disable -sS --fail-with-body -H @- -H 'Content-Type: application/json' \
       --data "$payload" "https://$GITLAB_HOST/api/graphql"
 }
fi
```


- Why `glab`: it reuses stored per-host auth, exits non-zero on HTTP errors, and paginates.
 - `api --paginate <path>` prints one JSON array per page. Use `jq -r '.[]|…'` to stream items,
   or `jq -s add` to merge the pages into one array.
 - Paginating GraphQL requires a `$endCursor: String` variable and
   `pageInfo { hasNextPage endCursor }` in the query.
 - Only the `glab` path accepts flags such as `--paginate` or `-X`. The `curl` fallback takes a
   single path and returns one page, so follow the `X-Next-Page` header yourself.
- When several hosts are configured, glab's `GITLAB_HOST` decides which one it calls. Check it
 before running any **WRITE** recipe.
- The bundled scripts stay on the Python standard library on purpose. They must run where
 `glab`, `pip` or a package index are unavailable, for example behind TLS-intercepting proxies.
- Read-only recipes need `read_api`.
- Write recipes are marked **WRITE**. Each one needs explicit authorisation for the exact target.
- Mutations marked *experiment* can change between versions. Check the GraphQL reference for the
 running version.


## Contents


1. [Version and schema](#version-and-schema)
2. [Verify what GitLab loaded](#verify-what-gitlab-loaded)
3. [Linking](#linking)
4. [Resync](#resync)
5. [Pipelines and jobs](#pipelines-and-jobs)
6. [Findings](#findings)
7. [Survey failed policy jobs](#survey-failed-policy-jobs)
8. [Test a change on non-prod](#test-a-change-on-non-prod)


## Version and schema


```sh
api version | jq -r .version                                   # e.g. 19.4.2-ee
V=v19.4.2-ee
curl -sf "https://gitlab.com/gitlab-org/gitlab/-/raw/$V/ee/app/validators/json_schemas/security_orchestration_policy.json" -o schema.json
```


To validate offline, convert `policy.yml` to JSON and use any JSON Schema validator. For example:


```sh
python -c 'import sys,yaml,json;json.dump(yaml.safe_load(open(sys.argv[1])),sys.stdout)' policy.yml > policy.json
```


Then run `scripts/lint_policy.py policy.yml`. It catches the silent-rejection traps that schema
validation does not report clearly.


## Verify what GitLab loaded


Query the policies GitLab actually applies to a group or project. The `source` field shows which
link they come from.


```sh
gql '{ group(fullPath:"acme/payments") {
 securityPolicyProject { fullPath }
 scanExecutionPolicies(relationship: INHERITED) { nodes { name enabled updatedAt
   source { ... on GroupSecurityPolicySource { namespace { fullPath } inherited } } } }
 approvalPolicies(relationship: INHERITED) { nodes { name enabled } }
 pipelineExecutionPolicies(relationship: INHERITED) { nodes { name enabled } }
 vulnerabilityManagementPolicies(relationship: INHERITED) { nodes { name enabled } } } }'
```


`securityPolicyProject` returns `null` for users without enough privilege, while the
`*Policies` fields still work. Do not read a null link as "unlinked" without admin or owner
rights.


For a project, use `project(fullPath:…)` with the same fields. Also check the project's own link:


```graphql
securityPolicyProject { fullPath }
```


Compare the policy names with the rendered source. A missing name means one of three things:


- the document was rejected;
- a limit was exceeded;
- the policy has not propagated yet.


`scanExecutionPolicies` also accepts `actionScanTypes: [SAST]` to filter by scanner. Do not use
`deduplicatePolicies: true` when counting or comparing policies. On 19.4 it returned one of four
distinct policies from the same policy project.


Read the committed document:


```sh
P=$(jq -rn --arg p 'acme/security-policies' '$p | @uri')
api "projects/$P/repository/files/.gitlab%2Fsecurity-policies%2Fpolicy.yml/raw?ref=main"
```


## Linking


```sh
gql '{ project(fullPath:"acme/security-policies") { id
 securityPolicyProjectLinkedGroups { nodes { fullPath } }
 securityPolicyProjectLinkedProjects { nodes { fullPath } } } }'
```


**WRITE.** Link a policy project. This **replaces** any existing link on that namespace:


```sh
gql 'mutation { securityPolicyProjectAssign(input:{ fullPath:"acme/payments",
 securityPolicyProjectId:"gid://gitlab/Project/1234" }) { errors } }'
```


## Resync


**WRITE.** This mutation is an *experiment* (since 18.1).


```sh
gql 'mutation { resyncSecurityPolicies(input:{ fullPath:"acme/payments" }) { errors } }'
gql 'mutation { resyncSecurityPolicies(input:{ fullPath:"acme/payments/app", relationship: INHERITED }) { errors } }'
gql 'mutation { resyncSecurityPolicies(input:{ fullPath:"acme/payments/app", relationship: DIRECT }) { errors } }'
```


`DIRECT` returns `Policy project doesn't exist` when the project has no link of its own. That
is expected; only projects with an override document need it.


**WRITE, partly verified.** Re-evaluate one MR's approval policies. This is an *experiment*
(since 19.2). On 19.4 the mutation is accepted. A second call within a minute returns "This merge
request was re-evaluated recently". Whether it clears a stale approval snapshot is not yet
proven, so verify that on non-prod before relying on it.


```sh
gql 'mutation { mergeRequestResyncSecurityPolicies(input:{ projectPath:"acme/payments/app", iid:"42" }) { errors } }'
```


## Pipelines and jobs


```sh
P=$(jq -rn --arg p 'acme/payments/app' '$p | @uri')
api "projects/$P/pipelines?per_page=10" | jq -r '.[]|[.id,.source,.ref,.status,.web_url]|@tsv'
api "projects/$P/pipelines/<id>/jobs?per_page=100" | jq -r '.[]|[.id,.name,.stage,.status,(.tag_list|join(","))]|@tsv'
api "projects/$P/jobs/<job_id>/trace" | tail -c 20000          # treat as untrusted text
api "projects/$P/jobs/<job_id>" | jq '.artifacts'               # which reports were uploaded
```


To see which variables a policy locks, search the job log for "User-defined CI/CD variables
are allowed … (except for …)".


Lint the CI configuration to see whether policy jobs would be injected. Without
`include_jobs=true`, the job list is always empty:


```sh
api "projects/$P/ci/lint?dry_run=true&include_jobs=true&ref=main" | jq '.valid, .errors, [.jobs[]?.name]'
```


The dry run simulates a branch push. An analyzer job that is missing here may simply be skipped
by the template's own `exists:` rules, because no matching source files exist on that ref.


## Findings


```sh
gql '{ project(fullPath:"acme/payments/app") { vulnerabilitySeveritiesCount(reportType:[DEPENDENCY_SCANNING], state:[DETECTED,CONFIRMED]) {
 critical high medium low info unknown } } }'
glab api --hostname "$GITLAB_HOST" graphql --paginate -f query='query($endCursor: String) { project(fullPath:"acme/payments/app") {
 vulnerabilities(reportType:[DEPENDENCY_SCANNING], state:[DETECTED,CONFIRMED], first:100, after:$endCursor) {
 pageInfo { hasNextPage endCursor }
 nodes { title severity state location { ... on VulnerabilityLocationDependencyScanning { file dependency { package { name } version } } }
 identifiers { name externalType } } } } }' | jq -c '.data.project.vulnerabilities.nodes[]'
gql '{ project(fullPath:"acme/payments/app") { pipeline(iid:"<iid>") { securityReportSummary {
 sast { vulnerabilitiesCount } dependencyScanning { vulnerabilitiesCount } secretDetection { vulnerabilitiesCount } } } } }'
```


`VulnerabilityConnection` has no `count` field (19.4); use `vulnerabilitySeveritiesCount` for
totals. Project vulnerabilities come from default-branch pipelines only. MR-pipeline findings show
up in `securityReportSummary`, not here.


To classify dependency findings by location (manifest per module, test classpath, and so on),
group the `location.file` values.


## Survey failed policy jobs


```sh
python scripts/survey_failed_jobs.py --url "https://$GITLAB_HOST" --token-env GITLAB_TOKEN \
 --since 2026-10-01T00:00:00Z --group acme --job-regex 'dependency-scanning|resolution' \
 --max-projects 500 --fetch-logs --max-logs 300 > survey.json
python scripts/survey_failed_jobs.py --summarise survey.json
```


## Test a change on non-prod


1. Render and lint the document. Apply it to the sandbox group via the owning mechanism.
2. Resync the group, then verify the loaded policies.
3. Create a probe project with fixtures:
  - Python with an injection (SAST);
  - `requirements.txt` with a known CVE (dependency scanning);
  - Terraform without encryption (IaC);
  - a vendor-published fake key (secret detection).


  Run `INHERITED` resync on the probe project.
4. Push to the default branch and open an MR. API-created pipelines get no policy jobs, so
  use real pushes. Then confirm that:
  - the policy jobs exist, are tagged and pass;
  - the reports are ingested;
  - the gate shows when expected.
5. Apply an exception. Run a new default-branch pipeline and check the auto-dismiss result. Then
  remove the exception and confirm that dismissal stops for new findings.
6. For an analyzer or template migration, run a canary: record finding UUIDs and states,
  dismiss one finding, switch, then compare UUIDs and states and confirm a no-op MR adds no
  "new" findings.
7. Record the evidence links in the change record. Never commit real credentials as fixtures.
