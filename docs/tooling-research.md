# Tooling research and pins

Research date: 2026-11-07. Upstream repository metadata, current source, release tags
and licenses were inspected before adoption. Repositories below were not archived
and showed activity during 2026; that is evidence of maintenance, not a security
guarantee. Recheck release notes and advisories on each update.

## Reused tools

| Tool | Version / source | License and decision |
| --- | --- | --- |
| Anthropic Skill Creator validator | `2c5958ecac7cee2b583967a2c4981d0f4a75c579` | Skill Creator's bundled Apache-2.0 license retained; exact validator bytes and digests vendored |
| checkout | v7.0.1, SHA in workflow | Official GitHub action, MIT; credentials disabled, hosted Ubuntu runtime |
| setup-python | v7.1.0, SHA in workflow | Official GitHub action, MIT; Python 3.14 matches local validation |
| setup-node | v7.1.0, SHA in workflow | Official GitHub action, MIT; Node 24 satisfies commitlint/markdownlint runtime constraints |
| upload-artifact | v7.0.2, SHA in workflow | Official GitHub action, MIT; artifacts only, bounded retention |
| commitlint / config-conventional | 21.2.4 | MIT; official parser, optional scopes/breaking changes/generated commit ignores |
| Ruff | 0.17.4 | MIT; Python lint plus shared-tool formatting |
| pytest | 9.2.0 | MIT; collects existing unittest tests as well as repository fixtures |
| PyYAML | 6.0.3 | MIT; safe YAML loader for frontmatter and configuration |
| jsonschema | 4.26.0 | MIT; Draft 2020-12 evaluation schemas |
| markdown-it-py | 4.0.0 | MIT; CommonMark relative-link extraction avoids custom Markdown parsing |
| yamllint | 1.38.0 | GPL-3.0-or-later; development CLI, not linked into distributed skills |
| markdownlint-cli2 | 0.24.0 | MIT; selected structural rules, no spelling/grammar checks |
| actionlint | 1.7.12 | MIT; official release binaries with pinned archive SHA-256 |
| zizmor | 1.32.0 | MIT; project moved from `woodruffw` to `zizmorcore`, installed from hash-locked PyPI package |
| Gitleaks | 8.30.1 | MIT; upstream CLI avoids extra action licensing/token requirements; redacted output |
| pip-audit | 2.10.1 | Apache-2.0; audits the development dependency lock |
| Claude Code | 2.1.319 | Anthropic commercial terms, optional manual evaluation runtime in its own integrity lock |

Python transitive versions and hashes are in `requirements-ci.txt`; npm versions
and integrity values are in the two package locks. The native Claude binary is
supplied by its integrity-locked platform package; installation scripts are disabled.
No third-party wrapper Actions are needed. Actions are pinned to resolved release
commit SHAs, not moving major tags. Hosted runners must support their current Node
runtime; older self-hosted runners are not targeted.

The initial npm audit identified KaTeX GHSA-238p-pmpm-9mq7 and RE2JS
GHSA-gg6h-894w-4m9c in markdownlint-cli2's pinned transitive dependencies. Explicit
npm overrides select the upstream patch markdownlint 0.42.1 and patched KaTeX
0.18.2. The resulting lock passed npm audit and repository Markdown lint. Remove
these overrides when markdownlint-cli2 adopts secure dependencies itself; recheck
compatibility rather than running a blanket forced audit fix.

The Gitleaks/actionlint binary installer verifies committed SHA-256 values before
extracting a single executable. Release checksums should be compared with upstream
checksum lists during review. Hash pinning prevents silent asset changes after
review; it does not protect against an already-compromised upstream release.

One scoped zizmor suppression preserves GitHub's documented `./.github/workflows/`
same-commit reusable-workflow syntax: current actionlint rejects zizmor's suggested
`$/` spelling. Other security findings remain blocking.

## Evaluated alternatives

- [Skill Creator source](https://github.com/anthropics/skills/tree/2c5958ecac7cee2b583967a2c4981d0f4a75c579/skills/skill-creator):
  inspected `SKILL.md`, `quick_validate.py`, `package_skill.py`, `run_eval.py` and
  `run_loop.py`. Validator reused directly; packager and trigger-only defaults
  differ from repository needs, as explained in the architecture/evaluation docs.
- [Agent Skills specification](https://agentskills.io/specification): required
  fields, supported optional fields, names and progressive directory conventions.
  Extra resource folders are permitted; no heading structure is mandated.
- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) and
  [commitlint](https://github.com/conventional-changelog/commitlint): standard parser
  adopted instead of a custom commit-message regex.
- [actionlint](https://github.com/rhysd/actionlint) and
  [zizmor](https://github.com/zizmorcore/zizmor): complementary syntax/expression and
  security checks; both are run against the implemented workflows.
- [Release Please](https://github.com/googleapis/release-please) 17.11.2,
  Apache-2.0, manifest monorepo support; [semantic-release](https://github.com/semantic-release/semantic-release)
  25.0.9, MIT; [Changesets](https://github.com/changesets/changesets) 3.0.3, MIT:
  reviewed, not installed. Explicit skill tags and GitHub CLI are sufficient for the
  current two independently packaged directories.
- [Promptfoo](https://www.promptfoo.dev/docs/providers/claude-agent-sdk/) 0.125.1,
  MIT, agent execution provider; [DeepEval](https://github.com/confident-ai/deepeval)
  4.2.4, Apache-2.0: reviewed, not installed. Keep existing human assertion grading
  and a small official-CLI adapter until automated semantic grading is required.
- [GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets)
  and [available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets):
  public Free support confirmed by documentation; actual account plan, metadata-rule
  availability need separate verification. Authenticated admin reads subsequently
  confirmed no rulesets/classic protection/environments and only the owner as a
  direct collaborator; no settings were changed.

No dependency is assumed safe solely because it is popular or official. Networked
dependency audits and repository secret scans are part of CI; they must be rerun
after lock changes. Development dependencies are not bundled into skill archives.
