// Test-only command boundary: no GitHub requests or real asset publication.
import childProcess from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
import {readFileSync,writeFileSync} from 'node:fs';
const original = childProcess.execFileSync;
childProcess.execFileSync = (command,args,options) => {
  if (!['gh','python'].includes(command)) return original(command,args,options);
  const state=JSON.parse(readFileSync(process.env.RELEASE_TEST_STATE,'utf8'));
  state.calls.push([command,...args]);
  const save=()=>writeFileSync(process.env.RELEASE_TEST_STATE,JSON.stringify(state));
  if(command==='python') {save();return '';}
  if(args[1]==='view') {
    save();if(!state.exists) throw new Error('Synthetic missing release');
    return JSON.stringify({assets:state.assets.map(name=>({name}))});
  }
  if(args[1]==='create') {if(state.exists) throw new Error('Overwrite attempted');state.exists=true;}
  if(args[1]==='upload') {
    const name=args[3].split('/').at(-1);
    if(state.assets.includes(name)) throw new Error('Asset overwrite attempted');
    state.assets.push(name);
  }
  save();return '';
};
syncBuiltinESMExports();
