import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { JSDOM, VirtualConsole } from 'jsdom';
const output = await build({ entryPoints: [new URL('./main.jsx',import.meta.url).pathname], bundle:true, write:false, outfile:'ui.js', format:'iife', define:{'process.env.NODE_ENV':'"production"'} });
const js=output.outputFiles.find(f=>f.path.endsWith('.js')).text;
const settle=()=>new Promise(resolve=>setTimeout(resolve,30));
async function app(t, preview=true, fetcher){const errors=[];const virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',e=>errors.push(e.message));const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost:3000',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole});dom.window.NETCLAW_PREVIEW=preview;if(fetcher)dom.window.fetch=(url,options)=>url==='/api/runtime'?Promise.resolve({ok:true,json:async()=>({kind:'openclaw',installationId:'11111111-1111-4111-8111-111111111111',label:'OpenClaw',readiness:{ready:true},capabilities:{}})}):fetcher(url,options);dom.window.AbortSignal=AbortSignal;dom.window.AbortController=AbortController;dom.window.eval(js);t.after(()=>dom.window.close());await settle();return {document:dom.window.document,window:dom.window,errors};}
function click(document,label){const button=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===label || b.textContent.trim().startsWith(label));assert.ok(button,`button ${label}`);button.click();}
test('sending from Avatar unlocks voice before the request and speaks only a safe notice',async t=>{
  const calls=[],order=[];let finish;
  const {document,window,errors}=await app(t,false,async(url,options={})=>{
    calls.push([url,options]);
    if(url==='/api/chat'){order.push('chat');return await new Promise(resolve=>{finish=()=>resolve({ok:true,json:async()=>({fromGateway:true,response:'Private network answer 10.1.2.3'})});});}
    if(url==='/api/pal/local/speech')return {ok:true,arrayBuffer:async()=>new ArrayBuffer(44)};
    return {ok:true,json:async()=>url==='/api/pal/local/status'?{available:true,maxCharacters:1800}:url==='/api/chat/models'?{models:[]}:{}};
  });
  let starts=0;
  window.AudioContext=class {
    state='suspended';destination={};
    createGain(){return {gain:{value:1},connect(){},disconnect(){}};}
    async resume(){order.push('unlock');this.state='running';}
    async close(){} async decodeAudioData(){return {};}
    createBufferSource(){return {connect(){},disconnect(){},start(){starts++;},stop(){}};}
    createAnalyser(){return {connect(){},disconnect(){},getFloatTimeDomainData(array){array.fill(.04);}};}
  };
  click(document,'Avatar');await settle();
  assert.match(document.querySelector('.local-pal-state').textContent,/Voice off/);
  typeChat(window,document,'Check this');await settle();
  document.querySelector('.chat-composer').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await settle();
  assert.deepEqual(order.slice(0,2),['unlock','chat']);
  finish();await settle();await settle();
  const speech=calls.filter(([url])=>url==='/api/pal/local/speech');
  assert.equal(speech.length,1);assert.deepEqual(JSON.parse(speech[0][1].body),{kind:'notice',notice:'ready',rate:1});
  assert.equal(starts,1);assert.match(document.querySelector('.local-pal-state').textContent,/Speaking/);
  document.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await settle();
  assert.match(document.querySelector('.local-pal-state').textContent,/Voice ready/);
  click(document,'Read latest reply');await settle();
  assert.equal(JSON.parse(calls.filter(([url])=>url==='/api/pal/local/speech').at(-1)[1].body).text,'Private network answer 10.1.2.3');
  assert.deepEqual(errors,[]);
});
test('local Pal shares the Chat draft and thread; avatar choice never starts Tavus or sends a model request',async t=>{
  const calls=[];
  const {document,window,errors}=await app(t,false,async(url,options={})=>{
    calls.push([url,options]);return {ok:true,json:async()=>url==='/api/pal/local/status'?{available:true,maxCharacters:1800}:url==='/api/chat/models'?{models:[]}:{}};
  });
  typeChat(window,document,'Keep this question while I choose a Pal');await settle();
  const chat=document.querySelector('.standard-chat');
  click(document,'Avatar');await settle();
  assert.deepEqual([...document.querySelector('[aria-label="Chat interface"]').querySelectorAll('button,a')].map(node=>node.textContent),['Chat','Canvas','OpenClaw ↗','Avatar']);
  assert.equal([...document.querySelectorAll('nav button')].some(button=>/Avatar|Pal/.test(button.textContent)),false);
  assert.equal(document.querySelector('.standard-chat'),chat);
  assert.equal(document.querySelectorAll('#standard-chat-message').length,1);
  assert.equal(document.querySelector('#standard-chat-message').value,'Keep this question while I choose a Pal');
  const lobster=[...document.querySelectorAll('[aria-label="Avatar selection"] button')].find(button=>button.textContent.includes('Lobster'));
  assert.ok(lobster);lobster.click();await settle();
  assert.equal(lobster.getAttribute('aria-pressed'),'true');
  assert.equal(window.localStorage.getItem('nc-pal-avatar-v1'),'lobster');
  click(document,'00Chat');await settle();
  assert.equal(document.querySelector('.standard-chat'),chat);
  assert.equal(document.querySelector('#standard-chat-message').value,'Keep this question while I choose a Pal');
  assert.equal(calls.some(([url])=>url==='/api/chat'||url==='/api/pal/sessions'||url==='/api/pal/status'),false);
  assert.deepEqual(errors,[]);
});
test('production dashboard renders and Basic/Advanced retains navigation without errors',async t=>{const {document,errors}=await app(t);assert.match(document.body.textContent,/SYNTHETIC PREVIEW/);assert.match(document.querySelector('h1').textContent,/^Chat/);click(document,'01Overview');await settle();assert.match(document.body.textContent,/Execution members/);click(document,'Advanced');await settle();assert.equal(document.querySelector('button[aria-pressed=true]').textContent,'Advanced');for(const label of ['Risk of Claws','External neighbours','Mobile devices','Science Officer','Network','Knowledge','Operations','Integrations','Settings','RAG','Configuration','Canvas','Tokenomics','Documentation','Logs','Security']){const button=[...document.querySelectorAll('nav button')].find(b=>b.textContent.includes(label));assert.ok(button,label);button.click();await settle();assert.match(document.querySelector('h1').textContent,new RegExp(label));}assert.deepEqual(errors,[]);});
test('member inspector uses exact identity; Three.js not required for selection',async t=>{const {document,errors}=await app(t);click(document,'03Risk of Claws');await settle();document.querySelector('button[aria-label="Inspect Network Claw"]').click();await settle();assert.match(document.querySelector('.inspector').textContent,/demo\/network/);assert.match(document.querySelector('.inspector').textContent,/Execution member/);assert.equal(document.querySelector('canvas'),null);assert.deepEqual(errors,[]);});
test('typed assessment comparison shows Noul probability, Choice answer and Score separately',async t=>{const {document,errors}=await app(t);click(document,'06Science Officer');await settle();click(document,'Inspect synthetic original');await settle();assert.equal(document.querySelectorAll('.assessment').length,2);assert.match(document.body.textContent,/0.72/);assert.match(document.body.textContent,/interfaces/);assert.match(document.body.textContent,/Rubric position/);assert.match(document.body.textContent,/not network health/);assert.match(document.body.textContent,/Border's interpretation/);assert.deepEqual(errors,[]);});

test('Canvas tab mounts real canvas.html once and preserves iframe across navigation and mode changes',async t=>{
  const {document,errors}=await app(t,false,async()=>({ok:true,json:async()=>({})}));
  click(document,'02Canvas');await settle();const frame=document.querySelector('iframe');
  assert.ok(frame);assert.equal(frame.getAttribute('src'),'/canvas.html?embedded=1');
  assert.equal(document.querySelector('.canvas-workspace').hidden,false);
  click(document,'01Overview');await settle();assert.equal(document.querySelector('.canvas-workspace').hidden,true);
  click(document,'Advanced');await settle();click(document,'02Canvas');await settle();
  assert.equal(document.querySelector('iframe'),frame);assert.equal(document.querySelector('.canvas-workspace').hidden,false);
  assert.ok(document.querySelector('a[href="/canvas.html"]'));assert.doesNotMatch(document.body.textContent,/Adam's/);assert.deepEqual(errors,[]);
});
test('RAG and configuration are available in Basic; preview never uploads or reads credentials',async t=>{
  const {document,errors}=await app(t);
  click(document,'12RAG');await settle();assert.match(document.body.textContent,/Collections & ingestion/);
  assert.equal(document.querySelector('input[type=file]').disabled,true);
  assert.match(document.body.textContent,/Branch routing runbook/);
  click(document,'13Configuration');await settle();assert.match(document.body.textContent,/TYPESAFE_API_KEY/);
  assert.match(document.body.textContent,/Values stay masked/);assert.deepEqual(errors,[]);
});
test('RAG retrieval uses selected collection and passes cited results to Canvas draft review',async t=>{
  const calls=[];
  const fetcher=async(url,options={})=>{calls.push([url,options]);return {ok:true,json:async()=>url==='/api/rag/search'?{collection:'documents',results:[{chunk_id:'c1',title:'Runbook',chunk_text:'Check counters',citation:'[Runbook p.2]',score:0.8}]}:url==='/api/rag/documents'?{documents:[],snapshots:[],replicas:[]}:url==='/api/rag/stats'?{collections:['documents']}: {}};};
  const {document,window,errors}=await app(t,false,fetcher);click(document,'12RAG');await settle();
  const input=document.querySelector('textarea');Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set.call(input,'routing');input.dispatchEvent(new window.Event('input',{bubbles:true}));await settle();
  input.closest('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await settle();
  const request=calls.find(([url])=>url==='/api/rag/search');assert.ok(request);assert.deepEqual(JSON.parse(request[1].body),{query:'routing',collection:'documents',k:5});
  assert.match(document.body.textContent,/Runbook p.2/);click(document,'Use evidence in Canvas');await settle();
  assert.match(document.querySelector('.context-review').textContent,/Runbook p.2/);assert.match(document.querySelector('h1').textContent,/Canvas/);assert.deepEqual(errors,[]);
});
test('RAG upload submits multipart fields and treats 202 as pending rather than ready',async t=>{
  const calls=[];const fetcher=async(url,options={})=>{calls.push([url,options]);return {ok:true,json:async()=>url==='/api/rag/upload'?{status:'pending'}:url==='/api/rag/documents'?{documents:[],snapshots:[],replicas:[]}: {}};};
  const {document,window,errors}=await app(t,false,fetcher);click(document,'12RAG');await settle();
  const form=document.querySelector('input[type=file]').closest('form');form.querySelector('[name=title]').value='Upload regression';
  form.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await settle();
  const upload=calls.find(([url])=>url==='/api/rag/upload');assert.ok(upload);assert.equal(upload[1].method,'POST');assert.equal(upload[1].body.get('title'),'Upload regression');assert.equal(upload[1].body.get('doc_type'),'other');assert.ok(upload[1].body.has('file'));assert.equal(upload[1].headers,undefined);assert.match(document.body.textContent,/Ingestion is pending/);assert.deepEqual(errors,[]);
});
test('RAG failures stay visible without reporting empty collections or successful uploads',async t=>{
  const {document,window}=await app(t,false,async url=>({ok:!url.startsWith('/api/rag'),status:503,json:async()=>({})}));click(document,'12RAG');await settle();
  assert.match(document.querySelector('[role=alert]').textContent,/could not complete/);assert.doesNotMatch(document.body.textContent,/No documents reported/);
  document.querySelector('input[type=file]').closest('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await settle();assert.match(document.querySelector('[role=status]').textContent,/could not complete/);assert.doesNotMatch(document.body.textContent,/Upload accepted/);
});

test('Claw inspector shows exact reported MCP tools and model, not generic capabilities',async t=>{
  const {document}=await app(t);click(document,'03Risk of Claws');await settle();document.querySelector('button[aria-label="Inspect Network Claw"]').click();await settle();const detail=document.querySelector('.inspector');assert.match(detail.textContent,/example\/network-model/);assert.match(detail.textContent,/pyats_run_show_command/);assert.match(detail.textContent,/tool list not reported/);
});
test('Tokenomics distinguishes recorded usage, heuristics, cache and separate Jev budgets',async t=>{
  const {document}=await app(t);click(document,'14Tokenomics');await settle();assert.match(document.body.textContent,/42,000/);assert.match(document.body.textContent,/Cache read/);assert.match(document.body.textContent,/\$0.17 per assistant turn/);assert.match(document.body.textContent,/not added together/);
});
test('Documentation includes Sean guide, CLI flags, MCP reference and real OpenAPI routes',async t=>{
  const {document}=await app(t);click(document,'15Documentation');await settle();assert.ok(document.querySelector('a[href="https://www.seanmahoney.ai/guides/netclaw-overview/"]'));click(document,'CLI reference');await settle();assert.match(document.body.textContent,/scripts\/netclaw/);assert.match(document.body.textContent,/--edge/);click(document,'MCP reference');await settle();assert.match(document.body.textContent,/rag_search/);click(document,'HTTP API');await settle();assert.match(document.body.textContent,/GET \/api\/hud\/logs/);
});
test('Logs filters synthetic tail and hands exact selected evidence to Canvas without executing commands',async t=>{
  const {document,window}=await app(t);click(document,'16Logs');await settle();const select=[...document.querySelectorAll('select')].find(s=>s.textContent.includes('warning'));select.value='warning';select.dispatchEvent(new window.Event('change',{bubbles:true}));await settle();assert.equal(document.querySelectorAll('tbody tr').length,1);assert.match(document.querySelector('tbody').textContent,/heartbeat delayed/);click(document,'Investigate ↗');await settle();assert.match(document.querySelector('.context-review').textContent,/heartbeat delayed/);assert.match(document.querySelector('h1').textContent,/Canvas/);
});

test('Overview labels LAB separately and Security distinguishes DefenseClaw, OpenShell and host confinement',async t=>{
  const {document}=await app(t);click(document,'01Overview');await settle();assert.match(document.body.textContent,/LAB bypass enabled/);click(document,'Inspect Security');await settle();assert.match(document.body.textContent,/Host member confinement/);assert.match(document.body.textContent,/OpenShell is not required/);assert.match(document.body.textContent,/Observe mode/);click(document,'DefenseClaw logs');await settle();assert.equal(document.querySelector('select').value,'defenseclaw');assert.match(document.body.textContent,/tail -n 200 ~\/\.defenseclaw\/gateway.log/);
});

function typeChat(window, document, value) {
  const input = document.querySelector('#standard-chat-message');
  Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set.call(input,value);
  input.dispatchEvent(new window.Event('input',{bubbles:true}));
}
function submitChat(window, document) {
  document.querySelector('.chat-composer').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));
}
test('Chat is default; native OpenClaw opens separately and Canvas and Chat drafts survive navigation',async t=>{
  const {document,window,errors}=await app(t,false,async url=>({ok:true,json:async()=>url==='/api/hud/runtime'?{controlUi:{available:true,port:19443,basePath:'/ops',tls:true}}:{}}));
  assert.match(document.querySelector('h1').textContent,/^Chat/);
  typeChat(window,document,'Unsent private question');await settle();
  const link=document.querySelector('.chat-switch a');assert.equal(link.href,'https://127.0.0.1:19443/ops/');assert.equal(link.target,'_blank');assert.match(link.rel,/noopener/);assert.match(link.rel,/noreferrer/);assert.equal(link.getAttribute('referrerpolicy'),'no-referrer');
  click(document,'02Canvas');await settle();const frame=document.querySelector('iframe');assert.ok(frame);
  link.addEventListener('click',e=>e.preventDefault());link.click();await settle();assert.equal(document.querySelector('iframe'),frame);
  click(document,'Advanced');click(document,'00Chat');await settle();assert.equal(document.querySelector('#standard-chat-message').value,'Unsent private question');
  click(document,'02Canvas');await settle();assert.equal(document.querySelector('iframe'),frame);assert.deepEqual(errors,[]);
});
test('standard Chat bootstraps scoped session, sends isolated chronological turns and retains response while hidden',async t=>{
  const calls=[];let deliver;const reply=new Promise(resolve=>deliver=resolve);
  const {document,window,errors}=await app(t,false,async(url,options={})=>{calls.push([url,options]);if(url==='/api/chat')return reply;return{ok:true,json:async()=>({})};});
  typeChat(window,document,'First question');await settle();submitChat(window,document);submitChat(window,document);await settle();
  assert.equal(calls.filter(([url])=>url==='/api/chat').length,1);
  assert.ok(calls.findIndex(([url])=>url==='/api/hud/session')<calls.findIndex(([url])=>url==='/api/chat'));
  const body=JSON.parse(calls.find(([url])=>url==='/api/chat')[1].body);assert.match(body.hudThread,/^chat-/);assert.deepEqual(body.messages,[{role:'user',content:'First question'}]);
  assert.equal([...document.querySelectorAll('button')].find(b=>b.textContent==='New chat').disabled,true);
  click(document,'02Canvas');await settle();const frame=document.querySelector('iframe');
  deliver({ok:true,json:async()=>({fromGateway:true,response:'Verified synthetic response <img src=x onerror=alert(1)>',assessmentRefs:[{taskRef:'owned-task',assessmentId:'owned-assessment'},{taskRef:'bad/../../',assessmentId:'unsafe'}]})});await settle();
  click(document,'00Chat');await settle();assert.equal(document.querySelectorAll('.chat-message').length,2);assert.equal(document.querySelector('.chat-message img'),null);assert.match(document.querySelector('.chat-message.assistant').textContent,/Verified synthetic/);
  assert.equal(document.querySelector('.chat-message.assistant a').getAttribute('href'),'/assessment.html?task=owned-task&assessment=owned-assessment');assert.equal(document.querySelectorAll('.chat-message.assistant a').length,1);
  assert.equal(document.querySelector('iframe'),frame);assert.equal(calls.some(([url])=>url==='/api/chat/history'),false);assert.deepEqual(errors,[]);
});
test('failed bootstrap, HTTP failure, gateway fallback and empty replies restore drafts without fabricated assistant messages',async t=>{
  for(const mode of ['bootstrap','http','fallback','empty','network']){
    const calls=[];const {document,window}=await app(t,false,async(url,options)=>{calls.push(url);if(url==='/api/hud/session')return {ok:mode!=='bootstrap'};if(url==='/api/chat'){if(mode==='network')throw new window.TypeError('private transport detail');return{ok:mode!=='http',status:503,json:async()=>({fromGateway:mode!=='fallback',response:mode==='empty'?'':'UNVERIFIED FALLBACK'})};}return{ok:true,json:async()=>({})};});
    typeChat(window,document,'Retain this draft');await settle();submitChat(window,document);await settle();
    assert.equal(document.querySelector('#standard-chat-message').value,'Retain this draft',mode);assert.equal(document.querySelectorAll('.chat-message.assistant').length,0,mode);assert.ok(document.querySelector('[role=alert]'),mode);assert.doesNotMatch(document.querySelector('[role=alert]').textContent,/UNVERIFIED|private transport/);
    assert.equal(calls.filter(url=>url==='/api/chat').length,mode==='bootstrap'?0:1,mode);
  }
});
test('new chat archives history and previous chat restores its original context',async t=>{
  const sent=[];const {document,window}=await app(t,false,async(url,options)=>{if(url==='/api/chat'){sent.push(JSON.parse(options.body));return{ok:true,json:async()=>({fromGateway:true,response:'Synthetic answer'})};}return{ok:true,json:async()=>({})};});
  for(const question of ['One','Two']){typeChat(window,document,question);await settle();submitChat(window,document);await settle();}
  assert.equal(sent[0].hudThread,sent[1].hudThread);assert.equal(sent[1].messages.length,3);
  click(document,'New chat');await settle();assert.equal(document.querySelectorAll('.chat-message').length,0);
  const picker=document.querySelector('#previous-chat');picker.value=`local:${sent[0].hudThread}`;picker.dispatchEvent(new window.Event('change',{bubbles:true}));await settle();
  assert.equal(document.querySelectorAll('.chat-message').length,4);
  click(document,'New chat');await settle();
  typeChat(window,document,'Fresh');await settle();submitChat(window,document);await settle();assert.notEqual(sent[2].hudThread,sent[1].hudThread);assert.deepEqual(sent[2].messages,[{role:'user',content:'Fresh'}]);
});
test('native switch remains disabled for failed runtime reads and synthetic preview never sends',async t=>{
  const {document}=await app(t,false,async url=>({ok:url!=='/api/hud/runtime',json:async()=>({})}));assert.equal(document.querySelector('.chat-switch a'),null);assert.equal(document.querySelector('.chat-unavailable button').disabled,true);
  const preview=await app(t);assert.equal(preview.document.querySelector('#standard-chat-message').disabled,true);assert.equal(preview.document.querySelector('.chat-switch a'),null);assert.match(preview.document.querySelector('.chat-transcript').textContent,/Synthetic example/);
});
test('composer Enter sends but Shift+Enter and IME composition do not',async t=>{
  const sent=[];const {document,window}=await app(t,false,async(url,options)=>{if(url==='/api/chat')sent.push(JSON.parse(options.body));return{ok:true,json:async()=>url==='/api/chat'?{fromGateway:true,response:'Synthetic answer'}:{}};});
  typeChat(window,document,'Keyboard question');await settle();const input=document.querySelector('#standard-chat-message');
  input.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',shiftKey:true,bubbles:true,cancelable:true}));
  input.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',isComposing:true,bubbles:true,cancelable:true}));await settle();assert.equal(sent.length,0);
  input.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));await settle();assert.equal(sent.length,1);
});


test('Avatar quiet preference survives switching views and never starts automatic speech',async t=>{
  const speech=[];
  const {document,window,errors}=await app(t,false,async(url,options={})=>{
    if(url==='/api/pal/local/speech')speech.push(options);
    return {ok:true,json:async()=>url==='/api/pal/local/status'?{available:true,maxCharacters:1800}:url==='/api/chat'?{fromGateway:true,response:'Saved answer'}:url==='/api/chat/models'?{models:[]}:{}};
  });
  click(document,'Avatar');await settle();
  const select=document.querySelector('#local-pal-autospeak');select.value='off';select.dispatchEvent(new window.Event('change',{bubbles:true}));await settle();
  click(document,'00Chat');await settle();click(document,'Avatar');await settle();
  assert.equal(document.querySelector('#local-pal-autospeak').value,'off');
  typeChat(window,document,'A quiet question');await settle();
  document.querySelector('.chat-composer').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await settle();
  assert.match(document.querySelector('.chat-transcript').textContent,/Saved answer/);
  assert.equal(speech.length,0);assert.match(document.querySelector('.local-pal-state').textContent,/Voice off/);
  click(document,'00Chat');await settle();click(document,'Avatar');await settle();
  assert.ok([...document.querySelectorAll('button')].find(button=>button.textContent==='Read latest reply'));
  assert.equal(speech.length,0);assert.deepEqual(errors,[]);
});
