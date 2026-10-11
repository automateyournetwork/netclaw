import * as vscode from 'vscode';
import { randomUUID,randomBytes } from 'node:crypto';
import { Connection } from '../connection/connect';
import { chatMessage } from '../webview/messages';
import { LocalState } from '../state/local';
import path from 'node:path';

type Saved={conversationId?:string;pendingNonce?:string;operationId?:string;draft?:string;retain?:boolean};
type Operation={operationId:string;state:string;result?:{output?:string};prompt?:string};
const nonce=()=>`${Date.now()}:${randomUUID()}`;
const escape=(text:string)=>text.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export function openChat(context:vscode.ExtensionContext,connection:Connection,avatar=false):vscode.WebviewPanel {
  if(!connection.ready||!connection.identity)throw Error('Connect to an existing installation first.');
  const identity=connection.identity,generation=connection.generation,viewId=randomUUID();
  const key=`chat.v1.${identity.hostId}.${identity.installationId}.${identity.principalId}`;
  const local=new LocalState(path.join(context.storageUri?.fsPath||context.globalStorageUri.fsPath,'conversations'));
  let saved=local.get<Saved>(key,{}),disposed=false,busy=false;
  const panel=vscode.window.createWebviewPanel(avatar?'netclaw.avatar':'netclaw.chat',avatar?'NetClaw Avatar':'NetClaw Chat',vscode.ViewColumn.One,{enableScripts:true,localResourceRoots:[vscode.Uri.joinPath(context.extensionUri,'resources'),vscode.Uri.joinPath(context.extensionUri,'dist')]});
  const scriptNonce=randomBytes(24).toString('base64');
  const css=panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri,'resources/workbench.css'));
  const script=panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri,'resources/chat.js'));
  const avatarScript=panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri,'dist/avatar.js'));
  const avatarAssets=panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri,'resources/pal'));
  panel.webview.html=`<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${panel.webview.cspSource} blob:; connect-src ${panel.webview.cspSource}; style-src ${panel.webview.cspSource}; script-src 'nonce-${scriptNonce}';"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="${css}"></head><body data-view-id="${viewId}"><header><p class="eyebrow">NETCLAW CHAT</p><h1>${escape(connection.profile?.label||'NetClaw')}</h1><p>${escape(identity.harness.type)} · ${escape(identity.installationId)}</p><div class="toolbar"><button id="refresh">Check status</button><button id="new">New conversation</button><button id="cancel">Request cancellation</button></div></header><main><p id="status" role="status" aria-live="polite">Loading owned conversation…</p>${avatar?`<div id="avatar" data-assets="${avatarAssets}"></div>`:''}<section id="transcript" aria-label="Conversation"></section><form id="composer"><label for="prompt">Message to NetClaw</label><textarea id="prompt" rows="5" maxlength="65536" placeholder="Ask your selected NetClaw…"></textarea><fieldset id="context"><legend>Explicitly staged context</legend><div id="contexts"></div></fieldset><label><input id="retain" type="checkbox"> Keep this draft on this editor host</label><p class="hint">NetClaw uses its configured model. Copilot is not required. Selected context may be sent to that model provider.</p><button id="send" type="submit">Send to NetClaw</button></form></main><script nonce="${scriptNonce}" src="${script}"></script>${avatar?`<script nonce="${scriptNonce}" src="${avatarScript}"></script>`:''}</body></html>`;
  const valid=()=>{if(disposed||generation!==connection.generation||!connection.ready)throw Error('Connection changed. Reopen Chat for the intended installation.');};
  const persist=async()=>{valid();await local.update(key,saved);};
  const post=async(value:unknown)=>{if(!disposed)await panel.webview.postMessage({viewId,...value as object});};
  const load=async(initial=false)=>{
    valid();
    if(saved.pendingNonce&&!saved.operationId){
      const result=await connection.call<{data:{operation:Operation|null}}>('operator_resources',{kind:'overview',filters:{query:saved.pendingNonce}});
      if(result.data.operation){saved={...saved,operationId:result.data.operation.operationId};await persist();}
    }
    let requests:Operation[]=[];
    if(saved.conversationId){
      if(saved.operationId)await connection.call('operator_operation_get',{operationId:saved.operationId});
      const history=await connection.call<{data:{requests:Operation[]}}>('operator_snapshot',{domain:'knowledge',resourceId:saved.conversationId});requests=history.data.requests;
    }
    const inventory=await connection.call<{data:{contexts:{id:string;name:string;size:number}[]}}>('operator_snapshot',{domain:'knowledge'});
    valid();await post({type:'state',initial,saved,requests,contexts:inventory.data.contexts,busy});
  };
  panel.webview.onDidReceiveMessage(async value=>{
    const message=chatMessage(value,viewId);if(!message)return;
    try{
      valid();
      if(message.type==='draft'){saved={...saved,retain:message.payload?.retain===true,draft:message.payload?.retain?message.payload.text:undefined};await persist();return;}
      if(busy)return;
      if(message.type==='ready'||message.type==='refresh'){await load(message.type==='ready');return;}
      busy=true;
      if(message.type==='new'){
        if(saved.pendingNonce){const choice=await vscode.window.showWarningMessage('A previous request may still be running. A new conversation will not cancel it.',{modal:true},'Start another conversation');if(choice!=='Start another conversation')return;}
        const opened=await connection.call<{conversationId:string}>('operator_conversation_open',{nonce:nonce(),view:'chat'});saved={conversationId:opened.conversationId,retain:saved.retain};await persist();
      }
      if(message.type==='cancel'&&saved.operationId)await connection.call('operator_cancel_request',{nonce:nonce(),operationId:saved.operationId});
      if(message.type==='send'){
        if(saved.pendingNonce){if(!saved.operationId)throw Error('Admission is unconfirmed. Check status before sending more work.');const state=await connection.call<{state:string}>('operator_operation_get',{operationId:saved.operationId});if(!['succeeded','failed','cancelled','denied','expired'].includes(state.state))throw Error('Check the unresolved request before sending more work.');}
        if(!saved.conversationId){const opened=await connection.call<{conversationId:string}>('operator_conversation_open',{nonce:nonce(),view:'chat'});saved={...saved,conversationId:opened.conversationId};}
        saved={...saved,pendingNonce:nonce(),operationId:undefined};await persist();
        const admitted=await connection.call<Operation>('operator_request_submit',{nonce:saved.pendingNonce,conversationId:saved.conversationId,prompt:message.payload!.text,contextIds:message.payload?.contextIds||[]});
        saved={...saved,operationId:admitted.operationId,draft:undefined};await persist();await post({type:'sent'});
      }
      busy=false;await load(message.type==='new');
    }catch(error){await post({type:'error',message:error instanceof Error?error.message:'Request unavailable. Check status; do not resend uncertain work.'});}
    finally{busy=false;}
  });
  const timer=setInterval(()=>{if(!busy&&!disposed&&saved.operationId&&generation===connection.generation)void load().catch(()=>{});},2500);
  panel.onDidDispose(()=>{disposed=true;clearInterval(timer);});return panel;
}
