(() => {
  'use strict';
  const api=acquireVsCodeApi(),viewId=document.body.dataset.viewId,post=window.netclawPost(api,viewId),el=id=>document.getElementById(id);
  let info,record,busy=true,invalidated=false,expiry=0;
  const clear=()=>{el('qr').hidden=true;el('qr-canvas').width=el('qr-canvas').height=0;expiry=0;};
  const buttons=()=>{el('generate').disabled=busy||invalidated||!info?.available||record?.status==='unknown';el('check').disabled=busy||invalidated||!record;el('refresh').disabled=busy||invalidated;el('generate').textContent=record&&record.status!=='unknown'?'Generate new QR code':'Generate QR code';};
  const message=()=>!info?.available?'Mobile enrollment is not ready on this Border. Check its trusted mobile listener setup.':({unknown:'The request may have been accepted. Check its status before generating another code.',issued:expiry?'Scan this code with NetClaw Mobile.':'The QR is not stored. Check status, then deliberately generate a new code if needed.',consumed:'Device enrolled. Open NetClaw Mobile to connect with its saved key.',expired:'This code expired. Generate a new code when your phone is ready.',replaced:'This code was replaced and can no longer enroll a device.',absent:'No offer was recorded. You can generate a new code.'}[record?.status]||'Generate a code, then scan it with NetClaw Mobile.');
  const request=type=>{if(busy||invalidated)return;busy=true;buttons();if(type==='generate')clear();post(type);};
  el('generate').onclick=()=>request('generate');el('check').onclick=()=>request('check');el('refresh').onclick=()=>request('refresh');
  document.addEventListener('visibilitychange',()=>{if(document.hidden){clear();post('hide');}});
  window.addEventListener('message',event=>{
    const m=event.data;if(m?.viewId!==viewId||invalidated)return;
    if(m.type==='error'&&m.invalidated){invalidated=true;clear();el('status').textContent='Connection changed. Reopen Mobile for the selected Border.';buttons();return;}
    if(m.type==='busy'){busy=m.busy===true;buttons();return;}
    if(m.type==='clearQr'){clear();el('status').textContent=message();return;}
    if(m.type==='notice'||m.type==='error'){clear();el('status').textContent=m.message||'Enrollment is unavailable.';buttons();return;}
    if(m.type==='state'){info=m.info;record=m.record;if(record?.status!=='issued')clear();el('destination').textContent=info?.available?`${info.endpoint.claw_domain} · ${info.mode==='protected'?'Protected operations':'Local Border'} · ${info.installation_id}`:'';el('status').textContent=message();buttons();return;}
    if(m.type==='qr'){
      if(document.hidden){clear();return;}
      const a=m.matrix,n=a?.length;if(!Array.isArray(a)||n<21||n>177||(n-21)%4!==0||a.some(r=>!Array.isArray(r)||r.length!==n||r.some(b=>typeof b!=='boolean'))||!Number.isSafeInteger(m.expires_ms)||m.expires_ms<=Date.now()){clear();return;}
      const c=el('qr-canvas'),scale=Math.max(2,Math.floor(360/(n+8))),width=(n+8)*scale;c.width=c.height=width;
      const ctx=c.getContext('2d');if(!ctx){clear();el('status').textContent='QR drawing unavailable. Check the offer status.';return;}
      ctx.fillStyle='#fff';ctx.fillRect(0,0,width,width);ctx.fillStyle='#000';a.forEach((r,y)=>r.forEach((bit,x)=>{if(bit)ctx.fillRect((x+4)*scale,(y+4)*scale,scale,scale);}));expiry=m.expires_ms;el('qr').hidden=false;el('status').textContent=message();return;
    }
    if(m.type==='inventoryError'){el('inventory-status').textContent=m.message;return;}
    if(m.type==='inventory'){el('devices').replaceChildren();el('inventory-status').textContent=m.data?.available===false?'The Border did not report device inventory.':'Reported by the selected Border.';const rows=Array.isArray(m.data?.edgeNodes)?m.data.edgeNodes:[];for(const row of rows){const article=document.createElement('article'),name=document.createElement('strong'),state=document.createElement('p');name.textContent=row.display_name||row.member_id||'Unnamed mobile device';state.textContent=`${row.status||row.state||'State not reported'} · ${row.member_id||''}`;article.append(name,state);el('devices').append(article);}if(!rows.length){const p=document.createElement('p');p.textContent=m.data?.available===false?'Device inventory unavailable.':'No mobile devices reported.';el('devices').append(p);}}
  });
  let polls=0;setInterval(()=>{if(record?.status==='issued'&&record.expires_ms>Date.now()&&!document.hidden&&!busy&&!invalidated&&++polls%3===0)request('check');if(!expiry)return;const remaining=Math.max(0,Math.ceil((expiry-Date.now())/1000));el('expiry').textContent=`Expires in ${remaining} seconds`;if(!remaining){clear();el('status').textContent='This code expired. Check status, then generate a new code when ready.';}},1000);
  buttons();post('ready');
})();
