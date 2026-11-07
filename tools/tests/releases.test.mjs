import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {discover, relevant, analyzeCommits} from '../skill-release.mjs';
test('filesystem discovery and commit analysis isolate independent skills', async () => {
 const original=process.cwd(), temp=mkdtempSync(join(tmpdir(),'skill-releases-'));
 const git=(...args)=>execFileSync('git',['-c','user.name=Test','-c','user.email=test@example.invalid',...args],{encoding:'utf8'}).trim();
 try {
  process.chdir(temp); git('init','-b','main');
  for (const skill of ['first-skill','second-skill','third-skill']) {
   mkdirSync(skill); writeFileSync(`${skill}/SKILL.md`, `---\nname: ${skill}\ndescription: Test skill\n---\n`);
  }
  git('add','.');git('commit','-m','feat: initial skills');
  assert.equal(discover().length,3);
  writeFileSync('first-skill/reference.md','new guidance');git('add','.');git('commit','-m','feat: extend first skill');
  const commits=[{hash:git('rev-parse','HEAD'),message:'feat: extend first skill'}];
  assert.equal(relevant('second-skill',commits).length,0);
  const context={commits,cwd:temp,logger:{log(){}}};
  assert.equal(await analyzeCommits({skill:'first-skill'},context),'minor');
  assert.equal(await analyzeCommits({skill:'second-skill'},context),null);
  assert.equal(await analyzeCommits({skill:'first-skill'},{...context,commits:[{...commits[0],message:'feat!: remove old interface'}]}),'major');
 } finally {process.chdir(original);rmSync(temp,{recursive:true,force:true});}
});

test('semantic-release creates the initial third-skill tag and retry is a no-op', () => {
 const env={...process.env}; delete env.NODE_TEST_CONTEXT;
 execFileSync(process.execPath,['tools/tests/initial_release.mjs'],{env,stdio:'pipe'});
});
