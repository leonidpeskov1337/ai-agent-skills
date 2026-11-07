# Independent skill releases

Releases use explicit SemVer tags such as `kubernetes-troubleshooter/v1.2.0` and
`gitlab-security-policies/v1.1.0`. Skill versions are independent; no initial
version or public release is invented by this implementation.

Release Please's manifest mode supports independent components, but introduces
release PR state, manifests and bot write access. Changesets primarily serves
package workspaces; semantic-release needs additional monorepo coordination.
For two non-package skill directories, reviewed manual tags plus GitHub CLI's
generated release notes and asset publishing are the smallest suitable existing
release tools. There is no custom version calculator. Revisit Release Please if
release frequency warrants automatic version PRs.

## One-time administrator setup

1. Review `.github/workflows/release.yml` and activate the approved trunk ruleset.
2. Create the `release` environment, restrict deployment branches to the default
   branch, and require maintainer approval. Permit self-approval only when a solo
   maintainer otherwise could not publish. Environment approval is separate from PR review.
3. Restrict tag creation/update/deletion for `*/v*` to designated maintainers using
   a tag ruleset. The branch workflow also verifies the chosen tag at the default
   branch tip, but this does not substitute for tag protection.
4. Set repository variable `RELEASE_ENABLED=true` only after approving the setup.

Nothing here creates the environment, enables that variable or publishes a release.

## Publish one skill

1. Merge the reviewed change into trunk after **Validation gate** passes.
2. Pick the skill's next version using Conventional Commits and compatibility impact.
3. Create and push an annotated tag at the current default-branch tip:

   ```sh
   git tag -a kubernetes-troubleshooter/v1.2.0 -m 'Kubernetes troubleshooter 1.2.0'
   git push origin kubernetes-troubleshooter/v1.2.0
   ```

4. Dispatch **Release skill** on the default branch with the exact existing tag.
   Non-default refs and disabled setup cannot publish. Pre-release tags and leading
   zeroes are currently rejected; add them deliberately if needed.
5. Validation checks tag identity, skill structure, relevant tests, source secrets,
   independent packaging, ZIP contents and SHA-256. Approve the `release` environment
   after inspecting those results.
6. The write-token job downloads only that run's validated artifact, checks its
   checksum and confirms trunk has not advanced. It executes no repository scripts.
   GitHub CLI generates release notes and attaches the `.skill` and checksum.
7. Download the release assets and verify `sha256sum --check *.sha256`. Review the
   generated notes, particularly the previous tag used for independent components.

If trunk advanced while approval was pending, validation must be repeated against
a newly reviewed release target. Do not move a published tag. A duplicate release
fails instead of replacing public assets. This workflow does not deploy infrastructure.
