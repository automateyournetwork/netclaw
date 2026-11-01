import * as vscode from 'vscode';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {randomBytes,randomUUID} from 'node:crypto';
import {LocalState} from '../state/local';
import {escape} from '../webview/shell';
import {SetupDraft} from '../setup/plan';
import {canonical,hash,readData,realParents,strictJson} from '../setup/data';
import {currentHost} from '../setup/host';
import {openWindowsGate} from '../setup/gate';
import {pendingHandoffs,claimHandoff} from '../setup/handoff';
import {prerequisites,hostPrerequisites,remedy,preparedMacPaths} from '../setup/prerequisites';
import {detectInstallations} from '../setup/installations';
import {inspectSource,resolveSelection,acquireSource} from '../setup/source';
import {SetupEngine} from '../setup/engine';
import {openNativeTerminal} from '../setup/native-terminal-view';
import {secretInput} from '../setup/secrets';
import {reviewPlan,reviewLive,channelDestination} from '../setup/review';
import {SetupRuns} from '../setup/runs';
import {showReport,exportReport} from '../setup/reports';
import {selectLocalModel} from '../setup/discovery';
import {showAdvisor} from '../setup/advisor';
import {writePresetReport} from '../setup/preset';
import {CommsManifest,validateComms,discoverComms,selectChannels,channelFields,setZoomBinding,channelTestChoices,setChannelTests} from '../setup/comms';
import {TestbedSource,setTestbed} from '../setup/testbeds';

const choose=async(title:string,values:{id:string;title?:string;description?:string}[])=>
  (await vscode.window.showQuickPick(values.map(v=>({label:v.title||v.id,description:v.description,id:v.id})),{title}))?.id;
const input=(title:string,prompt:string,value?:string)=>vscode.window.showInputBox({title,prompt,value,ignoreFocusOut:true,
  validateInput:v=>v.trim()&&!/[\r\n\0]/.test(v)?undefined:'Enter a nonempty, single-line value.'});

export class SetupWizard implements vscode.Disposable {
  private draft?:SetupDraft;
  private view?:vscode.WebviewPanel;
  private engine?:SetupEngine;
  private run?:any;
  private busy=false;
  private catalog:any;
  private comms!:CommsManifest;
  private testbedSources!:TestbedSource[];
  private adapters:any;
  private runs:SetupRuns;
  private selectedHomes:{home:string}[]=[];
  private handoffChecked=false;
  private pendingSecrets=new Map<string,string>();
  constructor(private context:vscode.ExtensionContext,private local:LocalState){this.runs=new SetupRuns(local);this.preparedTools();}
  private preparedTools(){
    if(process.platform==='darwin'&&this.local.get<boolean>('setup-mac-prerequisites-reviewed',false))
      process.env.PATH=[...new Set([...preparedMacPaths(process.arch),...(process.env.PATH||'').split(path.delimiter)])].join(path.delimiter);
  }
  private initialize(){
    if(this.draft)return;
    const base=path.join(this.context.extensionPath,'dist/setup'),stamp=readData(path.join(base,'stamp.json'));
    for(const [name,digest] of Object.entries(stamp.files)){
      if(path.basename(name)!==name||hash(fs.readFileSync(path.join(base,name)))!==digest)throw Error('Bundled setup policy changed. Rebuild or reinstall this extension.');
    }
    this.catalog=readData(path.join(base,'catalog.json'),16*1024*1024);this.adapters=readData(path.join(base,'harness-adapters.json'));
    this.testbedSources=readData(path.join(base,'pyats-testbed-sources.json')).sources;
    this.comms=readData(path.join(base,'comms.json'),4*1024*1024);validateComms(this.comms,readData(path.join(base,'comms.schema.json')));
    this.draft=new SetupDraft(readData(path.join(base,'claw-plan.schema.json')),this.catalog);
    const saved=this.local.get<any>('setup-draft',undefined);
    if(saved)this.draft.replace(saved,0);
    this.run=this.runs.saved();
  }
  snapshot(){this.initialize();return this.draft!.snapshot();}
  async submitDraft(value:any){
    if(this.busy)throw Error('Setup is busy. Wait for its current native action.');
    this.initialize();const current=this.draft!.snapshot();
    for(const key of ['host','source'])if(value[key]&&canonical(value[key])!==canonical(current.answers[key]||{}))throw Error('Choose the host and source through native setup first.');
    const next={...value};for(const key of ['host','source'])if(current.answers[key])next[key]=current.answers[key];
    this.draft!.replace(next,current.revision);this.clearSetupSecrets();await this.persist();await this.open();return {submitted:true,reviewRequired:true};
  }
  clearSetupSecrets(){this.pendingSecrets.clear();}
  async setupObservation(){
    this.initialize();const plan=this.draft!.snapshot().answers;
    const bindings=this.local.get<any[]>('management-bindings',[]);
    const checks=await prerequisites(this.context.extensionPath,plan.claws?.[0]?.harness||'openclaw');
    return {host:currentHost(vscode.env.remoteName).kind,
      existingInstallations:detectInstallations(bindings.map(b=>({home:b.target.home,harness:b.target.kind,label:b.profile.label,installationId:b.target.installationId})),this.selectedHomes).length,
      sourceReviewed:!!this.engine,prerequisites:checks.map(c=>({id:c.id,state:c.state,version:c.version,required:c.required})),
      detection:'saved-bindings-known-defaults-and-selected-homes',networkChecks:'native-prerequisite-action-required'};
  }
  setupCatalog(args:any){
    if(args.kind==='comms'||args.kind==='channel'){
      this.initialize();const items=discoverComms(this.comms,args.query||'',args.harness).filter(e=>(args.kind!=='channel'||e.inventory==='channel')&&(!args.ids||args.ids.includes(e.id)));
      return {items:items.map(e=>({id:e.id,title:e.name,channelId:e.channelId,nativeId:e.nativeId,harness:e.harness,kind:e.kind,
        roles:e.roles,hosts:e.hosts,component:e.component,state:e.state,qualification:e.qualification,reason:e.setup.reason,
        documentation:e.documentation,version:e.baseline.version,settings:e.setup.settings.map(f=>({key:f.key,classification:f.classification,required:f.required,help:f.help}))})),bounded:true};
    }
    this.initialize();const source=args.kind==='skill'?this.catalog.skills:args.kind==='profile'?this.catalog.profiles:this.catalog.components;
    const selected=source.filter((item:any)=>(!args.ids||args.ids.includes(item.id))&&(!args.query||[item.id,item.title,item.description].join(' ').toLowerCase().includes(args.query.toLowerCase()))).slice(0,40);
    return {items:selected.map((item:any)=>({id:item.id,title:item.title||item.id,description:item.description||item.purpose||'',components:item.components||[],dependencies:item.dependencies||[],settings:(item.settings||[]).map((f:any)=>({key:f.key,classification:f.classification,required:f.required,help:f.help}))})),bounded:true};
  }
  async setupStatus(runRef?:string){
    const ref=this.runs.saved();if(runRef&&runRef!==ref?.runId)throw Error('unknown_run');if(!ref)return {state:'not_started'};
    const engine=this.engine?.source===ref.source?this.engine:new SetupEngine('python3',ref.source);
    const status=await engine.read('status',undefined,ref.runId),report=await engine.read('report',undefined,ref.runId);
    return {runRef:ref.runId,state:status.state,report};
  }
  async writeDeploymentReport(){const ref=this.runs.saved();if(!ref)throw Error('No setup run is saved.');const engine=this.engine||new SetupEngine('python3',ref.source);await writePresetReport(this.local,engine,ref);}
  async connectionCandidates(){const ref=this.runs.saved();if(!ref)throw Error('No setup run is saved.');const engine=this.engine||new SetupEngine('python3',ref.source);if(engine.source!==ref.source)throw Error('Select the original source for this run.');return (await engine.read('connections',undefined,ref.runId)).candidates;}
  async setupSecret(owner:string,key:string){
    if(this.busy)throw Error('Setup is busy.');
    const state=this.snapshot(),claw=state.answers.claws?.find((c:any)=>c.id===owner),setting=claw?.settings?.[key];
    if(setting?.kind!=='secret'||setting.owner!==owner||setting.source!=='prompt')throw Error('not_authorized');
    const value=await secretInput(owner,key);if(this.snapshot().hash!==state.hash)throw Error('stale_plan');
    if(value===undefined)return {state:'absent'};this.pendingSecrets.set(state.hash+'|'+owner+'|'+key,value);return {state:'present'};
  }
  private async setupCredential(owner:string,key:string){
    const id=this.snapshot().hash+'|'+owner+'|'+key,value=this.pendingSecrets.get(id);this.pendingSecrets.delete(id);
    return value??secretInput(owner,key);
  }
  async setupInspect(file:string,operation:'validate'|'explain'){
    if(!this.engine)return {valid:false,applyReady:false,code:'native_source_required'};
    const result=await this.engine.read(operation,file);
    return {valid:result.valid,applyReady:result.applyReady,hash:result.hash,errors:result.errors,
      configurationRequiredCount:result.configurationRequired?.length||0,
      effects:(result.effects||[]).map((e:any)=>({phase:e.phase,component:e.component,native:e.native,scope:e.scope})),reviewRequired:true};
  }
  private async persist(){const state=this.draft!.snapshot();for(const key of this.pendingSecrets.keys())if(!key.startsWith(state.hash+'|'))this.pendingSecrets.delete(key);await this.local.update('setup-draft',state.answers);await this.render();}
  async open(){
    if(!vscode.workspace.isTrusted)throw Error('Trust this workspace before starting local setup.');
    this.initialize();
    const host=currentHost(vscode.env.remoteName);
    if(host.kind==='windows-gate'){await openWindowsGate(this.draft?.snapshot().answers,this.context.extensionPath);return;}
    if(host.kind==='unsupported'){await vscode.window.showWarningMessage(host.reason);return;}
    if(host.kind==='wsl2'&&!this.handoffChecked){
      this.handoffChecked=true;const root=path.join(os.homedir(),'.local/state/netclaw/setup/handoffs');
      const pending=pendingHandoffs(root,process.env.WSL_DISTRO_NAME||'');
      if(pending.length){
        const selected=await vscode.window.showQuickPick(pending.map(value=>({label:'Restore Windows setup choices',description:new Date(value.createdAt).toLocaleString(),value})),{title:'Private setup handoff available'});
        if(selected){
          const proposed={...selected.value.answers,unresolved:[...new Set([...((selected.value.answers.unresolved as string[])||[]),'review-wsl-host-source-paths'])]};
          const previous=this.draft!.snapshot();this.draft!.replace(proposed,previous.revision);
          try{claimHandoff(root,selected.value);await this.persist();}catch(error){this.draft!.replace(previous.answers,this.draft!.snapshot().revision);throw error;}
        }
      }
    }
    if(this.view){this.view.reveal();await this.render();return;}
    const view=vscode.window.createWebviewPanel('netclaw.setupWizard','Set up a NetClaw',vscode.ViewColumn.One,
      {enableScripts:true,retainContextWhenHidden:true,localResourceRoots:[vscode.Uri.joinPath(this.context.extensionUri,'resources')]});
    this.view=view;const nonce=randomBytes(24).toString('base64');
    const uri=(name:string)=>view.webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri,'resources',name));
    view.webview.html=`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${view.webview.cspSource}; style-src ${view.webview.cspSource}; script-src 'nonce-${nonce}';"><link rel="stylesheet" href="${uri('workbench.css')}"><link rel="stylesheet" href="${uri('setup-wizard.css')}"></head><body><header class="page-header"><div><p class="eyebrow">NETCLAW / SETUP</p><h1>A new home for your claw</h1><p>Choose its capabilities. Review every installation before it starts.</p></div><button data-action="manage">Manage existing claws</button></header><main id="setup"><p role="status">Loading setup…</p></main><script nonce="${nonce}" src="${uri('setup-wizard.js')}"></script></body></html>`;
    let serial=0;
    view.webview.onDidReceiveMessage(async(message:any)=>{
      if(!message||typeof message!=='object'||Buffer.byteLength(JSON.stringify(message))>8192||!Number.isSafeInteger(message.sequence)||message.sequence<=serial)return;
      serial=message.sequence;
      if(message.type==='ready'){await this.render();return;}
      if(message.type==='pause'){this.engine?.pause();return;}
      if(this.busy)return;
      this.busy=true;await this.render();
      try{await this.action(message.type,message);}
      catch(error){void vscode.window.showErrorMessage(error instanceof Error?error.message:'Setup action failed.');}
      finally{this.busy=false;await this.render();}
    });
    view.onDidDispose(()=>{this.engine?.pause();this.clearSetupSecrets();this.view=undefined;});await this.render();
  }
  private async render(){
    if(!this.view||!this.draft)return;
    const snapshot=this.draft.snapshot(),bindings=this.local.get<any[]>('management-bindings',[]);
    const installations=detectInstallations(bindings.map(b=>({home:b.target.home,harness:b.target.kind,label:b.profile.label,installationId:b.target.installationId})),this.selectedHomes);
    await this.view.webview.postMessage({type:'snapshot',...snapshot,busy:this.busy,installations,run:this.run,
      comms:this.comms.entries.map(e=>({id:e.id,title:e.name,channelId:e.channelId,harness:e.harness,kind:e.kind,aliases:e.aliases,
        roles:e.roles,hosts:e.hosts,component:e.component,inventory:e.inventory,version:e.baseline.version,
        disposition:e.setup.disposition,reason:e.setup.reason,qualification:e.qualification})),
      components:this.catalog.components.map((c:any)=>({id:c.id,title:c.title,category:c.category,description:c.description,
        skills:c.skills,dependencies:c.dependencies,links:c.links,native:c.installer.mode==='native',unavailable:this.adapters.unavailableComponents?.[c.id]?.reason,
        platforms:c.platforms,platformReason:c.platformReason,whenToChoose:c.whenToChoose,prerequisites:c.prerequisites,
        kind:c.kind,access:c.access,estimate:c.estimate,
        requiredSettings:c.settings.filter((s:any)=>s.required!=='optional'&&s.input!=='generated').map((s:any)=>s.key)})),
      profiles:this.catalog.profiles.map((p:any)=>({id:p.id,title:p.title,components:p.components}))});
  }
  private async action(type:string,message:any){
    this.preparedTools();
    if(type==='connect-new'){await vscode.commands.executeCommand('netclaw.setupConnect');return;}
    const state=this.draft!.snapshot();let plan=state.answers;
    if(type==='zoom-binding'){
      const existing=(plan.commsBindings||[]).find((b:any)=>b.owner===message.owner);
      const choice=await choose('Zoom input for this Risk',[{id:'none',title:'No Border binding',description:'Keep Zoom tools on this member.'},
        {id:'bind',title:'Bind this member to the Border',description:'Replace manual channel settings with a dedicated secret and a same-host loopback port.'}]);
      if(!choice)return;
      let port:number|null=null;
      if(choice==='bind'){
        const value=await input('Zoom Border port','Loopback port, 1024–65535. No listener starts while drafting.',String(existing?.port||19876));
        if(value===undefined)return;port=Number(value);
      }
      this.draft!.replace(setZoomBinding(plan,message.owner,port),state.revision);await this.persist();return;
    }
    if(type==='comms-guide'){
      if(!plan.source){await vscode.window.showInformationMessage('Choose a source checkout to read the Comms setup guide.');return;}
      const file=path.resolve(plan.source.path,'docs/COMMS-SETUP.md');realParents(file);
      await vscode.window.showTextDocument(vscode.Uri.file(file));return;
    }
    if(type==='comms-documentation'){
      const entry=this.comms.entries.find(e=>e.id===message.comms);if(!entry)throw Error('Select a known Comms option.');
      await vscode.env.openExternal(vscode.Uri.parse(entry.documentation));return;
    }
    if(type==='comms-option'){
      const claw=plan.claws?.find((c:any)=>c.id===message.owner),entry=this.comms.entries.find(e=>e.id===message.comms);
      if(!claw||!entry||entry.harness!==claw.harness)throw Error('Select a Comms option for this claw.');
      if(!entry.roles.includes(claw.role)||plan.host&&!entry.hosts.includes(plan.host.platform))throw Error('This Comms option requires a different owner role or host.');
      const allowed=discoverComms(this.comms,'',claw.harness,claw,plan.host?.platform).find(e=>e.id===entry.id)!;
      const selected=entry.component?allowed.selectable&&(claw.capabilities?.components||[]).includes(entry.component):(claw.channels||[]).some((c:any)=>c.id===entry.channelId);
      if(!allowed.selectable&&!selected){
        await vscode.window.showInformationMessage(entry.setup.reason,{modal:true});return;
      }
      if(entry.component){await this.action('component',{owner:claw.id,component:entry.component});return;}
      const ids=(claw.channels||[]).map((c:any)=>c.id),next=ids.includes(entry.channelId)?ids.filter((id:string)=>id!==entry.channelId):[...ids,entry.channelId];
      Object.assign(claw,selectChannels(claw,next,this.catalog,this.comms));
      this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='harness'||type==='provider'){await this.primaryChoice(type,message.owner);return;}
    if(type==='capabilities'){await this.configureClaw(message.owner);return;}
    if(type==='manage'){await vscode.commands.executeCommand('netclaw.selectConnection');return;}
    if(type==='advisor'){
      if(!this.engine)throw Error('Select a reviewed source first.');
      await showAdvisor(this.engine,await this.planFile());return;
    }
    if(type==='skills'){
      const claw=plan.claws?.find((c:any)=>c.id===message.owner);if(!claw?.capabilities)throw Error('Choose a profile first.');
      const choices=this.catalog.skills.filter((s:any)=>s.availability==='supported'&&s.components.every((id:string)=>claw.capabilities.components.includes(id)))
        .map((s:any)=>({label:s.title||s.id,description:s.id,picked:claw.capabilities.skills.includes(s.id),id:s.id}));
      const selected=await vscode.window.showQuickPick<{label:string;id:string}>(choices,{title:'Select independent skills',canPickMany:true});if(!selected)return;
      claw.capabilities.skills=selected.map(s=>s.id);this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='find-installation'){
      const selected=await vscode.window.showOpenDialog({canSelectFiles:false,canSelectFolders:true,canSelectMany:false,title:'Inspect an existing claw home (identity metadata only)'});
      if(selected?.[0]){const home=selected[0].fsPath;if(!this.selectedHomes.some(item=>item.home===home))this.selectedHomes.push({home});}return;
    }
    if(type==='prerequisites'){
      const rows=await prerequisites(this.context.extensionPath,plan.claws?.[0]?.harness||'openclaw',undefined,plan.source?.path);
      rows.push(...await hostPrerequisites((plan.claws||[]).flatMap((c:any)=>c.capabilities?.components||[]),currentHost(vscode.env.remoteName).kind));
      const item=await vscode.window.showQuickPick(rows.map(r=>({label:r.id+' · '+r.state,description:r.version||r.reason,detail:`Observed: ${r.version||'unknown'} · Required: ${r.required||'available'}. ${r.reason}`,row:r})),{title:'Prerequisites on this host'});
      if(item&&item.row.state!=='ready'){
        if(!['node','python3','git','uv'].includes(item.row.id)){await vscode.window.showInformationMessage(item.row.id+' · '+item.row.state,{modal:true,detail:`Observed: ${item.row.version||'unknown'}\nRequired: ${item.row.required||'available'}\n${item.row.reason}`});return;}
        const host=currentHost(vscode.env.remoteName);if(!['macos','wsl2'].includes(host.kind))return;
        const fix=remedy(item.row.id,host.kind as 'macos'|'wsl2',process.env.PATH);
        const choice=await vscode.window.showInformationMessage('Prepare '+item.row.id+'?',{modal:true,detail:fix.detail+(fix.command?'\n\n'+fix.command:'')},...(fix.command?['Open terminal step','Read guide']:['Read guide']));
        if(choice==='Open terminal step'&&fix.command){
          if(host.kind==='macos'){
            await this.local.update('setup-mac-prerequisites-reviewed',true);
            const terminal=vscode.window.createTerminal({name:'NetClaw prerequisite',shellPath:'/bin/bash',
              shellArgs:['--noprofile','--norc',path.join(this.context.extensionPath,'resources/mac-prerequisites.sh'),item.row.id],
              cwd:os.homedir(),strictEnv:true,env:{HOME:os.homedir(),USER:os.userInfo().username,SHELL:'/bin/bash',PATH:'/usr/bin:/bin:/usr/sbin:/sbin',LANG:'en_US.UTF-8'}});
            terminal.show();
          }else{const terminal=vscode.window.createTerminal({name:'NetClaw prerequisite'});terminal.show();terminal.sendText(fix.command,true);}
        }
        if(choice==='Read guide')await vscode.env.openExternal(vscode.Uri.parse(fix.url));
      }return;
    }
    if(type==='source'){await this.selectSource();return;}
    if(type==='documentation'){
      const component=this.catalog.components.find((c:any)=>c.id===message.component);if(!component)throw Error('Select a known capability.');
      const links=component.links.filter((l:any)=>l.target);const selected=await vscode.window.showQuickPick(links.map((link:any)=>({label:link.role,description:link.target,link})),{title:component.title+' documentation'}) as any;
      if(!selected)return;const target=selected.link.target;
      if(target.startsWith('https://'))await vscode.env.openExternal(vscode.Uri.parse(target));
      else if(plan.source){const file=path.resolve(plan.source.path,target.split('#')[0]);if(!file.startsWith(plan.source.path+path.sep))throw Error('Documentation path is outside the selected source.');realParents(file);await vscode.window.showTextDocument(vscode.Uri.file(file));}
      else await vscode.window.showInformationMessage('Choose a source checkout to open its local documentation.');
      return;
    }
    if(type==='channel'){
      const claw=plan.claws?.find((c:any)=>c.id===message.owner);if(!claw||claw.role==='member')throw Error('Channels belong to the Focused claw or Border.');
      const entries=discoverComms(this.comms,'',claw.harness,claw,plan.host?.platform).filter(e=>e.inventory==='channel'||e.channelId==='webex');
      const choices=[{label:'None',id:'none',description:'No conversation channels',picked:false},
        ...entries.map(e=>({label:e.name,id:e.channelId,description:e.state==='typed'||e.state==='native'?'Guided setup':e.setup.reason,picked:claw.channels?.some((c:any)=>c.id===e.channelId)}))];
      const picked=await vscode.window.showQuickPick(choices,{title:'Comms · conversation channels',placeHolder:'Select multiple channels, or choose None',canPickMany:true,matchOnDescription:true});if(!picked)return;
      const ids=picked.map(p=>p.id);
      for(const id of ids.filter(id=>id!=='none')){
        const e=entries.find(e=>e.channelId===id)!;
        if(!e.selectable&&!(['slack','telegram','discord'].includes(id)&&e.state==='incomplete-adapter')){await vscode.window.showInformationMessage(e.setup.reason,{modal:true});return;}
      }
      Object.assign(claw,selectChannels(claw,ids,this.catalog,this.comms));
      this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='ports'){
      const claw=plan.claws?.find((c:any)=>c.id===message.owner);if(!claw)throw Error('Select a claw.');
      for(const key of ['gatewayPort','hudPort','hudUiPort','companionPort','federationPort','bgpApiPort','bgpPort']){
        const text=await input('Port for '+claw.displayName,key+' · unique across all installations',String(claw.endpoints?.[key]||''));if(text===undefined)return;
        const value=Number(text);if(!Number.isInteger(value)||value<1024||value>65535)throw Error('Choose a port between 1024 and 65535.');claw.endpoints[key]=value;
      }
      this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='verification'){
      const optional=[{label:'4 · One live model turn',description:'Configured provider; normal token costs; separate approval at execution.',tier:4},
        {label:'5 · Channel message tests',description:'Choose channel requests; each message needs separate approval at execution.',tier:5},
        {label:'6 · Read-only device observation',description:'Selected inventory device only; separate native selection and approval.',tier:6}];
      const selected=await vscode.window.showQuickPick(optional.map(o=>({...o,picked:plan.verification?.tiers?.includes(o.tier)})),{title:'Optional verification (tiers 1–3 always run)',canPickMany:true});if(!selected)return;
      plan.verification={...(plan.verification||{risk:plan.shape==='risk',networkReadOnly:true,channelTests:[]}),tiers:[1,2,3,...selected.map(s=>s.tier)],costConsent:selected.some(s=>s.tier===4)};
      if(selected.some(s=>s.tier===5)){
        const choices=channelTestChoices(plan,this.comms);
        if(choices.length){
          const tests=await vscode.window.showQuickPick(choices.map(c=>({...c,
            description:'Destination and exact content are reviewed privately before sending.'})),
            {title:'Choose channel test requests; no messages are sent now',canPickMany:true});
          if(!tests)return;
          Object.assign(plan,setChannelTests(plan,tests.map(t=>t.key),this.comms));
        }else await vscode.window.showInformationMessage('No selected channel currently has an available message-test adapter. Its message results will remain unverified.');
      }
      this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='resolve'){
      const chosen=await vscode.window.showQuickPick<{label:string}>((plan.unresolved||[]).map((id:string)=>({label:id})),{title:'Select decisions you have resolved in this draft',canPickMany:true});
      if(!chosen)return;plan.unresolved=(plan.unresolved||[]).filter((id:string)=>!chosen.some(item=>item.label===id));
      this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='shape'){
      const shape=await choose('Installation shape',[{id:'focused',title:'Focused claw',description:'One runtime with selected capabilities.'},{id:'risk',title:'Risk',description:'One Border routes to independent members.'}]);
      if(!shape)return;
      const preview=this.draft!.preview({path:'/shape',value:shape});
      if(preview.discarded.length&&(await vscode.window.showWarningMessage('Review the choices affected by this shape change.',{modal:true,detail:preview.discarded.join('\n')+'\nThe primary harness, provider and channel choices are preserved.'},'Change shape'))!=='Change shape')return;
      this.draft!.update({path:'/shape',value:shape},state.revision,true);await this.persist();return;
    }
    if(type==='claw'){await this.configureClaw(message.owner);return;}
    if(type==='component'){
      const claw=plan.claws?.find((c:any)=>c.id===message.owner),component=this.catalog.components.find((c:any)=>c.id===message.component);
      if(!claw||!component)throw Error('Select a known claw and capability.');
      if(plan.host&&!component.platforms.includes(plan.host.platform))throw Error(component.platformReason);
      if(!claw.capabilities)throw Error('Choose the capability profile again after the source change.');
      const selected=new Set<string>(claw.capabilities.components),remove=selected.has(component.id);
      if(!remove&&this.adapters.unavailableComponents?.[component.id])throw Error(this.adapters.unavailableComponents[component.id].reason);
      if(remove){selected.delete(component.id);
        if(this.catalog.components.some((c:any)=>selected.has(c.id)&&c.dependencies.some((d:string)=>!selected.has(d))))throw Error('Remove dependent capabilities first.');
      }else{
        const add=(id:string)=>{if(selected.has(id))return;selected.add(id);this.catalog.components.find((c:any)=>c.id===id)?.dependencies.forEach(add);};add(component.id);
      }
      claw.capabilities.components=[...selected];claw.capabilities.skills=claw.capabilities.skills.filter((id:string)=>this.catalog.skills.find((s:any)=>s.id===id)?.components.every((c:string)=>selected.has(c)));
      if(remove&&component.id==='zoom-rtms')plan=setZoomBinding(plan,claw.id,null);
      if(remove&&component.id==='pyats')delete claw.testbed;
      this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='settings'){await this.configureSettings(message.owner);return;}
    if(type==='testbed'){
      const owner=plan.claws?.find((c:any)=>c.id===message.owner);if(!owner?.capabilities?.components?.includes('pyats'))throw Error('Select pyATS first.');
      const mode=await choose('Testbed mode · '+owner.displayName,[{id:'static',description:'Reviewed YAML, JSON or CSV file; existing behavior.'},{id:'dynamic',description:'Compose selected source inventory through MCP; review and activate later.'}]);
      if(!mode)return;
      let sources:string[]=[];
      if(mode==='dynamic'){
        const picked=await vscode.window.showQuickPick(this.testbedSources.map(s=>({id:s.id,label:s.label,
          description:s.upstreamNative?'Upstream native source · managed composition':'MCP or reviewed export',detail:s.help,
          picked:owner.testbed?.sources?.includes(s.id)})),{title:'Dynamic testbed sources · no source fetch or device connection during setup',canPickMany:true,ignoreFocusOut:true});
        if(!picked)return;if(!picked.length)throw Error('Select at least one dynamic source.');sources=picked.map(s=>s.id);
        if((plan.inventory||[]).some((i:any)=>i.owner===owner.id)&&
          (await vscode.window.showWarningMessage('Replace this claw’s planned static import with dynamic inventory?',{modal:true,detail:'The source file stays unchanged. The new plan will configure selected dynamic sources; build, validation and activation happen later.'},'Use dynamic inventory'))!=='Use dynamic inventory')return;
      }
      plan=setTestbed(plan,owner.id,{mode:mode as 'static'|'dynamic',sources},this.testbedSources);
      this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='cleanup'){
      const reference=this.runs.saved();if(!reference)throw Error('No setup run is saved.');
      const engine=this.engine||(this.engine=new SetupEngine('python3',reference.source));
      const proposed=await engine.read('cleanup-preview',undefined,reference.runId);
      const doc=await vscode.workspace.openTextDocument({language:'json',content:JSON.stringify(proposed.preview,null,2)});await vscode.window.showTextDocument(doc,{preview:false});
      const result=await engine.execute(reference.planFile,{event:()=>{},secret:async()=>undefined,review:async binding=>{
        if(canonical(binding)!==canonical(proposed.binding))throw Error('Cleanup changed. Preview it again.');
        const hasServices=proposed.preview.services?.length>0,action=hasServices?'Stop services and clean up':'Clean up listed files';
        return (await vscode.window.showWarningMessage(hasServices?'Stop the listed owned services and remove this run’s unchanged files?':'Remove only the listed, unchanged files created by this run?',{modal:true,detail:(hasServices?'Stopping these services can interrupt conversations and federation work. Cleanup verifies shutdown before removing service definitions, enable links and runtime files. ':'')+'Pre-existing, shared, edited and ambiguous artifacts are retained. Unverified service ownership retains the whole installation. Directories and audit evidence remain. This run cannot resume installation after cleanup begins.'},action))===action;
      }},reference.runId,{operation:'cleanup'});
      const report=await vscode.workspace.openTextDocument({language:'json',content:JSON.stringify(result,null,2)});await vscode.window.showTextDocument(report,{preview:false});
      await vscode.window.showInformationMessage(`Cleanup removed ${result.removed} files; retained ${result.retained} listed artifacts; ${result.alreadyAbsent||0} were already absent. Directories and audit evidence remain. The local report lists every outcome.`);return;
    }
    if(type==='inventory'||type==='identity'){
      const owner=plan.claws?.find((c:any)=>c.id===message.owner);if(!owner)throw Error('Select a claw first.');
      if(type==='inventory'&&owner.testbed?.mode==='dynamic')throw Error('Choose Static in Testbed mode before importing a file. Dynamic sources are composed after setup.');
      const chosen=await vscode.window.showOpenDialog({canSelectMany:false,canSelectFiles:true,canSelectFolders:false,title:type==='inventory'?'Choose reviewed YAML, JSON or CSV inventory':'Choose identity, user or soul Markdown'});
      if(!chosen?.[0])return;const file=chosen[0].fsPath;realParents(file);const info=fs.lstatSync(file);
      if(!info.isFile()||info.size>(type==='inventory'?256*1024:64*1024))throw Error(type==='inventory'?'Choose an inventory file no larger than 256 KiB.':'Choose an identity file no larger than 64 KiB.');
      const kind=type==='identity'?await choose('Identity file purpose',[{id:'soul'},{id:'user'},{id:'identity'}]):({'.yaml':'testbed-yaml','.yml':'testbed-yaml','.json':'testbed-json','.csv':'testbed-csv'} as any)[path.extname(file).toLowerCase()];
      if(!kind)throw Error('Choose a supported file format.');
      plan[type]=[...(plan[type]||[]).filter((i:any)=>!(i.owner===owner.id&&(type==='inventory'||i.kind===kind))),{owner:owner.id,kind,path:file,sha256:hash(fs.readFileSync(file))}];
      this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='posture'){
      const mode=await choose('Requested posture',[{id:'testing',description:'Local testing; no claim of production enforcement.'},{id:'production',description:'Stops unless every required host and claw control is verified.'}]);
      if(!mode)return;plan.posture={mode,requiredControls:[]};this.draft!.replace(plan,state.revision);await this.persist();return;
    }
    if(type==='save'){
      const target=await vscode.window.showSaveDialog({title:'Save non-secret Claw Plan',filters:{'Claw Plan':['json']}});
      if(target){realParents(target.fsPath);fs.writeFileSync(target.fsPath,canonical(plan)+'\n',{flag:'wx',mode:0o600});}return;
    }
    if(type==='import'){
      const target=await vscode.window.showOpenDialog({canSelectMany:false,filters:{'Claw Plan':['json']}});
      if(target?.[0]){this.draft!.replace(readData(target[0].fsPath),state.revision);await this.persist();}return;
    }
    if(['report','export-report','export-detailed','verify'].includes(type)){
      const reference=this.runs.saved();if(!reference)throw Error('No owned setup run is saved.');
      const engine=this.engine||(this.engine=new SetupEngine('python3',reference.source));
      if(engine.source!==reference.source)throw Error('Select the original source for this run.');
      if(type==='report')await showReport(engine,reference);
      else if(type==='verify'){
        this.runs.begin();const saved=this.runs.plan(reference);
        this.run=await engine.execute(reference.planFile,{review:binding=>reviewLive(saved,binding),destination:channelDestination,choice:async(_binding,title,choices)=>vscode.window.showQuickPick(choices,{title}),secret:secretInput,event:event=>{void this.runs.event(event,saved,reference.planFile).catch(()=>engine.pause());void this.view?.webview.postMessage({type:'progress',event});}},reference.runId,{operation:'verify'});
        await this.runs.event(this.run,saved,reference.planFile);await showReport(engine,reference);
      }else await exportReport(engine,reference,type==='export-detailed');
      return;
    }
    if(type==='validate'||type==='apply'||type==='resume'){
      const reference=type==='resume'?this.runs.saved():undefined;
      if(type==='resume'){
        if(!reference)throw Error('No run is available to resume.');
        plan=this.runs.plan(reference);
        if(hash(canonical(plan))!==state.hash){
          const choice=await vscode.window.showWarningMessage('Restore the saved plan for this run?',{modal:true,detail:'Resume uses the original, exact plan. Your current draft will be replaced only if you continue.'},'Restore saved run plan');
          if(choice!=='Restore saved run plan')return;
          this.draft!.replace(plan,state.revision);await this.persist();
        }
      }
      if(!plan.source)throw Error('Choose and review the source checkout first.');
      const engine=this.engine||(this.engine=new SetupEngine('python3',plan.source.path));
      if(engine.source!==plan.source.path)throw Error('Select the original source for this run.');
      const file=reference?.planFile||await this.planFile();const report=await engine.read('explain',file);
      if(type==='validate'||!report.applyReady){await this.view?.webview.postMessage({type:'validation',report});return;}
      this.runs.begin();
      this.run=await engine.execute(file,{terminal:openNativeTerminal,review:async binding=>{
        const accepted=await reviewPlan(plan,binding,report);
        if(accepted){
          // A newly reviewed installation must not show the previous run's
          // status alongside its progress. Keep the saved recovery reference
          // until the engine supplies the new run's authoritative identity.
          if(!reference)this.run=undefined;
          this.view?.reveal();await this.render();
        }
        return accepted;
      },destination:channelDestination,choice:async(_binding,title,choices)=>vscode.window.showQuickPick(choices,{title}),secret:(owner,key)=>this.setupCredential(owner,key),
        event:event=>{if(event.runId){this.run={...this.run,runId:event.runId,state:event.state};void this.runs.event(event,plan,file).catch(()=>engine.pause());}void this.view?.webview.postMessage({type:'progress',event});}},reference?.runId);
      await this.runs.event(this.run,plan,file);await this.runs.settled();return;
    }
    throw Error('Unknown setup action.');
  }
  private async planFile(){
    const directory=path.join(this.context.globalStorageUri.fsPath,'setup');realParents(directory);fs.mkdirSync(directory,{recursive:true,mode:0o700});
    const file=path.join(directory,'plan-'+randomUUID()+'.json');fs.writeFileSync(file,canonical(this.draft!.snapshot().answers)+'\n',{mode:0o600,flag:'wx'});return file;
  }
  private async selectSource(){
    const choice=await choose('NetClaw source',[{id:'existing',title:'Use an existing checkout as-is'},{id:'release',title:'Latest published release'},{id:'main',title:'Main branch'},{id:'tag',title:'Explicit tag'}]);if(!choice)return;
    let selected:any;
    if(choice==='existing'){
      const folder=await vscode.window.showOpenDialog({canSelectFolders:true,canSelectFiles:false,canSelectMany:false,title:'NetClaw checkout'});if(!folder?.[0])return;
      selected={channel:'existing',ref:'HEAD',...await inspectSource(folder[0].fsPath)};
      if((await vscode.window.showInformationMessage('Use this NetClaw source?',{modal:true,detail:`${selected.path}\nCommit: ${selected.commit}\n${selected.dirty?'Contains local changes. This exact tree is used as-is.':'Clean checkout.'}\nSetup reads its protocol/catalog and runs its Python engine. Each claw gets private build files.`},'Use reviewed source'))!=='Use reviewed source')return;
    }else{
      const ref=choice==='tag'?await input('Source tag','Exact NetClaw tag'):undefined;if(choice==='tag'&&!ref)return;
      const resolved=await resolveSelection(choice as 'release'|'main'|'tag',ref);
      const destination=await input('New source directory','Absolute new or empty directory');if(!destination)return;
      if((await vscode.window.showInformationMessage('Download this NetClaw source?',{modal:true,detail:`${resolved.provenance} · ${resolved.ref}\n${resolved.commit}\nDestination: ${destination}\nExisting checkouts are preserved.`},'Download source'))!=='Download source')return;
      selected=await acquireSource(resolved,destination,{reviewed:true,record:value=>this.local.update('setup-source-acquisition',value)});
    }
    const candidate=new SetupEngine('python3',selected.path);
    const host=await candidate.read('observe-host'),state=this.draft!.snapshot();
    const source={channel:selected.channel,ref:selected.ref,commit:selected.commit,treeHash:selected.treeHash,path:selected.path,dirty:selected.dirty};
    const plan={...state.answers,schema:1,host,source,assumptions:state.answers.assumptions||[],unresolved:state.answers.unresolved||[]} as any;
    if(state.answers.source&&hash(canonical(state.answers.source))!==hash(canonical(source))&&state.answers.claws?.length){
      if((await vscode.window.showWarningMessage('Review choices affected by this source change.',{modal:true,
        detail:'The new catalog invalidates capability selections and their settings. Names, homes, harnesses, providers and input references remain in the draft.'},'Discard dependent choices'))!=='Discard dependent choices')return;
      for(const claw of plan.claws){delete claw.capabilities;delete claw.settings;}
      plan.unresolved=[...new Set([...plan.unresolved,'review-source-capabilities'])];
    }
    // Frontends use the chosen source's data once it is explicitly trusted.
    const catalog=readData(path.join(selected.path,'config/components/catalog.json'),16*1024*1024);
    const comms=readData(path.join(selected.path,'config/components/comms.json'),4*1024*1024);validateComms(comms,readData(path.join(selected.path,'config/components/comms.schema.json')));
    const adapters=readData(path.join(selected.path,'config/components/harness-adapters.json'));
    const draft=new SetupDraft(readData(path.join(selected.path,'config/claw-plan.schema.json')),catalog);
    draft.replace(plan,0);this.engine?.dispose();this.engine=candidate;
    this.catalog=catalog;this.comms=comms;this.adapters=adapters;this.draft=draft;await this.persist();
  }
  private async primaryChoice(kind:'harness'|'provider',owner?:string){
    let state=this.draft!.snapshot(),plan=state.answers;
    const index=owner?plan.claws?.findIndex((c:any)=>c.id===owner):0;
    if(index===undefined||index<0)throw Error('Select a claw.');
    if(!plan.claws?.length){
      plan.claws=[{id:'claw-'+randomUUID().replaceAll('-','').slice(0,12),settings:{},channels:[]}];
      this.draft!.replace(plan,state.revision);state=this.draft!.snapshot();plan=state.answers;
    }
    const claw=plan.claws[index];
    if(kind==='harness'){
      const selected=await choose('Agent harness',[...(claw.role==='member'?[{id:'inherit',title:'Inherit Border harness'}]:[]),{id:'openclaw',title:'OpenClaw'},{id:'hermes',title:'Hermes'}]);if(!selected)return;
      const harness=selected==='inherit'?plan.claws[0].harness:selected;
      if(!harness)throw Error('Choose the Border harness first.');
      const change={path:`/claws/${index}/harness`,value:harness},preview=this.draft!.preview(change);
      if(preview.discarded.length&&(await vscode.window.showWarningMessage('Review dependent choices before changing the harness.',{modal:true,detail:preview.discarded.join('\n')},'Change harness'))!=='Change harness')return;
      this.draft!.update(change,state.revision,true);state=this.draft!.snapshot();plan=state.answers;
      plan.claws[index].harnessChoice=selected==='inherit'?'inherit':'explicit';
      for(const c of plan.claws)if(c.harness){c.runtimeVersion=this.adapters[c.harness].versions[0];c.settings=c.settings||{};c.channels=c.channels||[];if(c.runtimeHome)c.workspace=c.harness==='hermes'?c.runtimeHome:path.join(c.runtimeHome,'workspace');}
    }else{
      if(!claw.harness)throw Error('Choose the harness first.');
      const provider=await this.providerChoice(claw.harness,claw);if(!provider)return;
      const change={path:`/claws/${index}/provider`,value:provider},preview=this.draft!.preview(change);
      if(preview.discarded.length&&(await vscode.window.showWarningMessage('Review credential references affected by changing the provider.',{modal:true,detail:preview.discarded.join('\n')},'Change provider'))!=='Change provider')return;
      this.draft!.update(change,state.revision,true);state=this.draft!.snapshot();plan=state.answers;
      const current=plan.claws[index];current.settings=current.settings||{};
      for(const key of provider.credentialKeys)current.settings[key]={kind:'secret',key,owner:current.id,source:'prompt'};
    }
    this.draft!.replace(plan,state.revision);await this.persist();
  }
  private async providerChoice(harness:string,existing?:any):Promise<any|undefined>{
    const provider=await choose('Model provider',this.catalog.choices.filter((c:any)=>c.kind==='provider'&&c.harnesses.includes(harness)));if(!provider)return;
    const kind=['ollama','lm-studio'].includes(provider)?'local':provider==='custom'?await choose('Endpoint location',[{id:'local'},{id:'cloud'}]):'cloud';if(!kind)return;
    const apiMode=await choose('Provider API mode',this.adapters.providerApiModes[provider].filter((id:string)=>Object.hasOwn(this.adapters[harness].apiModes,id)).map((id:string)=>({id})));if(!apiMode)return;
    const suggested=provider==='ollama'?'http://127.0.0.1:11434'+(apiMode==='ollama'?'':'/v1'):provider==='lm-studio'?'http://127.0.0.1:1234/v1':undefined;
    const endpoint=kind==='local'||provider==='custom'?await input('Provider endpoint','Explicit HTTP(S) URL. Local models use loopback.',existing?.provider?.id===provider?existing.provider.endpoint:suggested):'';if(endpoint===undefined)return;
    let model:string|undefined;
    if(this.engine&&(provider==='ollama'||provider==='lm-studio')){model=await selectLocalModel(this.engine,provider,endpoint,existing?.runtimeHome||os.homedir());if(model===undefined)return;}
    if(!model)model=await input('Model','Exact model identifier. Listing models does not prove inference works.',existing?.provider?.id===provider?existing.provider.model:undefined);if(!model)return;
    const credentialKeys:string[]=[];
    for(const field of this.catalog.choices.find((c:any)=>c.kind==='provider'&&c.id===provider).settings.filter((f:any)=>f.classification==='secret')){
      const auth=field.required==='always'?'key':await choose('Endpoint authentication',[{id:'key',title:'API key',description:'Enter securely during installation.'},{id:'none',title:'No authentication',description:'Only for a server configured without authentication.'}]);if(!auth)return;
      if(auth==='key')credentialKeys.push(field.key);
    }
    return {id:provider,kind,model,apiMode,endpoint,credentialKeys};
  }
  private async configureClaw(owner?:string){
    const state=this.draft!.snapshot(),plan=state.answers;if(!plan.shape)throw Error('Choose Focused or Risk first.');
    const existing=plan.claws?.find((c:any)=>c.id===owner),index=existing?plan.claws.indexOf(existing):(plan.claws||[]).length;
    if(plan.shape==='focused'&&index>0)throw Error('A Focused setup has one claw. Choose Risk to add members.');
    const role=plan.shape==='focused'?'focused':index===0?'border':'member';
    const name=await input('Name this '+role,'Friendly name shown when managing multiple installations',existing?.displayName);if(!name)return;
    const id=existing?.id||'claw-'+randomUUID().replaceAll('-','').slice(0,12);
    const home=await input('Separate runtime home','Absolute new or empty directory. Existing homes cannot be adopted.',existing?.runtimeHome||path.join(os.homedir(),'NetClaws',id));if(!home)return;realParents(home);
    const selected=existing?.harness?(existing.harnessChoice==='inherit'?'inherit':existing.harness):await choose('Agent harness',[...(role==='member'?[{id:'inherit',title:'Inherit Border harness'}]:[]),{id:'openclaw',title:'OpenClaw'},{id:'hermes',title:'Hermes'}]);if(!selected)return;
    const harness=selected==='inherit'?plan.claws[0].harness:selected;
    const chosenProvider=existing?.provider||await this.providerChoice(harness,{runtimeHome:home});if(!chosenProvider)return;
    const {id:provider,kind,model,apiMode,endpoint,credentialKeys}=chosenProvider;
    const profiles=role==='member'?this.catalog.memberProfiles.filter((p:any)=>p.harnesses.includes(harness)):this.catalog.profiles;
    const profile=await choose('Capability profile',profiles);if(!profile)return;const descriptor=profiles.find((p:any)=>p.id===profile);
    if(existing?.capabilities&&existing.capabilities.profile!==profile&&(await vscode.window.showWarningMessage('Replace this claw’s selected capabilities?',{modal:true,detail:'The selected profile replaces component and skill choices. Settings used only by removed capabilities are discarded. Other claws keep their profiles.'},'Replace capabilities'))!=='Replace capabilities')return;
    const components=role==='border'?['gait','protocol','n2n']: [...new Set([...descriptor.components,...(role==='member'?['n2n']:[])])];
    if(role==='member'&&profile==='comms'){
      const tools=this.catalog.components.filter((c:any)=>['twilio','zoom-rtms'].includes(c.id));
      const selected=await vscode.window.showQuickPick(tools.map((c:any)=>({label:c.title,description:c.description,id:c.id,picked:existing?.capabilities?.components?.includes(c.id)})),{title:'Comms member · select tools',canPickMany:true});
      if(!selected?.length)return;components.push(...selected.map((c:any)=>c.id));
    }
    const skills=role==='member'?[...descriptor.skills]:this.catalog.skills.filter((s:any)=>s.availability==='supported'&&s.components.length&&s.components.every((id:string)=>components.includes(id))).map((s:any)=>s.id);
    if(role==='member'&&profile==='comms')skills.push(...this.catalog.skills.filter((s:any)=>s.availability==='supported'&&s.components.length&&s.components.every((id:string)=>components.includes(id))).map((s:any)=>s.id));
    const mode=role==='member'?await choose('Member lifecycle',[{id:'hot',description:'Keep the member worker running.'},{id:'on-demand',description:'Start the worker when invoked; local management services stay available.'}]):'hot';if(!mode)return;
    const claw:any={id,displayName:name,role,runtimeHome:home,workspace:harness==='hermes'?home:path.join(home,'workspace'),harness,harnessChoice:selected==='inherit'?'inherit':'explicit',runtimeVersion:this.adapters[harness].versions[0],
      provider:{id:provider,kind,model,apiMode,endpoint,credentialKeys},channels:existing?.channels||[],capabilities:{profile,components,skills,trustDomain:id},
      settings:{...existing?.settings,...Object.fromEntries(credentialKeys.map((key:string)=>[key,{kind:'secret',key,owner:id,source:'prompt'}]))},
      endpoints:existing?.endpoints||{gatewayPort:18789+index*20,hudPort:3001+index*20,hudUiPort:3000+index*20,companionPort:8643+index*20,bgpApiPort:8179+index*20,bgpPort:1179+index*20,federationPort:8000+index*20},service:{name:'netclaw-'+id,mode}};
    if(existing&&existing.harness===harness&&existing.provider?.id===provider&&existing.capabilities?.profile===profile){
      claw.settings={...existing.settings,...claw.settings};claw.channels=existing.channels;claw.capabilities=existing.capabilities;
    }
    if(claw.capabilities.components.includes('pyats')&&existing?.testbed)claw.testbed=existing.testbed;
    const retained=new Set<string>([...credentialKeys,...claw.channels.flatMap((c:any)=>c.settingKeys||[]),
      ...this.catalog.components.filter((c:any)=>claw.capabilities.components.includes(c.id)).flatMap((c:any)=>c.settings.map((f:any)=>f.key))]);
    for(const key of Object.keys(claw.settings))if(!retained.has(key))delete claw.settings[key];
    if(role==='border'&&existing&&existing.harness!==harness){
      const inherited=(plan.claws||[]).filter((c:any)=>c.role==='member'&&c.harnessChoice==='inherit');
      if(inherited.length&&(await vscode.window.showWarningMessage('Update inherited member harnesses?',{modal:true,detail:inherited.map((c:any)=>c.displayName).join(', ')+' will use '+harness+'. Review their provider and capability compatibility before applying.'},'Update inherited members'))!=='Update inherited members')return;
      for(const member of inherited){member.harness=harness;member.workspace=harness==='hermes'?member.runtimeHome:path.join(member.runtimeHome,'workspace');member.runtimeVersion=this.adapters[harness].versions[0];plan.unresolved=[...new Set([...(plan.unresolved||[]),'review-member-harness-'+hash(member.id).slice(0,12)])];}
    }
    plan.claws=plan.claws||[];plan.claws[index]=claw;plan.inventory=plan.inventory||[];plan.identity=plan.identity||[];
    if(!claw.capabilities.components.includes('zoom-rtms')&&plan.commsBindings)plan.commsBindings=plan.commsBindings.filter((b:any)=>b.owner!==id);
    plan.verification={...(plan.verification||{tiers:[1,2,3],costConsent:false,networkReadOnly:true,channelTests:[]}),risk:plan.shape==='risk'};
    this.draft!.replace(plan,state.revision);await this.persist();
  }
  private async configureSettings(owner:string){
    const state=this.draft!.snapshot(),plan=state.answers,claw=plan.claws?.find((c:any)=>c.id===owner);if(!claw)throw Error('Select a claw.');
    if(!claw.capabilities||!claw.settings)throw Error('Choose the claw profile again after the source change.');
    const entries=[...this.catalog.components.filter((c:any)=>claw.capabilities.components.includes(c.id)),
      ...this.catalog.choices.filter((c:any)=>c.kind==='harness'&&c.id===claw.harness||c.kind==='provider'&&c.id===claw.provider.id),
      ...(claw.channels||[]).map((c:any)=>({settings:channelFields(claw,c.id,this.catalog,this.comms)}))];
    const fields=new Map<string,any>();for(const entry of entries)for(const field of entry.settings)if(field.input==='user'){
      const old=fields.get(field.key);if(!old||old.classification!=='secret')fields.set(field.key,field);
    }
    const key=await choose('Settings for '+claw.displayName,[...fields.values()].map(f=>({id:f.key,title:f.label,description:f.required+' · '+f.classification})));if(!key)return;
    const field=fields.get(key);
    if(field.classification==='secret'){
      const source=await choose(field.label,[{id:'prompt',title:'Prompt securely during installation'},{id:'later',title:'Configure later'}]);if(!source)return;
      claw.settings[key]={kind:'secret',key,owner,source};
      if(this.catalog.choices.find((c:any)=>c.kind==='provider'&&c.id===claw.provider.id)?.settingKeys.includes(key)&&!claw.provider.credentialKeys.includes(key))claw.provider.credentialKeys.push(key);
    }else if(key==='NETCONVERTER_MODE'){
      const mode=await choose('NetConverter mode · no file submission during setup',[
        {id:'hosted-readonly',title:'Hosted read-only',description:'Review existing job evidence using your enabled account.'},
        {id:'local-terminal',title:'Local Terminal',description:'Operator-installed licensed client; exact-file approval before each submission.'}]);
      if(!mode)return;
      claw.settings[key]={kind:'value',value:mode};
    }else{
      const value=await input(field.label,field.help,claw.settings[key]?.value?.toString());if(value===undefined)return;
      const typed=field.valueType==='integer'?Number(value):field.valueType==='boolean'?value==='true'?true:value==='false'?false:undefined:value;
      if(typed===undefined||typeof typed==='number'&&!Number.isSafeInteger(typed))throw Error('Enter a valid '+field.valueType+'.');
      claw.settings[key]={kind:'value',value:typed};
    }
    this.draft!.replace(plan,state.revision);await this.persist();
  }
  dispose(){this.clearSetupSecrets();this.engine?.dispose();this.view?.dispose();}
}
