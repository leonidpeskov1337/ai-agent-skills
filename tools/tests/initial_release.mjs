import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {discover, relevant, analyzeCommits} from '../skill-release.mjs';

 const {default:release}=await import('semantic-release');
 const original=process.cwd(), temp=mkdtempSync(join(tmpdir(),'skill-release-core-'));
 const remote=join(temp,'remote.git'), work=join(temp,'work');mkdirSync(work);
 const git=(...args)=>execFileSync('git',['-C',work,'-c','user.name=Test','-c','user.email=test@example.invalid',...args],{encoding:'utf8'}).trim();
 try {
  execFileSync('git',['init','--bare','-b','main',remote]);git('init','-b','main');
  git('config','user.name','Test');git('config','user.email','test@example.invalid');
  mkdirSync(join(work,'third-skill'));writeFileSync(join(work,'third-skill','SKILL.md'),'synthetic');
  git('add','.');git('commit','-m','feat: add third skill');git('remote','add','origin',remote);git('push','-u','origin','main');
  const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!k.startsWith('GITHUB') && !['CI','GITLAB_CI'].includes(k)));
  Object.assign(env,{GIT_AUTHOR_NAME:'Test',GIT_AUTHOR_EMAIL:'test@example.invalid',GIT_COMMITTER_NAME:'Test',GIT_COMMITTER_EMAIL:'test@example.invalid'});
  const options={ci:false,branches:['main'],repositoryUrl:remote.replaceAll('\\','/'),tagFormat:'third-skill/v${version}',plugins:[join(original,'node_modules/@semantic-release/commit-analyzer/index.js')]};
  const first=await release(options,{cwd:work,env});assert.equal(first.nextRelease.version,'1.0.0');
  assert.equal(git('tag','--list','third-skill/v*'),'third-skill/v1.0.0');
  assert.equal(await release(options,{cwd:work,env}),false);
 } finally {process.chdir(original);rmSync(temp,{recursive:true,force:true});}
