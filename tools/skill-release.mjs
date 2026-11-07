import {execFileSync} from 'node:child_process';
import {existsSync, readdirSync} from 'node:fs';
import {analyzeCommits as analyze} from '@semantic-release/commit-analyzer';
import {generateNotes as notes} from '@semantic-release/release-notes-generator';
const git = (...args) => execFileSync('git', args, {encoding: 'utf8'}).trim();
export function discover() {
  return readdirSync('.', {withFileTypes:true}).filter(d => d.isDirectory() && existsSync(`${d.name}/SKILL.md`)).map(d => d.name).sort();
}
export function relevant(skill, commits) {
  return commits.filter(c => git('diff-tree','--root','--no-commit-id','--name-only','-r',c.hash,'--',skill).length > 0);
}
export async function analyzeCommits(config, context) {
  const commits = relevant(config.skill, context.commits);
  if (!commits.length) return null;
  return await analyze({}, {...context, commits}) || 'patch';
}
export async function generateNotes(config, context) {
  return notes({}, {...context, commits: relevant(config.skill, context.commits)});
}
export async function prepare(config) {
  execFileSync('python', ['-m','tools.package_skill',config.skill], {stdio:'inherit'});
}
