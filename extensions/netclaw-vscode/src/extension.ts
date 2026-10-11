import * as vscode from 'vscode';
import { randomUUID } from 'node:crypto';
import { Connection } from './connection/connect';
import { Profiles,ConnectionProfile,hostContext } from './state/profiles';
import { NavigationTree,connectionTree,Navigation } from './views/overview';
import { openDataView } from './webview/bridge';
import { openChat } from './views/chat';
import { openCanvas } from './views/canvas';
import { openRag } from './views/rag';
import { stageSelectedContext } from './commands/context';

const nonce=():string=>`${Date.now()}:${randomUUID()}`;
type Domain={title:string;method:string;args:Record<string,unknown>;group:string;icon:string};
const domains:Record<string,Domain>={
  overview:{title:'Overview',method:'operator_resources',args:{kind:'overview'},group:'estate',icon:'dashboard'},
  estate:{title:'Risk / iN2N',method:'operator_resources',args:{kind:'member'},group:'estate',icon:'organization'},
  peers:{title:'External peers / eN2N',method:'operator_resources',args:{kind:'peer'},group:'estate',icon:'globe'},
  mobile:{title:'Mobile & edge',method:'operator_resources',args:{kind:'edge'},group:'estate',icon:'device-mobile'},
  science:{title:'Science Officer',method:'operator_resources',args:{kind:'advisor'},group:'knowledge',icon:'beaker'},
  network:{title:'Network',method:'operator_resources',args:{kind:'network'},group:'estate',icon:'type-hierarchy'},
  operations:{title:'Operations',method:'operator_resources',args:{kind:'overview'},group:'operations',icon:'tasklist'},
  gait:{title:'GAIT audit trail',method:'operator_evidence',args:{kind:'gait'},group:'operations',icon:'history'},
  integrations:{title:'MCP integrations',method:'operator_resources',args:{kind:'integration'},group:'integrations',icon:'plug'},
  skills:{title:'Installed skills',method:'operator_resources',args:{kind:'skill'},group:'integrations',icon:'tools'},
  settings:{title:'Runtime settings',method:'operator_snapshot',args:{domain:'settings'},group:'integrations',icon:'settings-gear'},
  configuration:{title:'Environment configuration',method:'operator_snapshot',args:{domain:'settings'},group:'integrations',icon:'key'},
  tokenomics:{title:'Tokenomics',method:'operator_snapshot',args:{domain:'usage'},group:'operations',icon:'graph'},
  security:{title:'DefenseClaw',method:'operator_snapshot',args:{domain:'security'},group:'security',icon:'shield'},
  openshell:{title:'OpenShell',method:'operator_snapshot',args:{domain:'security'},group:'security',icon:'lock'},
  knowledge:{title:'Knowledge & memory',method:'operator_snapshot',args:{domain:'knowledge'},group:'knowledge',icon:'library'},
  documentation:{title:'Documentation',method:'operator_snapshot',args:{domain:'documentation'},group:'help',icon:'book'},
};

export async function activate(context:vscode.ExtensionContext):Promise<{connection:Connection;profiles:Profiles}> {
  const output=vscode.window.createOutputChannel('NetClaw'),profiles=new Profiles(context.globalState,context.globalStorageUri.fsPath),connection=new Connection(output);
  const status=vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left,40);status.command='netclaw.selectConnection';status.name='NetClaw installation';
  context.subscriptions.push(output,connection,status);const trees:NavigationTree[]=[];
  const refresh=()=>{for(const tree of trees)tree.refresh();status.text=connection.identity?`$(remote) ${connection.profile?.label} · ${connection.identity.harness.type}`:'$(remote) NetClaw: disconnected';status.tooltip=connection.identity?`${hostContext()}\n${connection.identity.installationId}\nManagement contract ${connection.identity.contract.major}`:'Select an existing installation';status.show();};
  context.subscriptions.push(connection.changed.event(refresh));
  function register(name:string,handler:(...args:unknown[])=>unknown):void {
    context.subscriptions.push(vscode.commands.registerCommand(`netclaw.${name}`,async(...args:unknown[])=>{try{return await handler(...args);}catch(error){const message=error instanceof Error?error.message:'NetClaw operation failed.';void vscode.window.showErrorMessage(message);}}));
  }
  async function connectProfile(profile:ConnectionProfile):Promise<void>{
    const identity=await vscode.window.withProgress({location:vscode.ProgressLocation.Notification,title:`Connecting to ${profile.label}`},()=>connection.connect(profile));
    if(!profile.installationId){
      const answer=await vscode.window.showInformationMessage(`Bind ${profile.label} to ${identity.harness.type} installation ${identity.installationId}?`,{modal:true,detail:`Host context: ${hostContext()}\nBackend source: ${identity.sourceVersion}\nPrincipal: ${identity.principalId}`},'Bind installation');
      if(answer!=='Bind installation'){await connection.disconnect();return;}
      await profiles.save({...profile,installationId:identity.installationId,hostId:identity.hostId});
    }
    refresh();
  }
  register('addConnection',async()=>{
    if(!vscode.workspace.isTrusted)throw Error('Trust this workspace before adding an operational connection.');
    const transport=await vscode.window.showQuickPick([{label:'This extension host',value:'local' as const,description:hostContext()},{label:'Existing SSH alias',value:'ssh' as const,description:'Uses your existing known-host and authentication configuration'}],{title:'Existing NetClaw location'});if(!transport)return;
    if(transport.value==='local'&&process.platform==='win32'){await vscode.commands.executeCommand('workbench.action.showCommands','WSL:');return;}
    const harness=await vscode.window.showQuickPick(['openclaw','hermes'],{title:'Installed NetClaw harness'});if(!harness)return;
    const label=await vscode.window.showInputBox({title:'Connection label',prompt:'A short name for this installation',validateInput:v=>v.trim()&&v.length<=100?undefined:'Enter a label of 1–100 characters'});if(!label)return;
    const sshAlias=transport.value==='ssh'?await vscode.window.showInputBox({title:'Existing SSH alias',prompt:'An alias already configured and trusted in your SSH client'}):undefined;if(transport.value==='ssh'&&!sshAlias)return;
    const nodePath=await vscode.window.showInputBox({title:'Backend Node executable',prompt:'Absolute path on the managed host; supported Node 24.19–24.x or 26.1+'});if(!nodePath)return;
    const launcherPath=await vscode.window.showInputBox({title:'Installed management launcher',prompt:'Absolute path ending in /scripts/netclaw-operator.mjs'});if(!launcherPath)return;
    const home=await vscode.window.showInputBox({title:'Existing runtime home',prompt:'Absolute path to the selected OpenClaw or Hermes home; no files are installed or upgraded'});if(!home)return;
    const profile=await profiles.save({label,transport:transport.value,home,nodePath,launcherPath,sshAlias,harness:harness as 'openclaw'|'hermes'});refresh();await connectProfile(profile);
  });
  register('selectConnection',async id=>{
    const items=profiles.list();const profile=typeof id==='string'?items.find(p=>p.id===id):(await vscode.window.showQuickPick(items.map(p=>({label:p.label,description:`${p.harness} · ${p.transport}`,profile:p})),{title:'Select NetClaw installation'}))?.profile;
    if(profile)await connectProfile(profile);else if(!items.length)await vscode.commands.executeCommand('netclaw.addConnection');
  });
  register('disconnect',()=>connection.disconnect());
  register('removeConnection',async()=>{const item=await vscode.window.showQuickPick(profiles.list().map(p=>({label:p.label,profile:p})));if(!item)return;if(connection.profile?.id===item.profile.id)await connection.disconnect();await profiles.remove(item.profile.id);refresh();});
  register('openDomain',async key=>{if(typeof key!=='string'||!Object.hasOwn(domains,key))throw Error('Unknown NetClaw view.');const view=domains[key]!;openDataView(context,connection,{title:view.title,kind:key,load:()=>connection.call(view.method,view.args)});});
  for(const [command,key] of Object.entries({openOverview:'overview',openSettings:'settings',openGait:'gait',openTokenomics:'tokenomics',openDocumentation:'documentation'}))register(command,()=>vscode.commands.executeCommand('netclaw.openDomain',key));
  register('help',async()=>{const document=await vscode.workspace.openTextDocument(vscode.Uri.joinPath(context.extensionUri,'README.md'));await vscode.window.showTextDocument(document);});
  register('refresh',refresh);
  register('openChat',()=>openChat(context,connection));
  register('openAvatar',()=>openChat(context,connection,true));
  register('openCanvas',()=>openCanvas(context,connection));
  register('openRag',()=>openRag(context,connection));
  register('addSelectedContext',()=>stageSelectedContext(connection));
  register('prepareChange',async()=>{
    const snapshot=await connection.call<{data:{revision:string;environment:{managedFields:{key:string;secret:boolean}[]}}}>('operator_snapshot',{domain:'settings'});
    const field=await vscode.window.showQuickPick(snapshot.data.environment.managedFields.map(f=>({label:f.key,description:f.secret?'Secret · presence only':'Configuration value',field:f})),{title:'Choose a managed environment field'});if(!field)return;
    const intent=await vscode.window.showQuickPick(['keep','replace','clear'],{title:`${field.label}: desired change`});if(!intent)return;
    let value:string|undefined;if(!field.field.secret&&intent==='replace'){value=await vscode.window.showInputBox({title:`New ${field.label}`});if(value===undefined)return;}
    const prepared=await connection.call<{proposalId:string}>('operator_change_prepare',{nonce:nonce(),action:'integration.configure',targets:[connection.identity!.installationId],expectedRevision:snapshot.data.revision,patch:{fields:[{key:field.label,intent,...(value===undefined?{}:{value})}]}});
    await vscode.commands.executeCommand('netclaw.reviewProposal',prepared.proposalId);
  });
  register('reviewProposal',async id=>{
    let proposalId=typeof id==='string'?id:undefined;
    if(!proposalId){
      const overview=await connection.call<{data:{operations:{operationId:string;state:string;result?:{proposalId?:string}}[]}}>('operator_resources',{kind:'overview'});
      const item=await vscode.window.showQuickPick(overview.data.operations.filter(o=>o.state==='waiting-approval'&&o.result?.proposalId).map(o=>({label:o.result!.proposalId!,description:o.state})),{title:'Pending managed proposals'});proposalId=item?.label;
    }
    if(!proposalId)return;
    const response=await connection.call<{data:{action:string;targets:string[];expectedRevision:string;impact:string;changeClass:string;patch:{fields?:{key:string;intent:string}[]}}}>('operator_evidence',{kind:'approval',id:proposalId});
    const proposal=response.data;
    const review=await vscode.window.showInformationMessage(`Review ${proposal.action}`,{modal:true,detail:`Installation: ${connection.identity?.installationId}\nTargets: ${proposal.targets.join(', ')}\n${proposal.impact}\n${JSON.stringify(proposal.patch,null,2)}`},'Apply reviewed change');if(review!=='Apply reviewed change')return;
    const replacements:Record<string,string>={};
    for(const field of proposal.patch.fields||[]){if(field.intent!=='replace'||!/KEY|TOKEN|PASSWORD|SECRET|AUTH|CREDENTIAL/i.test(field.key))continue;const value=await vscode.window.showInputBox({title:`Replace ${field.key}`,password:true,prompt:'Blank keeps the existing value. This input is sent only to the selected backend.'});if(value===undefined)return;replacements[field.key]=value;}
    const approvalReference=proposal.changeClass==='production'?await vscode.window.showInputBox({title:'Independently approved ServiceNow change reference',prompt:'NetClaw verifies the live Implement state and exact approved scope. This field does not approve the change.'}):undefined;
    if(proposal.changeClass==='production'&&!approvalReference)return;
    const result=await connection.call<{operationId:string}>('operator_change_apply',{proposalId,nonce:nonce(),expectedRevision:proposal.expectedRevision,replacements,...(approvalReference?{approvalReference}:{})});
    openDataView(context,connection,{title:'Change outcome',kind:'change',load:()=>connection.call('operator_operation_get',{operationId:result.operationId})});
  });
  register('exportDiagnostics',async()=>{
    const result=await connection.call('operator_identity');const content=JSON.stringify({generatedAt:new Date().toISOString(),extensionVersion:'0.1.0',identity:result},null,2);
    const document=await vscode.workspace.openTextDocument({content,language:'json'});await vscode.window.showTextDocument(document);
    if(await vscode.window.showInformationMessage('Review these local diagnostics before saving or sharing.','Save local copy')!=='Save local copy')return;
    const destination=await vscode.window.showSaveDialog({filters:{JSON:['json']},saveLabel:'Save reviewed diagnostics'});if(destination)await vscode.workspace.fs.writeFile(destination,Buffer.from(content));
  });
  const connections=connectionTree(connection,profiles);trees.push(connections);context.subscriptions.push(vscode.window.registerTreeDataProvider('netclaw.connections',connections));
  for(const group of ['estate','operations','integrations','knowledge','security','help']){
    const tree=new NavigationTree(()=>{
      const items:Navigation[]=Object.entries(domains).filter(([,d])=>d.group===group).map(([key,d])=>({label:d.title,command:'netclaw.openDomain',args:[key],icon:d.icon}));
      if(group==='help')items.push({label:'Getting started',command:'netclaw.help',icon:'info'});
      if(group==='knowledge')items.unshift({label:'RAG knowledge base',command:'netclaw.openRag',icon:'search'});
      if(group==='operations')items.unshift({label:'Chat',command:'netclaw.openChat',icon:'comment-discussion'});
      if(group==='operations')items.push({label:'Avatar',command:'netclaw.openAvatar',icon:'person'});
      if(group==='operations')items.push({label:'Canvas',command:'netclaw.openCanvas',icon:'preview'});
      if(group==='operations')items.push({label:'Prepare a managed change',command:'netclaw.prepareChange',icon:'git-pull-request'},{label:'Review a proposal',command:'netclaw.reviewProposal',icon:'checklist'});
      return items;
    });trees.push(tree);context.subscriptions.push(vscode.window.registerTreeDataProvider(`netclaw.${group}`,tree));
  }
  context.subscriptions.push(vscode.workspace.onDidGrantWorkspaceTrust(refresh));refresh();
  return {connection,profiles};
}
export function deactivate():void {}
