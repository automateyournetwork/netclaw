import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
const built=await build({stdin:{contents:`import React from 'react';import {createRoot} from 'react-dom/client';import Pal from './Pal.jsx';const root=createRoot(document.getElementById('root'));window.showPal=active=>root.render(<Pal active={active}/>);window.closePal=()=>root.unmount();window.showPal(true);`,resolveDir:new URL('.',import.meta.url).pathname,loader:'jsx'},bundle:true,write:false,format:'iife',define:{'process.env.NODE_ENV':'"production"'},plugins:[{
  name:'fake-daily',setup(builder){builder.onResolve({filter:/^@daily-co\/daily-js$/},()=>({path:'daily',namespace:'fixture'}));builder.onLoad({filter:/.*/,namespace:'fixture'},()=>({contents:`export default {createCallObject(options){window.dailyOptions=options;const handlers={};window.dailyHandlers=handlers;return {on(name,fn){handlers[name]=fn;return this;},participants(){return {local:{local:true,session_id:'local'}};},async join(){if(window.failJoin)throw Error('join failed');},async destroy(){window.destroyed=true;},sendAppMessage(event){window.sent.push(event);}};}};`}));}
}]});
const js=built.outputFiles[0].text;
const settle=()=>new Promise(resolve=>setTimeout(resolve,35));

async function until(predicate) {
  const deadline=Date.now()+3000;
  while(!predicate()) {
    if(Date.now()>deadline)assert.fail('Pal fixture did not become ready');
    await new Promise(resolve=>setTimeout(resolve,5));
  }
}
async function fixture(t){
  const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost:3000',runScripts:'outside-only',pretendToBeVisual:true});
  const window=dom.window,calls=[];window.sent=[];
  window.HTMLMediaElement.prototype.play=()=>Promise.resolve();
  window.fetch=async(url,options={})=>{
    calls.push([url,options]);
    const result=url==='/api/pal/status'?{enabled:true,configured:true,confirmationRequired:false,remainingSeconds:1200}:
      url==='/api/pal/sessions'?{id:'local-session',deadline:Date.now()+120000,url:'https://tavus.daily.co/fixture',token:'temporary-token'}:
      url.endsWith('/turns')?{callId:'call_1',state:'complete',localAnswer:'Private local answer',event:{event_type:'conversation.tool_result',properties:{output:'Review your local panel'}}}:
      url.endsWith('/speech/call_1')?{event_type:'conversation.echo',properties:{text:'Private local answer'}}:{};
    return {ok:true,json:async()=>result};
  };
  t.after(()=>{window.closePal?.();dom.window.close();});
  window.eval(js);await until(()=>button(window.document,'Start two-minute call')?.disabled===false);
  return {window,document:window.document,calls};
}
const button=(document,label)=>[...document.querySelectorAll('button')].find(b=>b.textContent===label);
test('opening Pal does not create a call; local icon selection never uploads',async t=>{
  const {window,document,calls}=await fixture(t);
  assert.equal(calls.some(([url])=>url==='/api/pal/sessions'),false);
  const input=document.querySelector('input[type=file]');
  Object.defineProperty(input,'files',{value:[new window.File(['fixture-image'],'smiley.png',{type:'image/png'})]});
  input.dispatchEvent(new window.Event('change',{bubbles:true}));await settle();
  assert.match(window.localStorage.getItem('nc-pal-icon-v1'),/^data:image\/png;base64,/);
  assert.equal(document.querySelector('img').alt,'Your local Pal icon');
  assert.equal(calls.some(([,options])=>options.body?.includes('fixture-image')),false);
  assert.deepEqual(calls.map(([url])=>url),['/api/hud/session','/api/pal/status']);
});
test('call camera is disabled, automatic results exclude answers, speech requires click and navigation ends',async t=>{
  const {window,document,calls}=await fixture(t);
  button(document,'Start two-minute call').click();await until(()=>window.dailyOptions && window.dailyHandlers?.['app-message']);
  assert.equal(window.dailyOptions.videoSource,false);assert.equal(window.dailyOptions.startVideoOff,true);
  await window.dailyHandlers['app-message']({fromId:'tavus',data:{event_type:'conversation.tool_call'}});await settle();
  assert.match(document.querySelector('.pal-answer').textContent,/Private local answer/);
  assert.equal(window.sent.length,1);assert.doesNotMatch(JSON.stringify(window.sent[0]),/Private/);
  button(document,'Speak this answer').click();await settle();
  assert.equal(window.sent[1].properties.text,'Private local answer');
  window.showPal(false);await settle();
  assert.equal(window.destroyed,true);assert.equal(calls.filter(([url])=>url.endsWith('/end')).length,1);
  assert.equal(calls.filter(([url])=>url==='/api/pal/sessions').length,1);
});
test('a failed media join still ends the already-created provider conversation',async t=>{
  const {window,document,calls}=await fixture(t);window.failJoin=true;
  button(document,'Start two-minute call').click();await settle();
  assert.equal(window.destroyed,true);assert.equal(calls.filter(([url])=>url.endsWith('/end')).length,1);
  assert.match(document.querySelector('[role=alert]').textContent,/join failed/);
});
