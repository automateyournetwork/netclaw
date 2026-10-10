import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Execute the production session handlers, with storage/state boundaries replaced.
function handlers({ failSave = false, failDelete = false } = {}) {
  const source = fs.readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  const newSession =');
  const end = source.indexOf('\n  useEffect(', start);
  const rows = new Map([['old', { id: 'old' }]]);
  const state = { id: 'old', errors: [] };
  const context = {
    runSessionChange: async (fn) => { try { return await fn(); } catch(e) { state.errors.push(e.message); } },
    resetSession: () => { state.id = 'new'; },
    saveTimerRef: { current: null }, currentSession: { id: 'old', createdAt: 1 },
    clearTimeout, serialize: () => ({ nodes: [], active: 'root' }),
    deriveSessionTitle: () => 'fixture', sessId: () => 'new', ROOT: {},
    pastRef: { current: [] }, futureRef: { current: [] }, firstSave: { current: false },
    _seq: 0, setCurrentSession: (v) => { state.id = v.id; },
    setDrafts() {}, setQuotes() {}, setAttachments() {}, setNodes() {}, setActive() {}, setSel() {}, setShowSessions() {},
    reloadSessionList() {}, setSessionFolder() {}, setSessionTitles() {},
    loadState() {},
    idb: {
      put: async (row) => { if (failSave) throw Error('fixture storage full'); rows.set(row.id, row); },
      del: async (id) => { if (failDelete) throw Error('fixture delete failed'); rows.delete(id); },
      get: async (id) => rows.get(id),
    },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end) + '\nglobalThis.handlers = { newSession, openSession, deleteSession };', context);
  return { ...context.handlers, rows, state };
}

test('deleting active session never saves it again', async () => {
  const h = handlers(); await h.deleteSession('old');
  assert.equal(h.rows.has('old'), false);
  assert.equal(h.state.id, 'new');
});
test('failed save retains current session', async () => {
  const h = handlers({ failSave: true }); await h.newSession();
  assert.equal(h.state.id, 'old'); assert.equal(h.state.errors.length, 1);
});
test('failed deletion retains current session and metadata', async () => {
  const h = handlers({ failDelete: true }); await h.deleteSession('old');
  assert.equal(h.state.id, 'old'); assert.equal(h.rows.has('old'), true);
  assert.equal(h.state.errors.length, 1);
});

import { createSessionGate } from './session-gate.js';
test('pending reply blocks conversation replacement, then releases after failure', async () => {
  const gate = createSessionGate();
  let reject;
  const request = gate.request(() => new Promise((_, no) => { reject = no; }));
  let changed = false;
  await assert.rejects(gate.change(() => { changed = true; }), /Wait/);
  assert.equal(changed, false);
  reject(new Error('fixture request failed'));
  await assert.rejects(request, /fixture/);
  await gate.change(() => { changed = true; });
  assert.equal(changed, true);
});
test('pending session save blocks new requests and overlapping switches', async () => {
  const gate = createSessionGate();
  let resolve;
  const save = gate.change(() => new Promise((yes) => { resolve = yes; }));
  await assert.rejects(gate.request(() => 'wrong conversation'), /Wait/);
  await assert.rejects(gate.change(() => {}), /Wait/);
  resolve(); await save;
  assert.equal(await gate.request(() => 'correct conversation'), 'correct conversation');
});

test('relate-to-origin keeps its text response and uses the existing thread binding',async()=>{
 const source=fs.readFileSync(new URL('./App.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  const relateToOrigin =');const end=source.indexOf('\n  // --- local persistence',start);
 let called, appended;const context={nodes:[{id:'root',parentId:null,messages:[{role:'user',content:'Original'}]},{id:'n1',parentId:'root',messages:[{role:'user',content:'Branch'}]}],currentSession:{id:'saved'},patch(){},toAPIMessages:x=>x,callLLM:async(messages,thread)=>{called={messages,thread};return {text:'Connects to the original question.',assessmentRefs:[],fromGateway:true};},append:(id,message)=>appended={id,message}};
 vm.createContext(context);vm.runInContext(source.slice(start,end)+'\nglobalThis.relate=relateToOrigin;',context);await context.relate('n1','focus');assert.equal(called.thread,'saved:n1');assert.equal(appended.message.content,'Connects to the original question.');assert.equal(appended.message.relate,true);
});
test('production canvas serializer and loader preserve old saved graph, tabs, attachments and layout',()=>{
 const source=fs.readFileSync(new URL('./App.jsx',import.meta.url),'utf8');const start=source.indexOf('  const serialize =');const end=source.indexOf('  const saveToFile =',start);
 const fixture={v:1,active:'n3',drafts:{n3:'unsent draft'},quotes:{},attachments:{},nodes:[{id:'root',depth:0,parentId:null,x:40,y:40,w:360,h:260,messages:[{role:'user',content:'Investigate',files:[{name:'fixture.txt',content:'evidence'}]}]},{id:'n1',depth:1,parentId:'root',sourceQuote:'First branch',x:450,y:40,w:360,h:260,messages:[{role:'assistant',content:'Answer',tabs:{context:'detail',summary:'summary',sources:'source',action:'action'}}]},{id:'n2',depth:1,parentId:'root',x:450,y:350,w:360,h:260,messages:[]},{id:'n3',depth:2,parentId:'n1',synthFrom:['n1','n2'],x:900,y:200,w:360,h:260,messages:[]}]};
 const context={drafts:{},quotes:{},attachments:{},nodes:[],active:null,_seq:0,setNodes:n=>context.nodes=n,setActive:a=>context.active=a,setDrafts:d=>context.drafts=d,setQuotes:q=>context.quotes=q,setAttachments:a=>context.attachments=a};vm.createContext(context);vm.runInContext(source.slice(start,end)+'\nglobalThis.roundtrip=value=>{loadState(value);return serialize();};',context);const result=JSON.parse(JSON.stringify(context.roundtrip(fixture)));assert.equal(result.active,'n3');assert.deepEqual(result.drafts,fixture.drafts);assert.deepEqual(result.nodes.map(({loading,error,...node})=>node),fixture.nodes);assert.equal(context._seq,3);
 for(const invariant of ['const DB_NAME = runtimeKey("netclaw-canvas")','const DB_VER = 2','const SESS_STORE = "sessions"','const KV_STORE = "kv"'])assert.ok(source.includes(invariant));
});
