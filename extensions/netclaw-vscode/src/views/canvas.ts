import * as vscode from 'vscode';
import {randomUUID,randomBytes} from 'node:crypto';
import {Connection} from '../connection/connect';
import {LocalState} from '../state/local';
import path from 'node:path';

type Node={id:string;kind?:string;messages?:{role:string;content:string}[];seedContext?:{role:string;content:string}[];[key:string]:unknown};
type Canvas={v:1;nodes:Node[];[key:string]:unknown};
type Binding={conversationId:string;operationId?:string;pendingNonce?:string};
const nonce=()=>`${Date.now()}:${randomUUID()}`;
export function openCanvas(context:vscode.ExtensionContext,connection:Connection):vscode.WebviewPanel{
  if(!connection.ready||!connection.identity)throw Error('Connect to an existing installation first.');
  const generation=connection.generation,identity=connection.identity,viewId=randomUUID();
  const key=`canvas.v1.${identity.hostId}.${identity.installationId}.${identity.principalId}`;
  const local=new LocalState(path.join(context.storageUri?.fsPath||context.globalStorageUri.fsPath,'conversations'));
  let saved=local.get<{id?:string;bindings:Record<string,Binding>}>(key,{bindings:{}}),document:Canvas={v:1,nodes:[{id:'root',title:'Investigation',messages:[],kind:'chat',depth:0}],drafts:{},quotes:{},attachments:{}},busy=false,disposed=false;
  const panel=vscode.window.createWebviewPanel('netclaw.canvas','NetClaw Canvas',vscode.ViewColumn.One,{enableScripts:true,localResourceRoots:[vscode.Uri.joinPath(context.extensionUri,'resources'),vscode.Uri.joinPath(context.extensionUri,'dist')]});
  const scriptNonce=randomBytes(24).toString('base64'),css=panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri,'resources/workbench.css')),script=panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri,'dist/canvas.js'));
  panel.webview.html=`<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${panel.webview.cspSource}; script-src 'nonce-${scriptNonce}';"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="${css}"></head><body data-view-id="${viewId}"><header><p class="eyebrow">NETCLAW CANVAS</p><h1>Investigations</h1><p>Branch a conversation while retaining its selected ancestor context.</p><div class="toolbar"><button id="save">Save investigation</button><button id="open">Open saved</button><button id="import">Import HUD Canvas v1</button><button id="export">Export reviewed copy</button><button id="refresh">Check requests</button></div></header><main><p id="status" role="status" aria-live="polite">Loading…</p><div id="lanes" class="canvas-lanes"></div></main><script nonce="${scriptNonce}" src="${script}"></script></body></html>`;
  const valid=()=>{if(disposed||generation!==connection.generation||!connection.ready)throw Error('Connection changed. Reopen Canvas for the intended installation.');};
  const persist=async()=>{valid();await local.update(key,saved);};
  const post=async(data:object)=>{valid();await panel.webview.postMessage({viewId,...data});};
  const load=async()=>{
    const inventory=await connection.call<{data:{contexts:{id:string;name:string;size:number}[]}}>('operator_snapshot',{domain:'knowledge'});
    await post({type:'contexts',contexts:inventory.data.contexts});
    const requests:Record<string,unknown>={};
    for(const [nodeId,binding] of Object.entries(saved.bindings)){
      if(binding.pendingNonce&&!binding.operationId){const result=await connection.call<{data:{operation?:{operationId:string}}}>('operator_resources',{kind:'overview',filters:{query:binding.pendingNonce}});if(result.data.operation){binding.operationId=result.data.operation.operationId;await persist();}}
      if(binding.operationId){
        const operation=await connection.call('operator_operation_get',{operationId:binding.operationId});
        const history=await connection.call<{data:{requests:{operationId:string;prompt:string}[]}}>('operator_snapshot',{domain:'knowledge',resourceId:binding.conversationId});
        requests[nodeId]={...operation,prompt:history.data.requests.find(r=>r.operationId===binding.operationId)?.prompt};
      }
    }
    await post({type:'requests',requests});
  };
  const save=async()=>{
    const value=await connection.call<{id:string}>('operator_workspace',{action:'canvas-import',nonce:nonce(),args:{name:'VS Code investigation',content:JSON.stringify(document)}});
    saved={...saved,id:value.id};await persist();return value.id;
  };
  panel.webview.onDidReceiveMessage(async(raw:unknown)=>{
    if(!raw||typeof raw!=='object')return;const m=raw as Record<string,unknown>;
    if(m.viewId!==viewId||typeof m.requestId!=='string'||m.requestId.length>100||typeof m.type!=='string'||!['ready','save','open','import','export','send','refresh','state'].includes(m.type)||Object.keys(m).some(k=>!['viewId','requestId','type','document','nodeId','text','contextIds'].includes(k)))return;
    if(m.document){if(typeof m.document!=='object'||JSON.stringify(m.document).length>10*1024*1024)return;const value=m.document as Canvas;if(value.v!==1||!Array.isArray(value.nodes)||value.nodes.length>500)return;document=value;}
    try{
      valid();if(m.type==='state')return;if(busy)return;busy=true;
      if(m.type==='ready'&&saved.id){const value=await connection.call<{content:Canvas}>('operator_workspace',{action:'canvas-export',args:{id:saved.id}});document=value.content;}
      if(m.type==='import'){
        const files=await vscode.window.showOpenDialog({canSelectMany:false,filters:{'HUD Canvas':['json']}});if(!files?.[0])return;
        const stat=await vscode.workspace.fs.stat(files[0]);if(stat.size>10*1024*1024)throw Error('Canvas import exceeds 10 MiB.');
        const bytes=await vscode.workspace.fs.readFile(files[0]);valid();
        const value=await connection.call<{id:string}>('operator_workspace',{action:'canvas-import',nonce:nonce(),args:{name:'Imported HUD investigation',content:Buffer.from(bytes).toString('utf8')}});
        const result=await connection.call<{content:Canvas}>('operator_workspace',{action:'canvas-export',args:{id:value.id}});document=result.content;saved={id:value.id,bindings:{}};await persist();
      }
      if(m.type==='open'){
        const inventory=await connection.call<{data:{artifacts:{id:string;name:string;createdAt:string}[]}}>('operator_snapshot',{domain:'knowledge'});
        const item=await vscode.window.showQuickPick(inventory.data.artifacts.map(a=>({label:a.name,description:a.createdAt,id:a.id})));if(!item)return;
        const result=await connection.call<{content:Canvas}>('operator_workspace',{action:'canvas-export',args:{id:item.id}});document=result.content;saved={id:item.id,bindings:{}};await persist();
      }
      if(m.type==='save')await save();
      if(m.type==='export'){
        const id=await save(),result=await connection.call<{content:Canvas}>('operator_workspace',{action:'canvas-export',args:{id}});
        const preview=await vscode.workspace.openTextDocument({content:JSON.stringify(result.content,null,2),language:'json'});await vscode.window.showTextDocument(preview,{preview:true});
        const destination=await vscode.window.showSaveDialog({filters:{'Canvas JSON':['json']},saveLabel:'Save reviewed Canvas'});if(destination)await vscode.workspace.fs.writeFile(destination,Buffer.from(preview.getText()));
      }
      if(m.type==='send'){
        if(typeof m.nodeId!=='string'||typeof m.text!=='string'||Buffer.byteLength(m.text)>65536||!m.text.trim())throw Error('Invalid Canvas message.');
        const node=document.nodes.find(n=>n.id===m.nodeId);if(!node||!['chat',undefined].includes(node.kind))throw Error('This imported lane is retained as a reference and cannot dispatch from this candidate.');
        let binding=saved.bindings[m.nodeId];
        if(binding?.pendingNonce){if(!binding.operationId)throw Error('Admission is unconfirmed. Check requests before sending.');const op=await connection.call<{state:string}>('operator_operation_get',{operationId:binding.operationId});if(!['succeeded','failed','cancelled','denied','expired'].includes(op.state))throw Error('This lane has an unresolved request. Check it before sending more work.');}
        if(m.contextIds!==undefined&&(!Array.isArray(m.contextIds)||m.contextIds.length>19||!m.contextIds.every(v=>typeof v==='string'&&v.length<=200)))throw Error('Select at most 19 staged contexts.');
        const contextIds:string[]=Array.isArray(m.contextIds)?m.contextIds as string[]:[];
        if(!binding){
          const seed=[...(node.seedContext||[]),...(node.messages||[])].map(value=>({role:value.role,content:value.content}));
          if(seed.length){const value=await connection.call<{contextId:string}>('operator_workspace',{action:'rag-stage',nonce:nonce(),args:{name:'Selected Canvas ancestor context',content:JSON.stringify(seed)}});contextIds.push(value.contextId);}
          const opened=await connection.call<{conversationId:string}>('operator_conversation_open',{nonce:nonce(),view:'canvas'});binding={conversationId:opened.conversationId};
        }
        await save(); // The explicit send preserves its graph/context before admission.
        binding={...binding,pendingNonce:nonce(),operationId:undefined};saved.bindings[m.nodeId]=binding;await persist();
        const op=await connection.call<{operationId:string}>('operator_request_submit',{nonce:binding.pendingNonce,conversationId:binding.conversationId,prompt:m.text,contextIds});binding.operationId=op.operationId;await persist();
        await post({type:'admitted',nodeId:m.nodeId,prompt:m.text,operationId:op.operationId});
      }
      if(['ready','open','import'].includes(m.type))await post({type:'document',document});
      await load();if(m.type==='save')await post({type:'notice',message:'Investigation saved. Imports and exports carry no execution authority.'});
    }catch(error){await post({type:'notice',message:error instanceof Error?error.message:'Canvas operation unavailable.'}).catch(()=>{});}
    finally{busy=false;}
  });
  const timer=setInterval(()=>{if(!busy&&!disposed&&generation===connection.generation)void load().catch(()=>{});},3000);
  panel.onDidDispose(()=>{disposed=true;clearInterval(timer);});return panel;
}
