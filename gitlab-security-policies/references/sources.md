# Sources and provenance


## Provenance

The KICS additions on 2026-11-05 use the supplied incident report for GitLab EE
19.4, analyzer `kics` 6.13.0 and KICS 2.1.20. The reporter describes native
reproduction and a confirming non-production run. Repository maintenance did not
rerun those scans or independently verify their findings and memory measurements.
The report describes generated CI YAML referencing an 844 KB `pnpm-lock.yaml`
36 times, plus package files, after earlier-stage artifacts were downloaded.

The [KICS CLI reference](https://docs.kics.io/latest/commands/) documents resolver
depth 15 and per-query timeout 60 seconds as defaults. The supplied analyzer's
`KICS_MAX_RESOLVER_DEPTH`/`KICS_TIMEOUT` mappings and its node-level memory output
remain version-specific observations to verify on the installed image. Current
KICS documentation describes `.gitignore` exclusions, while the supplied incident
reports that those entries failed to resolve the memory problem in its input set.


The supplied material attributes behaviour marked *measured* to centrally enforced policies on
GitLab EE 19.2–19.4 self-managed. The estate had about 3,000 projects across several business
units, under Terraform-managed delivery. Organisation-specific names have been removed.


What a measured fact shows:


- what happened on those versions;
- that a pattern is plausible on yours.


It does not prove the same behaviour on your version. Re-verify before relying on it, especially
across minor upgrades.


## Primary GitLab sources


Prefer them in this order: the schema and source at your version tag, then the versioned docs,
then the latest docs.


- Policy JSON schema:
 `https://gitlab.com/gitlab-org/gitlab/-/raw/<vX.Y.Z-ee>/ee/app/validators/json_schemas/security_orchestration_policy.json`
- GraphQL types and mutations:
 - `ee/app/graphql/types/security_orchestration/`;
 - `ee/app/graphql/mutations/security_policy/`, which holds `SecurityPolicyProjectAssign`,
   `SecurityPolicyProjectUnassign`, `SecurityPolicyProjectCreate` and `ResyncSecurityPolicies`;
 - `ee/app/graphql/mutations/merge_requests/resync_security_policies.rb`
   (`MergeRequestResyncSecurityPolicies`).
- Policy limits: `Security::OrchestrationPolicyConfiguration#policy_limit_by_type` in
 `ee/app/models/security/orchestration_policy_configuration.rb`.
- Docs (append `/` plus the version, or use the docs version switcher):
 - Policies overview: https://docs.gitlab.com/user/application_security/policies/
 - Scan execution policies: https://docs.gitlab.com/user/application_security/policies/scan_execution_policies/
 - Merge request approval policies: https://docs.gitlab.com/user/application_security/policies/merge_request_approval_policies/
 - Pipeline execution policies: https://docs.gitlab.com/user/application_security/policies/pipeline_execution_policies/
 - Scheduled pipeline execution policies: https://docs.gitlab.com/user/application_security/policies/scheduled_pipeline_execution_policies/
 - Vulnerability management policies: https://docs.gitlab.com/user/application_security/policies/vulnerability_management_policy/
 - Security policy projects: https://docs.gitlab.com/user/application_security/policies/enforcement/security_policy_projects/
 - Dependency scanning (SBOM-based / v2): https://docs.gitlab.com/user/application_security/dependency_scanning/
 - Plan limits (artifact size by type): https://docs.gitlab.com/administration/instance_limits/
 - GraphQL reference: https://docs.gitlab.com/api/graphql/reference/
- Terraform provider: https://registry.terraform.io/providers/gitlabhq/gitlab/latest/docs. The
 relevant resources are `gitlab_group_security_policy_attachment` and
 `gitlab_project_security_policy_attachment`.


## Standards


Cite at the requirement level, and check that the edition you cite is the one in force.


- **NIST SP 800-218 v1.1 (SSDF).** The practice titles were verified against the NIST PDF:
 - PO.3 Implement Supporting Toolchains;
 - PO.4 Define and Use Criteria for Software Security Checks;
 - PW.4 Reuse Existing, Well-Secured Software;
 - PW.7 Review and/or Analyze Human-Readable Code;
 - PW.8 Test Executable Code;
 - RV.1 Identify and Confirm Vulnerabilities on an Ongoing Basis;
 - RV.2 Assess, Prioritize, and Remediate Vulnerabilities.


 Source: https://doi.org/10.6028/NIST.SP.800-218
- **ISO/IEC 27001:2022 Annex A** controls:
 - 5.3 segregation of duties;
 - 8.4 access to source code;
 - 8.8 management of technical vulnerabilities;
 - 8.25 secure development life cycle;
 - 8.28 secure coding;
 - 8.29 security testing in development and acceptance;
 - 8.32 change management.
- **PCI DSS v4.0.1** Requirement 6, "Develop and maintain secure systems and software". The
 relevant parts are 6.2 (bespoke and custom software) and 6.3 (security vulnerabilities
 identified and addressed, including the software component inventory). Confirm sub-requirement
 numbers in the PCI SSC document library.
- **EU DORA, Regulation (EU) 2022/2554**:
 - Art. 8 identification;
 - Art. 9 protection and prevention;
 - Art. 25 testing of ICT tools and systems, which lists vulnerability assessments and scans,
   open-source analyses and source code reviews.
- **OWASP SAMM v2**: Verification (Security Testing), Implementation (Defect Management) and
 Governance (Policy & Compliance).
- **CIS Software Supply Chain Security Guide** and **SLSA**: integrity of build tooling and
 dependencies. These are relevant to pinning scanner and resolution images.


## Search terms for upstream issues


Search `gitlab-org/gitlab` issues for the following phrases:


- "policy.yml invalid silently ignored";
- "resyncSecurityPolicies";
- "scan execution policy workflow rules";
- "dependency resolution gradle toolchain";
- "CycloneDX 413";
- "auto_dismiss existing projects".
