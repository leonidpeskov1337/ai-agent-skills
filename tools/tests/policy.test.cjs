const {test} = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const {validBranch} = require('../branch_policy.cjs');

test('branch policy validates fork branch names and bot identities', () => {
  for (const branch of ['feature/mimir-discovery', 'fix/metrics-timeout', 'ci/skill-validation']) {
    assert.equal(validBranch(branch, 'fork-contributor'), true);
  }
  for (const branch of ['main', 'feature/Uppercase', 'fix/two--hyphens', 'fix/nested/path', 'codex/task']) {
    assert.equal(validBranch(branch, 'person'), false);
  }
  assert.equal(validBranch('dependabot/npm_and_yarn/tool-1.2', 'dependabot[bot]'), true);
  assert.equal(validBranch('dependabot/npm_and_yarn/tool-1.2', 'person'), false);
  assert.equal(validBranch('renovate/configure', 'renovate[bot]'), true);
});

test('commitlint rejects an invalid earlier commit even when the tip is valid', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'skill-commit-range-'));
  const git = process.env.GIT_EXECUTABLE || 'git';
  const runGit = (...args) => {
    const result = spawnSync(git, ['-C', directory,
      '-c', 'user.name=Policy Test', '-c', 'user.email=policy-test@example.invalid', ...args],
    {encoding: 'utf8'});
    assert.equal(result.status, 0, result.stderr);
    return result.stdout.trim();
  };
  try {
    runGit('init');
    runGit('commit', '--allow-empty', '-m', 'chore: initialize fixture');
    const base = runGit('rev-parse', 'HEAD');
    runGit('commit', '--allow-empty', '-m', 'Invalid middle commit');
    runGit('commit', '--allow-empty', '-m', 'fix: valid tip');
    const head = runGit('rev-parse', 'HEAD');
    const result = spawnSync(process.execPath, [path.resolve('node_modules/@commitlint/cli/cli.js'),
      '--config', path.resolve('commitlint.config.cjs'), '--from', base, '--to', head, '--verbose'],
    {cwd: directory, encoding: 'utf8'});
    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /Invalid middle commit/);
    assert.match(result.stdout, /fix: valid tip/);
  } finally {
    fs.rmSync(directory, {recursive: true, force: true});
  }
});

test('commitlint accepts conventional, breaking, merge and revert commits', () => {
  const cli = path.resolve('node_modules/@commitlint/cli/cli.js');
  for (const input of ['feat(kubernetes): add Mimir discovery', 'fix!: change behavior',
    'feat: change\n\nBREAKING CHANGE: remove old interface',
    "Merge branch 'main' into feature/example", 'Revert "old change"']) {
    const result = spawnSync(process.execPath, [cli, '--verbose'], {input, encoding: 'utf8'});
    assert.equal(result.status, 0, result.stdout + result.stderr);
  }
  for (const input of ['Add a thing', 'invalid: thing', 'fix:', 'feat(scope) missing colon']) {
    const result = spawnSync(process.execPath, [cli, '--verbose'], {input, encoding: 'utf8'});
    assert.notEqual(result.status, 0, input);
  }
});
