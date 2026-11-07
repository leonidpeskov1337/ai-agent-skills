const prefixes = 'feature|fix|skill|refactor|docs|test|ci|chore|security';
const branchPattern = new RegExp(`^(${prefixes})/[a-z0-9]+(?:-[a-z0-9]+)*$`);

function validBranch(branch, login) {
  if (branchPattern.test(branch)) return true;
  // Exceptions depend on verified GitHub actor identity, never branch text alone.
  return (login === 'dependabot[bot]' && /^dependabot\/[a-zA-Z0-9/_@.-]+$/.test(branch)) ||
    (login === 'renovate[bot]' && /^renovate\/[a-z0-9/_@.-]+$/.test(branch));
}

if (require.main === module) {
  const fs = require('node:fs');
  const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
  const pr = event.pull_request;
  if (!pr || !validBranch(pr.head.ref, pr.user.login)) {
    console.error('Use feature/, fix/, skill/, refactor/, docs/, test/, ci/, chore/, or security/ followed by lowercase kebab-case.');
    process.exitCode = 1;
  }
}
module.exports = {validBranch};
