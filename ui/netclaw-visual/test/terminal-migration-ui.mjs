// Actual React component, controlled local API. No browser/device/hosted service.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {build} from 'esbuild';
import {JSDOM} from 'jsdom';
import React, {act, useState} from 'react';
import {createRoot} from 'react-dom/client';
const require=createRequire(import.meta.url);
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost:12345'});
globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const bundle=await build({entryPoints:['src/canvas-chat/TerminalChangeControl.jsx'],bundle:true,write:false,format:'cjs',platform:'node',external:['react']});
const module={exports:{}};new Function('require','module','exports',bundle.outputFiles[0].text)(require,module,module.exports);
const Control=module.exports.default;
const device={id:'fixture',name:'Fixture',host:'192.0.2.1',port:22,protocol:'ssh',supported:true,valid:true};
const captured=[],requests=[];let latest;
globalThis.fetch=async(url,options={})=>{
  requests.push({url,options});let data;
  if(url.endsWith('change-policy'))data={enabled:true,revision:'revision',devices:[device]};
  else if(url.endsWith('migration-inventories'))data=[{harness:'a'.repeat(32),testbed:'b'.repeat(64),devices:[device]}];
  else if(url.endsWith('migration-candidates')){
    const content=JSON.parse(options.body).content;
    data={artifact_ref:'c'.repeat(32),sha256:createHash('sha256').update(content).digest('hex'),bytes:Buffer.byteLength(content)};
  } else throw Error('Unexpected route');
  return {ok:true,status:200,json:async()=>data};
};
function Fixture(){const [value,setValue]=useState({mode:'local-lab',targetDeviceIds:['fixture'],policyRevision:null});latest=value;
  return React.createElement(Control,{devices:[device],value,busy:false,onChange:v=>{captured.push(v);setValue(v);}});}
const root=createRoot(document.querySelector('#app'));
const label=text=>[...document.querySelectorAll('label')].find(l=>l.textContent.includes(text));
try {
  await act(async()=>root.render(React.createElement(Fixture)));
  assert.match(document.body.textContent,/file stays on this installation/);
  const input=document.querySelector('input[type=file]');
  const data=new TextEncoder().encode('hostname PRIVATE_CANDIDATE_CANARY\n');
  Object.defineProperty(input,'files',{configurable:true,value:[{size:data.byteLength,arrayBuffer:async()=>data.buffer}]});
  await act(async()=>input.dispatchEvent(new window.Event('change',{bubbles:true})));
  assert.match(document.body.textContent,/SHA-256/);assert.doesNotMatch(document.body.textContent,/PRIVATE_CANDIDATE_CANARY/);
  const refresh=[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Refresh active'));
  await act(async()=>refresh.click());
  const select=document.querySelector('[aria-label="Active pyATS binding"]');
  await act(async()=>{select.value='a'.repeat(32);select.dispatchEvent(new window.Event('change',{bubbles:true}));});
  await act(async()=>label('I reviewed this exact').querySelector('input').click());
  assert.equal(latest.migration.artifact_ref,'c'.repeat(32));assert.equal(latest.migration.profile,'ospf-routing-v1');
  assert.doesNotMatch(JSON.stringify(captured),/PRIVATE_CANDIDATE_CANARY/);
  assert.equal(requests.filter(r=>r.options.body?.includes('PRIVATE_CANDIDATE_CANARY')).length,1);
  assert.equal(requests.find(r=>r.options.body?.includes('PRIVATE_CANDIDATE_CANARY')).url,'/api/terminal/intent/migration-candidates');
  const target=label('Fixture ·').querySelector('input');
  await act(async()=>target.click());assert.equal(latest.migration,undefined);
  await act(async()=>target.click());assert.equal(latest.migration,undefined);
  await act(async()=>label('I reviewed this exact').querySelector('input').click());
  const mode=document.querySelector('[aria-label="Change control mode"]');
  await act(async()=>{mode.value='production';mode.dispatchEvent(new window.Event('change',{bubbles:true}));});
  assert.equal(latest.migration,undefined);
  await act(async()=>{mode.value='local-lab';mode.dispatchEvent(new window.Event('change',{bubbles:true}));});
  const currentFile=document.querySelector('input[type=file]');let finishOld;
  Object.defineProperty(currentFile,'files',{configurable:true,value:[{size:40,arrayBuffer:()=>new Promise(resolve=>{finishOld=resolve;})}]});
  await act(async()=>currentFile.dispatchEvent(new window.Event('change',{bubbles:true})));
  const newer=new TextEncoder().encode('hostname newer-candidate\n');
  Object.defineProperty(currentFile,'files',{configurable:true,value:[{size:newer.byteLength,arrayBuffer:async()=>newer.buffer}]});
  await act(async()=>currentFile.dispatchEvent(new window.Event('change',{bubbles:true})));
  await act(async()=>finishOld(new TextEncoder().encode('hostname stale-candidate\n').buffer));
  assert.match(document.body.textContent,new RegExp(createHash('sha256').update(newer).digest('hex')));
  assert.equal(requests.filter(r=>r.options.body?.includes('stale-candidate')).length,0);
  console.log('Migration UI: actual JSX file selection, private local upload, hash review, process/profile binding and decline passed (JSDOM, not desktop acceptance).');
} finally {await act(async()=>root.unmount());dom.window.close();}
