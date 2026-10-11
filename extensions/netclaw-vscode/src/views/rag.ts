import * as vscode from 'vscode';
import {randomUUID,randomBytes,createHash} from 'node:crypto';
import path from 'node:path';
import {Connection} from '../connection/connect';
import {LocalState} from '../state/local';

const nonce=()=>`${Date.now()}:${randomUUID()}`;
type Operation={operationId:string;kind:string;state:string;result?:{message?:string}};
type Listing={documents:{id:string;title:string;collection:string;ingest_status:string}[];nextCursor?:string;stats:{collections:string[]}};
type Search={searchId:string;results:{title:string;citation:string;chunk_text:string;staleness_notice?:string;low_confidence?:boolean}[]};
const escape=(text:string)=>text.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));

export function openRag(context:vscode.ExtensionContext,connection:Connection):vscode.WebviewPanel{
  if(!connection.ready||!connection.identity)throw Error('Connect to an existing installation first.');
  const identity=connection.identity,generation=connection.generation,viewId=randomUUID();
  const panel=vscode.window.createWebviewPanel('netclaw.rag','NetClaw RAG',vscode.ViewColumn.One,{enableScripts:true,localResourceRoots:[vscode.Uri.joinPath(context.extensionUri,'resources')]});
  const scriptNonce=randomBytes(24).toString('base64'),css=panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri,'resources/workbench.css')),script=panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri,'resources/rag.js'));
  panel.webview.html=`<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${panel.webview.cspSource}; script-src 'nonce-${scriptNonce}';"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="${css}"></head><body data-view-id="${viewId}"><header><p class="eyebrow">NETCLAW KNOWLEDGE</p><h1>RAG knowledge base</h1><p>${escape(connection.profile?.label||'NetClaw')} · ${escape(identity.harness.type)}</p><p>Search the same collections used by your NetClaw HUD and runtime.</p><div class="toolbar"><button id="refresh">Refresh collections</button><button id="upload">Upload a selected document</button><button id="chat">Open Chat</button><button id="canvas">Open Canvas</button></div></header><main><p id="status" role="status" aria-live="polite">Loading collections…</p><section aria-label="Search knowledge"><form id="rag-search"><label for="collection">Collection</label><select id="collection"><option value="documents">documents</option></select><label for="query">Search query</label><input id="query" type="search" maxlength="4000" required placeholder="Find an upgrade procedure, design decision or reference…"><button type="submit">Search knowledge</button></form><p class="hint">Retrieval uses local backend embeddings. Results are reference material, not current network state.</p><div id="results"></div><button id="stage" disabled>Add selected results to context</button><p class="hint">Choose this context in Chat or a Canvas lane before sending. Only that request shares it with NetClaw’s configured model.</p></section><section aria-label="Indexing operations"><h2>Indexing operations</h2><div id="operations"></div></section><section aria-label="Documents and snapshots"><h2>Documents, snapshots & replicas</h2><p id="stats"></p><div id="documents"></div><button id="more" hidden>Load more documents</button></section></main><script nonce="${scriptNonce}" src="${script}"></script></body></html>`;
  const local=new LocalState(path.join(context.storageUri?.fsPath||context.globalStorageUri.fsPath,'conversations'));
  const key=`rag.pending.${identity.hostId}.${identity.installationId}.${identity.principalId}`;
  let pending=local.get<{nonce?:string;operationId?:string}>(key,{}),listing:Listing|undefined,search:Search|undefined,disposed=false,busy=false;
  const valid=()=>{if(disposed||generation!==connection.generation||!connection.ready)throw Error('Connection changed. Reopen RAG for the intended installation.');};
  const post=async(data:object)=>{valid();await panel.webview.postMessage({viewId,...data});};
  const operations=async()=>{
    if(pending.nonce&&!pending.operationId){
      const result=await connection.call<{data:{operation?:Operation}}>('operator_resources',{kind:'overview',filters:{query:pending.nonce}});
      if(result.data.operation){pending.operationId=result.data.operation.operationId;await local.update(key,pending);}
    }
    const result=await connection.call<{data:{operations:Operation[]}}>('operator_resources',{kind:'overview'});
    await post({type:'operations',operations:result.data.operations.filter(o=>o.kind==='rag-index'),unconfirmed:Boolean(pending.nonce&&!pending.operationId)});
  };
  const load=async(more=false)=>{
    await operations();
    const value=await connection.call<Listing>('operator_workspace',{action:'rag-list',args:{},limit:100,...(more&&listing?.nextCursor?{cursor:listing.nextCursor}:{})});
    listing={...value,documents:[...(more?listing?.documents||[]:[]),...value.documents]};await post({type:'listing',...listing});
  };
  panel.webview.onDidReceiveMessage(async(raw:unknown)=>{
    if(!raw||typeof raw!=='object')return;const m=raw as Record<string,unknown>;
    if(JSON.stringify(m).length>16384||m.viewId!==viewId||!['ready','refresh','more','search','stage','upload','chat','canvas'].includes(String(m.type))||Object.keys(m).some(k=>!['viewId','type','query','collection','indices'].includes(k)))return;
    try{
      valid();if(busy)return;busy=true;
      if(m.type==='chat'||m.type==='canvas'){await vscode.commands.executeCommand(m.type==='chat'?'netclaw.openChat':'netclaw.openCanvas');return;}
      if(['ready','refresh','more'].includes(String(m.type)))await load(m.type==='more');
      if(m.type==='search'){
        if(typeof m.query!=='string'||!m.query.trim()||m.query.length>4000||typeof m.collection!=='string'||!/^[\w.-]{1,128}$/.test(m.collection))throw Error('Enter a query and collection.');
        search=await connection.call<Search>('operator_workspace',{action:'rag-search',args:{query:m.query,collection:m.collection,k:10}});await post({type:'results',...search});
      }
      if(m.type==='stage'){
        if(!search||!Array.isArray(m.indices)||!m.indices.length||m.indices.length>20||!m.indices.every(i=>Number.isInteger(i)&&i>=0&&i<search!.results.length))throw Error('Select one or more current results.');
        const content=m.indices.map(i=>search!.results[i]!).map(r=>[r.citation,r.low_confidence?'Low confidence retrieval.':'',r.staleness_notice,r.chunk_text].filter(Boolean).join('\n')).join('\n\n');
        const preview=await vscode.workspace.openTextDocument({content,language:'plaintext'});await vscode.window.showTextDocument(preview,{preview:true,preserveFocus:true,viewColumn:vscode.ViewColumn.Beside});
        if(await vscode.window.showInformationMessage('Add these reviewed RAG results to NetClaw context?',{modal:true,detail:`Destination: ${identity.installationId}. They are sent to the configured model only when selected in a submitted request.`},'Add selected context')!=='Add selected context')return;valid();
        await connection.call('operator_workspace',{action:'rag-context',nonce:nonce(),args:{id:search.searchId,indices:m.indices}});await post({type:'notice',message:'Selected citations are available in Chat and Canvas. Choose them before sending a message.'});
      }
      if(m.type==='upload'){
        if(pending.nonce&&!pending.operationId)throw Error('A prior indexing admission is unconfirmed. Refresh to reconcile it before uploading again.');
        const selected=await vscode.window.showOpenDialog({canSelectMany:false,openLabel:'Review document for NetClaw',filters:{Documents:['pdf','md','markdown','html','htm','txt','docx','xlsx','pptx','vsdx','doc','xls','ppt','vsd']}});if(!selected?.[0])return;
        const file=selected[0],stat=await vscode.workspace.fs.stat(file);if(stat.size>10*1024*1024||stat.size===0)throw Error('Select a nonempty document up to 10 MiB.');
        const bytes=Buffer.from(await vscode.workspace.fs.readFile(file));if(bytes.length>10*1024*1024)throw Error('The document grew beyond 10 MiB.');
        const name=path.posix.basename(file.path),sha256=createHash('sha256').update(bytes).digest('hex');
        const type=await vscode.window.showQuickPick(['vendor','standard','customer','install-guide','other'],{title:'Document category'});if(!type)return;valid();
        await load();const previous=listing?.documents.find(d=>d.title===name);
        const review=`File: ${file.toString(true)}\nSize: ${bytes.length} bytes\nSHA-256: ${sha256}\nDestination: ${connection.profile?.label} / ${identity.installationId} / documents\n${previous?'This replaces the reviewed document '+previous.id+'.':'The selected file will be retained and indexed in the backend knowledge base.'}`;
        if(await vscode.window.showInformationMessage(`Upload and index ${name}?`,{modal:true,detail:review},'Upload and index')!=='Upload and index')return;valid();
        const upload=await connection.call<{uploadId:string}>('operator_workspace',{action:'rag-upload',nonce:nonce(),args:{name,docType:type,content:bytes.toString('base64')}});
        pending={nonce:nonce()};await local.update(key,pending);
        const admitted=await connection.call<Operation>('operator_workspace',{action:'rag-index',nonce:pending.nonce,args:{id:upload.uploadId,...(previous?{expectedDocumentId:previous.id}:{})}});
        pending.operationId=admitted.operationId;await local.update(key,pending);await operations();await post({type:'notice',message:'Indexing admitted. You can close this view; the backend owns the operation. Refresh collections after it completes.'});
      }
    }catch(error){await post({type:'notice',message:error instanceof Error?error.message:'RAG is unavailable.'}).catch(()=>{});}
    finally{busy=false;}
  });
  const timer=setInterval(()=>{if(!busy&&!disposed&&generation===connection.generation)void operations().catch(()=>{});},5000);
  panel.onDidDispose(()=>{disposed=true;clearInterval(timer);});return panel;
}
