# Exception not applied, or not removed


1. **Is it valid?** It must have passed validation in the source, and it must not be expired. The
  project must resolve.
2. **Was it rendered?** Check the per-project override policy or the group policy document for
  the identifier, paths and scope ID (an integer).
3. **Is it loaded?** Query `vulnerabilityManagementPolicies` (or the scan policies, for scanner
  exceptions) on the project.
4. **Is it linked?** New dismissal policies are not linked to existing projects. Run the
  `INHERITED` resync on the project, then `DIRECT` if it has its own policy project (**WRITE**).
5. **When does it act?** Auto-dismiss happens at the next **default-branch** ingestion. For MRs,
  the exceptions automation must act, or the MR must be approved.
6. **Does it match?**
  - Is the identifier exact, as shown under *Identifiers*?
  - Are the `file_path` patterns repository-relative, with `*` vs `**/` correct?
  - Remember the criteria are ANDed.
7. **Removal.**
  - GitLab never reverts auto-dismissals. The automation must re-open them.
  - Run a `DIRECT` resync so the removal takes effect.
  - A remaining whole-scanner exception still wins over a path exception.
