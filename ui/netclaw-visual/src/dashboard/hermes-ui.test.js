import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {JSDOM,VirtualConsole} from 'jsdom';
const built=await build({stdin:{contents:`import React from 'react';import {createRoot} from 'react-dom/client';import StandardChat from './StandardChat.jsx';import {bootstrapRuntime} from '../shared/runtime-client.js';const root=createRoot(document.getElementById('root'));window.showChat=pal=>root.render(<StandardChat pal={pal}/>);window.closeChat=()=>root.unmount();bootstrapRuntime().then(()=>window.showChat(false));`,resolveDir:new URL('.',import.meta.url).pathname,loader:'jsx'},bundle:true,write:false,format:'iife',define:{'process.env.NODE_ENV':'"production"'}});
const wait=()=>new Promise(r=>setTimeout(r,50));
const button=(doc,label)=>[...doc.querySelectorAll('button')].find(b=>b.textContent===label);
test('Hermes chat restores uncertain draft, recovers without replay, and shares local Avatar context',async t=>{
 const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost:3000',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});
 const w=dom.window,calls=[];let state='unknown';w.AbortSignal=AbortSignal;w.AbortController=AbortController;w.HTMLMediaElement.prototype.play=()=>Promise.resolve();
 w.fetch=async(url,options={})=>{calls.push([url,options]);return {ok:true,json:async()=>url==='/api/runtime'?{kind:'hermes',installationId:'11111111-1111-4111-8111-111111111111',readiness:{ready:true,executionVerified:false}}:url==='/api/chat/models'?{models:[],selectionSupported:false}:url==='/api/chat/conversations'?{conversations:[],sourceAvailable:true}:url==='/api/chat/requests'?{requestId:'owned',state:'queued'}:url==='/api/chat/requests/owned'?{requestId:'owned',state,fromGateway:state==='completed',response:'Recovered confirmed answer',runtime:{model:'qualified-model',provider:'fixture'}}:{}};};
 w.eval(built.outputFiles[0].text);await wait();t.after(()=>{w.closeChat();w.close();});
 const doc=w.document,input=doc.querySelector('textarea');assert.ok(input,JSON.stringify({errors,html:doc.body.innerHTML}));assert.equal(doc.querySelector('#standard-chat-model').disabled,true);
 Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'Remember my branch');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait();input.closest('form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait();
 assert.match(doc.querySelector('[role=alert]').textContent,/Outcome unknown/);assert.equal(input.value,'Remember my branch');assert.equal(calls.filter(([u,o])=>u==='/api/chat/requests'&&o.method==='POST').length,1);
 state='completed';button(doc,'Check status').click();await wait();assert.match(doc.querySelector('[role=log]').textContent,/Recovered confirmed answer/);assert.equal(input.value,'');assert.match(doc.body.textContent,/qualified-model/);
 w.showChat(true);await wait();w.showChat(false);await wait();assert.match(doc.querySelector('[role=log]').textContent,/Recovered confirmed answer/);assert.equal(calls.filter(([u,o])=>u==='/api/chat/requests'&&o.method==='POST').length,1);assert.equal(calls.some(([u])=>u==='/api/pal/sessions'),false);assert.deepEqual(errors,[]);
});
