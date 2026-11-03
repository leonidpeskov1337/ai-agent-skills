# Gate behaviour


1. **Which policy?** Read the MR's approval rules and the `SECURITY_POLICIES_VIOLATIONS` status.
  Note the policy name.
2. **Blocks with "scans missing"** → no report was produced for that scanner. Either the job
  failed or was skipped, or the project is excluded from the scanner but not from the gate.
  Fail-closed requires approval. Fix the job, or align the scopes.
3. **Blocks on a dismissed finding** → check the gate's `vulnerability_states`. The MR may have
  snapshotted its rules before the exception, so approve, re-evaluate
  (`mergeRequestResyncSecurityPolicies`, an experiment) or recreate the MR.
4. **Does not block** → check:
  - the mode (`scan` means no gates);
  - `enforcement_type`;
  - the severity filter;
  - the `vulnerabilities_allowed` count;
  - whether the finding is "new" relative to the target;
  - `branch_type` (only protected targets).
5. **Wrong approvers** → list who is eligible. Verify `group_approvers` on a real MR (membership semantics
  differed from the docs in one test). `role_approvers` are broad, and with SSO provisioning
  everyone as Developer, `[maintainer]` leaves nobody eligible. Compare with the organisation's approver model.
6. **`warn` blocking** → that is by design. The author bypasses with a reason, or a reviewer
  approves.
