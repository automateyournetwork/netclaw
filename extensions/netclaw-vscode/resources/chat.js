(() => {
  const api=acquireVsCodeApi(),viewId=document.body.dataset.viewId;
  let sequence=0,selected=new Set(),sending=false;
  const el=id=>document.getElementById(id);
  const post=(type,payload)=>api.postMessage({viewId,requestId:String(++sequence),type,...(payload?{payload}:{})});
  for(const id of ['refresh','new','cancel'])el(id).addEventListener('click',()=>post(id));
  const draft=()=>post('draft',{text:el('prompt').value,retain:el('retain').checked});
  let timer;
  el('prompt').addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(draft,350);});
  el('retain').addEventListener('change',draft);
  el('composer').addEventListener('submit',event=>{
    event.preventDefault();if(sending||!el('prompt').value.trim())return;
    sending=true;el('send').disabled=true;el('status').textContent='Admitting request…';
    post('send',{text:el('prompt').value,contextIds:[...selected]});
  });
  const message=(role,text)=>{const article=document.createElement('article'),heading=document.createElement('h2'),body=document.createElement('pre');heading.textContent=role;body.textContent=text;article.append(heading,body);el('transcript').append(article);};
  window.addEventListener('message',event=>{
    const data=event.data;if(data.viewId!==viewId)return;
    if(data.type==='sent'){el('prompt').value='';sending=false;return;}
    if(data.type==='error'){el('status').textContent=data.message;sending=false;el('send').disabled=false;return;}
    if(data.type!=='state')return;
    if(data.initial){el('prompt').value=data.saved.draft||'';el('retain').checked=data.saved.retain===true;}
    el('transcript').replaceChildren();
    for(const request of data.requests){message('You',request.prompt);if(request.result?.output)message('NetClaw',request.result.output);message('Request status',`${request.state} · ${request.operationId}`);}
    const active=data.requests.find(r=>!['succeeded','failed','cancelled','denied','expired'].includes(r.state));
    const lost=data.saved.pendingNonce&&!data.saved.operationId;
    el('send').disabled=Boolean(active||lost||sending);el('cancel').disabled=!active||active.state==='unknown';
    el('status').textContent=lost?'Admission is unconfirmed. Check status; nothing will be resent.':active?`Request ${active.state}. Status checks do not resend it.`:'Ready for an explicit request.';
    el('contexts').replaceChildren();
    for(const context of data.contexts){const label=document.createElement('label'),checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=selected.has(context.id);checkbox.addEventListener('change',()=>{if(checkbox.checked)selected.add(context.id);else selected.delete(context.id);});label.append(checkbox,document.createTextNode(`${context.name} · ${context.size} bytes`));el('contexts').append(label);}
    if(!data.contexts.length)el('contexts').textContent='Use NetClaw: Add Selected Context after selecting text in an editor.';
  });
  post('ready');
})();
