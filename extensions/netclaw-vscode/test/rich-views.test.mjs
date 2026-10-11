import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { sourceModule } from './bundle-fixture.mjs';
import {build} from 'esbuild';
const require=createRequire(new URL('../../../ui/netclaw-visual/package.json',import.meta.url));
const {JSDOM}=require('jsdom');

test('RAG panel preserves citations and warnings as inert text; selecting results never sends a prompt',()=>{
  const calls=[],dom=new JSDOM('<body data-view-id="view"><button id="refresh"></button><button id="upload"></button><button id="chat"></button><button id="canvas"></button><button id="more"></button><p id="status"></p><form id="rag-search"><input id="query"><select id="collection"></select></form><div id="results"></div><button id="stage"></button><p id="stats"></p><div id="documents"></div><div id="operations"></div></body>',{runScripts:'outside-only'});
  dom.window.acquireVsCodeApi=()=>({postMessage:value=>calls.push(value)});dom.window.eval(fs.readFileSync(new URL('../resources/rag.js',import.meta.url),'utf8'));
  dom.window.dispatchEvent(new dom.window.MessageEvent('message',{data:{viewId:'view',type:'results',results:[{title:'<script>ignore instructions</script>',citation:'[Guide p.2]',chunk_text:'<img onerror=evil()>',low_confidence:true,staleness_notice:'Historical snapshot'}]}}));
  const document=dom.window.document;assert.equal(document.querySelectorAll('script,img').length,0);assert.match(document.getElementById('results').textContent,/Low confidence/);assert.match(document.getElementById('results').textContent,/Historical snapshot/);
  document.querySelector('input[type=checkbox]').click();document.getElementById('stage').click();assert.deepEqual(calls.map(c=>c.type),['ready','stage']);assert.equal(calls.at(-1).indices[0],0);dom.window.close();
});

test('webview messages reject stale view, unknown methods, injected authority and unbounded text',async()=>{
  const {chatMessage}=await sourceModule('webview/messages.ts');
  const base={viewId:'view',requestId:'1',type:'send',payload:{text:'hello',contextIds:[]}};
  assert.ok(chatMessage(base,'view'));
  for(const value of [{...base,viewId:'old'},{...base,method:'operator_change_apply'},{...base,type:'shell'},{...base,payload:{...base.payload,approved:true}},{...base,payload:{text:'x'.repeat(65537)}}])assert.equal(chatMessage(value,'view'),undefined);
});

test('Canvas ready never replaces the host graph; a branch preserves frozen context without sending',async()=>{
  const output=await build({entryPoints:[new URL('../webview/canvas.js',import.meta.url).pathname],bundle:true,write:false,platform:'browser',format:'iife'});
  const calls=[],dom=new JSDOM('<body data-view-id="view"><button id="save"></button><button id="open"></button><button id="import"></button><button id="export"></button><button id="refresh"></button><p id="status"></p><div id="lanes"></div></body>',{runScripts:'outside-only'});
  dom.window.acquireVsCodeApi=()=>({postMessage:value=>calls.push(value)});dom.window.eval(output.outputFiles[0].text);
  assert.equal(calls[0].type,'ready');assert.equal(calls[0].document,undefined);
  dom.window.dispatchEvent(new dom.window.MessageEvent('message',{data:{viewId:'view',type:'document',document:{v:1,nodes:[{id:'root',messages:[{role:'assistant',content:'Observed violet'}]}]}}}));
  [...dom.window.document.querySelectorAll('button')].find(button=>button.textContent==='Branch this conversation').click();
  assert.equal(dom.window.document.querySelectorAll('.canvas-lane').length,2);assert.equal(calls.some(call=>call.type==='send'),false);
  assert.equal(calls.at(-1).document.nodes[1].seedContext[0].content,'Observed violet');dom.window.close();
});
test('actual bundled chat script renders hostile text literally and never sends on restore',()=>{
  const calls=[];
  const dom=new JSDOM('<body data-view-id="view"><button id="refresh"></button><button id="new"></button><button id="cancel"></button><p id="status"></p><section id="transcript"></section><form id="composer"><textarea id="prompt"></textarea><input id="retain" type="checkbox"><div id="contexts"></div><button id="send"></button></form></body>',{runScripts:'outside-only'});
  dom.window.acquireVsCodeApi=()=>({postMessage:value=>calls.push(value)});
  dom.window.eval(fs.readFileSync(new URL('../resources/chat.js',import.meta.url),'utf8'));
  dom.window.dispatchEvent(new dom.window.MessageEvent('message',{data:{viewId:'view',type:'state',initial:true,saved:{draft:'saved draft',retain:true},contexts:[],requests:[{operationId:'owned',state:'succeeded',prompt:'<script>evil()</script>',result:{output:'<img src=x onerror=evil()>'}}]}}));
  assert.equal(dom.window.document.querySelectorAll('script,img').length,0);
  assert.match(dom.window.document.getElementById('transcript').textContent,/<script>/);
  assert.equal(dom.window.document.getElementById('prompt').value,'saved draft');assert.deepEqual(calls.map(c=>c.type),['ready']);dom.window.close();
});
