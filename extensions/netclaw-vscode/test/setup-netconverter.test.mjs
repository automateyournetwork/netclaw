import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {load} from './load.mjs';
import {build} from 'esbuild';
import {createRequire} from 'node:module';
const {SetupDraft}=await load('src/setup/plan.ts');
const schema=JSON.parse(fs.readFileSync('../../config/claw-plan.schema.json','utf8'));
const catalog=JSON.parse(fs.readFileSync('../../config/components/catalog.json','utf8'));
const require=createRequire(import.meta.url);
const bundle=await build({entryPoints:['src/views/setup-wizard.ts'],bundle:true,write:false,platform:'node',format:'cjs',external:['vscode']});
function wizardFixture(picks){
  const questions=[],saves=[],module={exports:{}};
  const vscode={window:{showQuickPick:async(options,config)=>{questions.push({options,config});const picked=picks.shift();return options.find(o=>o.id===picked);}}};
  new Function('require','module','exports',bundle.outputFiles[0].text)(name=>name==='vscode'?vscode:require(name),module,module.exports);
  const wizard=Object.create(module.exports.SetupWizard.prototype);
  wizard.local={get:(_key,fallback)=>fallback,update:async(key,value)=>saves.push({key,value})};
  wizard.catalog=catalog;wizard.pendingSecrets=new Map();wizard.draft=new SetupDraft(schema,catalog);
  wizard.draft.replace({schema:1,claws:[{id:'one',displayName:'One',harness:'openclaw',provider:{id:'none',credentialKeys:[]},capabilities:{components:['netconverter']},settings:{}},
    {id:'two',displayName:'Two',settings:{NETCONVERTER_MODE:{kind:'value',value:'hosted-readonly'}}}]},0);
  return {wizard,questions,saves};
}

test('real setup wizard uses bounded mode picker, preserves neighbor and cancellation',async()=>{
  for(const mode of ['hosted-readonly','local-terminal']){
    const f=wizardFixture(['NETCONVERTER_MODE',mode]);await f.wizard.action('settings',{owner:'one'});
    const plan=f.wizard.draft.snapshot().answers;
    assert.equal(plan.claws[0].settings.NETCONVERTER_MODE.value,mode);
    assert.equal(plan.claws[1].settings.NETCONVERTER_MODE.value,'hosted-readonly');assert.equal(f.saves.length,1);
    assert.equal(f.questions[1].options.length,2);
  }
  for(const picks of [[],['NETCONVERTER_MODE']]){
    const f=wizardFixture(picks),before=f.wizard.draft.snapshot();await f.wizard.action('settings',{owner:'one'});
    assert.deepEqual(f.wizard.draft.snapshot(),before);assert.equal(f.saves.length,0);
  }
});

test('NetConverter modes persist independently and credentials remain native references',()=>{
  const draft=new SetupDraft(schema,catalog);
  const value={schema:1,assumptions:[],unresolved:[],claws:[{id:'claw-a',settings:{NETCONVERTER_MODE:{kind:'value',value:'local-terminal'},NETCONVERTER_API_KEY:{kind:'secret',key:'NETCONVERTER_API_KEY',owner:'claw-a',source:'later'}}},{id:'claw-b',settings:{NETCONVERTER_MODE:{kind:'value',value:'hosted-readonly'}}}]};
  const state=draft.replace(value,0);
  assert.equal(state.answers.claws[0].settings.NETCONVERTER_MODE.value,'local-terminal');
  assert.equal(state.answers.claws[1].settings.NETCONVERTER_MODE.value,'hosted-readonly');
  const bad=structuredClone(value);bad.claws[0].settings.NETCONVERTER_MODE.value='anything';
  assert.throws(()=>draft.replace(bad,state.revision),/supported NetConverter/);
  assert.deepEqual(draft.snapshot(),state);
});

test('NetConverter keys in non-secret answers and ambiguous paths are refused',()=>{
  for(const key of ['nck_live_12345678','nck_test_12345678']){
    const draft=new SetupDraft(schema,catalog);
    assert.throws(()=>draft.replace({schema:1,assumptions:[key],unresolved:[]},0),/native secret/);
  }
  for(const value of ['relative','/private/../elsewhere']){
    const draft=new SetupDraft(schema,catalog);
    assert.throws(()=>draft.replace({schema:1,assumptions:[],unresolved:[],claws:[{id:'claw-a',settings:{NETCONVERTER_WORKSPACE:{kind:'value',value}}}]},0),/absolute host paths/);
  }
});
