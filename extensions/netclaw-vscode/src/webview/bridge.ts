import * as vscode from 'vscode';
import { randomBytes,randomUUID } from 'node:crypto';
import { Connection } from '../connection/connect';

export interface ViewDefinition {title:string;kind:string;load:()=>Promise<unknown>}
const escape=(text:string):string=>text.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export function openDataView(context:vscode.ExtensionContext,connection:Connection,view:ViewDefinition):vscode.WebviewPanel {
  const panel=vscode.window.createWebviewPanel(`netclaw.${view.kind}`,view.title,vscode.ViewColumn.One,{enableScripts:true,localResourceRoots:[vscode.Uri.joinPath(context.extensionUri,'resources')]});
  const nonce=randomBytes(24).toString('base64'),viewId=randomUUID(),generation=connection.generation;
  const css=panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri,'resources','workbench.css'));
  panel.webview.html=`<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${panel.webview.cspSource}; style-src ${panel.webview.cspSource}; script-src 'nonce-${nonce}';"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="${css}"></head><body><header><p class="eyebrow">NETCLAW</p><h1>${escape(view.title)}</h1><p id="binding">${escape(connection.profile?.label||'Disconnected')} · ${escape(connection.identity?.harness.type||'No runtime')}</p><button id="refresh" type="button">Refresh</button></header><main><p id="status" role="status" aria-live="polite">Loading…</p><div id="content"></div></main><script nonce="${nonce}">
    const vscode=acquireVsCodeApi();const viewId=${JSON.stringify(viewId)};let count=0;
    document.getElementById('refresh').addEventListener('click',()=>vscode.postMessage({type:'refresh',viewId,requestId:String(++count)}));
    function render(value,parent){
      if(value===null||typeof value!=='object'){const span=document.createElement('span');span.textContent=value===null?'Unknown':String(value);parent.appendChild(span);return;}
      if(Array.isArray(value)){if(!value.length){const p=document.createElement('p');p.textContent='No entries in this observed result.';parent.appendChild(p);}value.forEach(item=>{const card=document.createElement('article');render(item,card);parent.appendChild(card);});return;}
      const dl=document.createElement('dl');for(const [key,item] of Object.entries(value)){const dt=document.createElement('dt');dt.textContent=key.replace(/([a-z])([A-Z])/g,'$1 $2');const dd=document.createElement('dd');render(item,dd);dl.append(dt,dd);}parent.appendChild(dl);
    }
    window.addEventListener('message',event=>{const m=event.data;if(m.viewId!==viewId)return;document.getElementById('status').textContent=m.error||'Observed result';const container=document.getElementById('content');container.replaceChildren();if(!m.error)render(m.data,container);});
  </script></body></html>`;
  let disposed=false,loading=false;
  const load=async()=>{if(loading||disposed)return;loading=true;try{if(connection.generation!==generation)throw Error('Connection changed. Reopen this view for the selected installation.');const data=await view.load();if(connection.generation!==generation)return;await panel.webview.postMessage({viewId,data});}catch(error){await panel.webview.postMessage({viewId,error:error instanceof Error?error.message:'Source unavailable'});}finally{loading=false;}};
  panel.webview.onDidReceiveMessage((message:unknown)=>{
    if(!message||typeof message!=='object')return;const m=message as Record<string,unknown>;
    if(Object.keys(m).sort().join(',')!=='requestId,type,viewId'||m.type!=='refresh'||m.viewId!==viewId||typeof m.requestId!=='string'||m.requestId.length>100)return;
    if(!vscode.workspace.isTrusted||connection.generation!==generation)return;void load();
  });
  panel.onDidDispose(()=>{disposed=true;});void load();return panel;
}
