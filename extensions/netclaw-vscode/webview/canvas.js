import {branchSeed} from '../../../ui/netclaw-visual/src/canvas-chat/branch-context.js';
const api=acquireVsCodeApi(),viewId=document.body.dataset.viewId;
let documentState={v:1,nodes:[]},requests={},sequence=0,contexts=[],selectedContexts={};
const el=id=>document.getElementById(id);
const post=(type,extra={})=>api.postMessage({viewId,requestId:String(++sequence),type,...(type==='ready'?{}:{document:documentState}),...extra});
for(const id of ['save','open','import','export','refresh'])el(id).addEventListener('click',()=>post(id));
const text=(tag,value,parent)=>{const element=document.createElement(tag);element.textContent=value;parent.append(element);return element;};
function render(){
  el('lanes').replaceChildren();
  for(const node of documentState.nodes){
    const lane=document.createElement('article');lane.className='canvas-lane';lane.dataset.node=node.id;el('lanes').append(lane);
    text('h2',node.title||'Conversation',lane);
    if(node.sourceQuote)text('blockquote',node.sourceQuote,lane);
    if(node.seedContext?.length){const details=document.createElement('details');text('summary','Selected ancestor context',details);text('pre',node.seedContext.map(m=>`${m.role}: ${m.content}`).join('\n\n'),details);lane.append(details);}
    for(const message of node.messages||[])text('pre',`${message.role}: ${message.content}`,lane);
    if(node.kind&&!['chat'].includes(node.kind)){text('p','Imported reference lane. Original content is retained for export; execution is unavailable here.',lane);continue;}
    const branch=text('button','Branch this conversation',lane);branch.addEventListener('click',()=>{
      const quote=window.getSelection()?.toString()||'';
      documentState.nodes.push({id:crypto.randomUUID(),kind:'chat',title:'Branch',parentId:node.id,depth:(node.depth||0)+1,sourceQuote:quote,seedContext:branchSeed(documentState.nodes,node.id,quote),messages:[]});render();post('state');
    });
    const label=text('label','Message',lane),input=document.createElement('textarea');input.rows=4;input.value=documentState.drafts?.[node.id]||'';input.id='draft-'+node.id;label.htmlFor=input.id;lane.append(input);
    input.addEventListener('input',()=>{documentState.drafts={...(documentState.drafts||{}),[node.id]:input.value};post('state');});
    const contextBox=document.createElement('fieldset');text('legend','Selected context for this request',contextBox);lane.append(contextBox);
    for(const context of contexts){
      const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.checked=(selectedContexts[node.id]||[]).includes(context.id);label.append(check,document.createTextNode(context.name));contextBox.append(label);
      check.addEventListener('change',()=>{const ids=new Set(selectedContexts[node.id]||[]);if(check.checked)ids.add(context.id);else ids.delete(context.id);selectedContexts[node.id]=[...ids];});
    }
    if(!contexts.length)text('p','Add selected editor text or cited RAG results to make context available.',contextBox);
    const submit=text('button','Send in this lane',lane),status=text('p',requests[node.id]?.state||'Ready',lane);status.setAttribute('role','status');
    submit.disabled=Boolean(requests[node.id]&&!['succeeded','failed','cancelled','denied','expired'].includes(requests[node.id].state));
    submit.addEventListener('click',()=>{if(!input.value.trim())return;submit.disabled=true;status.textContent='Admitting request…';post('send',{nodeId:node.id,text:input.value,contextIds:selectedContexts[node.id]||[]});});
  }
}
window.addEventListener('message',event=>{
  const m=event.data;if(m.viewId!==viewId)return;
  if(m.type==='document'){documentState=m.document;render();el('status').textContent='Save investigation to retain changes across reloads. Branching and switching views do not send prompts.';}
  if(m.type==='notice')el('status').textContent=m.message;
  if(m.type==='contexts'&&JSON.stringify(contexts)!==JSON.stringify(m.contexts)){contexts=m.contexts;render();}
  if(m.type==='admitted'){const node=documentState.nodes.find(n=>n.id===m.nodeId);if(node){node.messages=[...(node.messages||[]),{role:'user',content:m.prompt,operationId:m.operationId}];documentState.drafts={...(documentState.drafts||{}),[node.id]:''};}render();post('state');}
  if(m.type==='requests'){
    const changed=JSON.stringify(requests)!==JSON.stringify(m.requests);requests=m.requests;
    for(const [nodeId,request] of Object.entries(requests)){
      const node=documentState.nodes.find(n=>n.id===nodeId);
      if(node&&request.prompt&&!node.messages?.some(message=>message.role==='user'&&message.operationId===request.operationId))node.messages=[...(node.messages||[]),{role:'user',content:request.prompt,operationId:request.operationId}];
      if(node&&request.state==='succeeded'&&request.result?.output&&!node.messages?.some(message=>message.role==='assistant'&&message.operationId===request.operationId))node.messages=[...(node.messages||[]),{role:'assistant',content:request.result.output,operationId:request.operationId}];
    }
    if(changed){render();post('state');}
  }
});
post('ready');
