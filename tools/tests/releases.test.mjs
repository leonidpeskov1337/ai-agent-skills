import {pathToFileURL} from 'node:url';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync} from 'node:fs';
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
  writeFileSync('second-skill/reference.md','same commit affects two skills');
  writeFileSync('third-skill/reference.md','same commit affects two skills');
  git('add','.');git('commit','-m','fix: update two skills');
  const multiple=[{hash:git('rev-parse','HEAD'),message:'fix: update two skills'}];
  assert.equal(relevant('first-skill',multiple).length,0);
  assert.equal(await analyzeCommits({skill:'second-skill'},{...context,commits:multiple}),'patch');
  assert.equal(await analyzeCommits({skill:'third-skill'},{...context,commits:multiple}),'patch');
  writeFileSync('shared.txt','tooling only');git('add','.');git('commit','-m','feat!: change shared tooling');
  const shared=[{hash:git('rev-parse','HEAD'),message:'feat!: change shared tooling'}];
  for (const skill of discover()) assert.equal(await analyzeCommits({skill},{...context,commits:shared}),null);

 } finally {process.chdir(original);rmSync(temp,{recursive:true,force:true});}
});

test('semantic-release creates the initial third-skill tag and retry is a no-op', () => {
 const env={...process.env}; delete env.NODE_TEST_CONTEXT;
 execFileSync(process.execPath,['tools/tests/initial_release.mjs'],{env,stdio:'pipe'});
});

test('release recovery creates missing assets once and complete retries do not rebuild', () => {
 const original=process.cwd(), temp=mkdtempSync(join(tmpdir(),'skill-publishing-'));
 const git=(...args)=>execFileSync('git',['-C',temp,'-c','user.name=Test','-c','user.email=test@example.invalid',...args],{encoding:'utf8'}).trim();
 try {
  git('init','-b','main');mkdirSync(join(temp,'third-skill'));
  writeFileSync(join(temp,'third-skill/SKILL.md'),'synthetic');git('add','.');git('commit','-m','feat: initial fixture');git('tag','third-skill/v1.0.0');
  const stateFile=join(temp,'state.json');
  const invoke=()=>{const env={...process.env,RELEASE_TEST_STATE:stateFile};delete env.NODE_TEST_CONTEXT;execFileSync(process.execPath,['--import',pathToFileURL(join(original,'tools/tests/release_commands_stub.mjs')).href,join(original,'tools/release.mjs')],{cwd:temp,env,stdio:'pipe'});return JSON.parse(readFileSync(stateFile,'utf8'));};
  writeFileSync(stateFile,JSON.stringify({exists:false,assets:[],calls:[]}));
  let state=invoke();assert.equal(state.calls.filter(c=>c[1]==='release'&&c[2]==='create').length,1);assert.equal(state.assets.length,2);
  state.calls=[];writeFileSync(stateFile,JSON.stringify(state));state=invoke();
  assert.equal(state.calls.filter(c=>c[0]==='python'||c[2]==='upload'||c[2]==='create').length,0);
  writeFileSync(stateFile,JSON.stringify({exists:true,assets:['third-skill.skill'],calls:[]}));state=invoke();
  assert.equal(state.calls.filter(c=>c[2]==='create').length,0);assert.equal(state.calls.filter(c=>c[2]==='upload').length,1);
  writeFileSync(join(temp,'shared.txt'),'tooling change');git('add','shared.txt');git('commit','-m','fix: shared tooling only');
  state.calls=[];writeFileSync(stateFile,JSON.stringify(state));state=invoke();
  assert.equal(state.calls.length,0);

 } finally {rmSync(temp,{recursive:true,force:true});}
});
