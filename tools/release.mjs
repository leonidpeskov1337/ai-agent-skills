import semanticRelease from 'semantic-release';
import {execFileSync} from 'node:child_process';
import {writeFileSync} from 'node:fs';
import {discover} from './skill-release.mjs';
const git = (...args) => execFileSync('git', args, {encoding:'utf8'}).trim();
function publish(skill, tag, releaseNotes) {
  let release;
  try { release = JSON.parse(execFileSync('gh',['release','view',tag,'--json','assets'],{encoding:'utf8',stdio:['ignore','pipe','pipe']})); }
  catch {
    writeFileSync('.ci-release-notes.md', releaseNotes || `Validated independent release of ${skill}.`);
    execFileSync('gh',['release','create',tag,'--verify-tag','--title',tag,'--notes-file','.ci-release-notes.md'],{stdio:'inherit'});
    release = {assets:[]};
  }
  for (const suffix of ['.skill','.skill.sha256']) {
    const name = skill + suffix;
    if (!release.assets.some(a => a.name === name))
      execFileSync('gh',['release','upload',tag,`dist/${name}`],{stdio:'inherit'});
  }
}
for (const skill of discover()) {
  // Recover a tag created before a failed publish, without calculating another version.
  const tags = git('tag','--points-at','HEAD','--list',`${skill}/v*`).split('\n').filter(Boolean);
  if (tags.length) {
    execFileSync('python',['-m','tools.package_skill',skill],{stdio:'inherit'});
    for (const tag of tags) publish(skill,tag);
    continue;
  }
  const result = await semanticRelease({
    branches:['main'], tagFormat: `${skill}/v${'${version}'}`,
    plugins: [[ './tools/skill-release.mjs', {skill} ]],
  });
  if (result) publish(skill,result.nextRelease.gitTag,result.nextRelease.notes);
}
