import * as vscode from 'vscode';
import { createHash } from 'node:crypto';
import { Connection } from '../connection/connect';
import { MobileEnrollment } from '../client/mobile';
import { inspect } from '../client/domains';
import { panel } from '../webview/panel';
export function openMobile(context:vscode.ExtensionContext,connection:Connection){
  const p=panel(context,connection,'mobile','Mobile & edge',`<section class="mobile-enrollment"><h2>Enroll mobile device</h2><p>Open NetClaw Mobile, choose <strong>Scan QR code</strong>, and point your camera at the code below.</p><p id="destination"></p><div class="toolbar"><button id="generate" disabled>Generate QR code</button><button id="check" class="secondary" disabled>Check enrollment status</button></div><p id="status" role="status" aria-live="polite">Checking mobile enrollment…</p><div id="qr" class="mobile-qr" hidden><canvas id="qr-canvas" aria-label="One-use mobile enrollment QR code"></canvas><p id="expiry"></p></div><p class="hint">A code enrolls one device and expires after two minutes. Enrolled phones reconnect with their saved key.</p></section><section><div class="toolbar"><h2>Enrolled mobile devices</h2><button id="refresh" class="secondary">Refresh devices</button></div><p id="inventory-status" role="status"></p><div id="devices"></div></section>`,['resources/mobile.js']);
  const id=connection.identity!.installationId,key='mobile-enrollment.'+createHash('sha256').update(p.bound.client.base+'|'+id).digest('hex');
  const enrollment=new MobileEnrollment(p.bound.client,async value=>{await context.workspaceState.update(key,value);},context.workspaceState.get(key));
  let busy=false;
  const postState=async()=>p.post({type:'state',info:enrollment.info,record:enrollment.record});
  const inventory=async()=>{try{const value=await p.bound.run(()=>inspect(p.bound.client,'mobile'));await p.post({type:'inventory',data:value.data});}catch{await p.post({type:'inventoryError',message:'Mobile device inventory is unavailable.'});}};
  p.view.onDidChangeViewState(event=>{if(!event.webviewPanel.visible)void p.post({type:'clearQr'});});
  p.onMessage(['ready','generate','check','refresh','hide'],async message=>{
    if(message.type==='hide'){await p.post({type:'clearQr'});return;}
    if(busy)return;busy=true;await p.post({type:'busy',busy:true});
    try{
      if(message.type==='ready'){await p.bound.run(()=>enrollment.load());await postState();await inventory();}
      if(message.type==='generate'){const value=await p.bound.run(()=>enrollment.generate());await postState();if(value.qr_matrix&&p.view.visible)await p.post({type:'qr',matrix:value.qr_matrix,expires_ms:value.expires_ms});}
      if(message.type==='check'){await p.bound.run(()=>enrollment.recover());await postState();}
      if(message.type==='refresh')await inventory();
    }catch{
      await postState();await p.post({type:'notice',message:'Enrollment is unavailable. Check the original request before generating another code. Nothing was retried.'});
    }finally{busy=false;await p.post({type:'busy',busy:false});}
  });
  return p.view;
}
