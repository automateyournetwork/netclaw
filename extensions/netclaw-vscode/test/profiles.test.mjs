import test from 'node:test';
import assert from 'node:assert/strict';
import { sourceModule } from './bundle-fixture.mjs';

test('independent windows retain same-label profiles and host separation',async()=>{
  const {Profiles,hostContext}=await sourceModule('state/profiles.ts',{env:{}});
  const values=new Map(),state={get:(key,fallback)=>structuredClone(values.has(key)?values.get(key):fallback),keys:()=>[...values.keys()],async update(key,value){await new Promise(resolve=>setTimeout(resolve,2));values.set(key,structuredClone(value));}};
  const first=new Profiles(state),second=new Profiles(state);
  const input={label:'Same label',transport:'local',home:'/fixture/home',nodePath:'/fixture/node',launcherPath:'/fixture/repo/scripts/netclaw-operator.mjs',harness:'hermes'};
  const [a,b]=await Promise.all([first.save(input),second.save(input)]);
  assert.equal(first.list().length,2);assert.notEqual(a.id,b.id);
  await first.save({...input,context:'another-host'});assert.equal(second.list().length,2);
  await second.remove(a.id);assert.equal(first.list().length,1);assert.equal(first.list()[0].id,b.id);
  assert.equal(first.list()[0].context,hostContext());
});

test('atomic profile files survive stale Memento echoes and process restart',async t=>{
  const fs=await import('node:fs'),os=await import('node:os'),path=await import('node:path');
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'netclaw150-profiles-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const {Profiles}=await sourceModule('state/profiles.ts',{env:{}});
  const stale={get:(_key,fallback)=>fallback,keys:()=>[],update:()=>{throw Error('must not write a whole stale Memento');}};
  const input={label:'Same label',transport:'local',home:'/fixture/home',nodePath:'/fixture/node',launcherPath:'/fixture/repo/scripts/netclaw-operator.mjs',harness:'hermes'};
  const one=new Profiles(stale,directory),two=new Profiles(stale,directory);
  const [a,b]=await Promise.all([one.save(input),two.save(input)]);
  assert.equal(new Profiles(stale,directory).list().length,2);
  await one.remove(a.id);assert.equal(new Profiles(stale,directory).list()[0].id,b.id);
});

test('SSH launch preserves hostile path text as a single quoted argument and verifies known hosts',async()=>{
  const {launchProfile,quotePosix}=await sourceModule('connection/connect.ts',{env:{}});
  const profile={id:'fixture',label:'fixture',transport:'ssh',home:"/fixture/a'$(echo injection); x",nodePath:'/usr/bin/node',launcherPath:'/fixture/repo/scripts/netclaw-operator.mjs',harness:'openclaw',sshAlias:'fixture-alias'};
  const launch=launchProfile(profile);assert.equal(launch.command,'ssh');assert.ok(launch.args.includes('StrictHostKeyChecking=yes'));assert.ok(launch.args.includes('ForwardAgent=no'));assert.equal(launch.args.at(-1).includes(quotePosix(profile.home)),true);
  const {spawnSync}=await import('node:child_process');
  const actual=spawnSync('/bin/sh',['-c',`printf '%s' ${quotePosix(profile.home)}`],{encoding:'utf8'});
  assert.equal(actual.stdout,profile.home);assert.equal(actual.status,0);
  assert.throws(()=>launchProfile({...profile,sshAlias:'-oProxyCommand=bad'}));
  assert.throws(()=>launchProfile({...profile,home:'/fixture\ncommand'}));
});
