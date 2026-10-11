import fs from 'node:fs';
import path from 'node:path';
import yaml from 'js-yaml';
import { randomUUID } from 'node:crypto';
import { bindInstallation } from './identity.js';
import { Journal } from './journal.js';
import { InstallationAudit,redactor,bounded } from './evidence.js';
import { Proposals } from './proposals.js';
import { configurationAdapters,configurationSnapshot,environment,secretField } from './configuration.js';
import { readOwned } from './files.js';
import { fail,invariant } from './errors.js';
import { authorize } from './policy.js';
import { federationReader } from './federation.js';
import { runtimeSettings,hermesRuntimeSettings } from '../hud-server/runtime-settings.js';
import { runtimeInventory,readUsage } from '../hud-server/tokenomics.js';
import { gatewayAgentId } from '../hud-server/gateway-agent.js';
import { securitySettings } from '../hud-server/security-posture.js';
import { ENV_MAP } from '../hud-server/integration-environment.js';
import { documentContent } from '../hud-server/documentation.js';
import { ClientGrants } from './clients.js';
import { startOwnedWorker } from './worker.js';
import { Conversations } from './conversations.js';
import { createManagementRuntime } from './chat-runtime.js';
import { Workspace } from './workspace.js';
import { RagClient } from './rag.js';

export class ManagementService {
  constructor({root,home,kind,expectedInstallationId,audit,adapters={},authority}) {
    this.root=root;this.binding=bindInstallation({home,kind,expectedInstallationId});
    this.journal=new Journal(path.join(this.binding.statePath,'management'),this.binding.installationId);
    this.audit=audit||new InstallationAudit(this.binding,root,this.journal);
    this.adapters={...configurationAdapters(this.binding),...adapters};
    this.proposals=new Proposals({binding:this.binding,journal:this.journal,audit:this.audit,adapters:this.adapters,authority});
    this.clients=new ClientGrants({binding:this.binding,journal:this.journal,audit:this.audit});
    this.runtime=createManagementRuntime(this.binding,root);
    this.workspace=new Workspace({binding:this.binding,journal:this.journal,audit:this.audit,clean:value=>this.clean(value),rag:new RagClient(this.binding,root),start:operationId=>startOwnedWorker({root,binding:this.binding,operationId})});
    this.conversations=new Conversations({binding:this.binding,journal:this.journal,audit:this.audit,runtime:this.runtime,
      start:operationId=>startOwnedWorker({root,binding:this.binding,operationId}),clean:value=>this.clean(value)});
    this.readFederation=federationReader(this.binding,()=>environment(this.binding));
    this.journal.reconcileExpired();
  }
  config(){const data=readOwned(this.binding.configPath,{limit:4*1024*1024}).toString();return this.binding.kind==='hermes'?yaml.load(data):JSON.parse(data);}
  clean(value){const values=environment(this.binding);return bounded(redactor(Object.entries(values).filter(([key])=>secretField(key)).map(([,value])=>value))(value));}
  envelope(data,source,warnings=[]){return this.clean({contractVersion:1,installationId:this.binding.installationId,source,observedAt:new Date().toISOString(),data,freshness:'observed',warnings});}
  identity(){
    const config=this.config(),env=environment(this.binding),role=env.N2N_ROLE||env.N2N_RISK_ROLE||'unknown';
    return this.clean({contract:{major:1,minor:0},installationId:this.binding.installationId,principalId:this.binding.principal.principalId,
      hostId:this.binding.hostId,sourceVersion:fs.readFileSync(path.join(this.root,'VERSION'),'utf8').trim(),harness:{type:this.binding.kind,version:null,versionSource:'Not probed'},
      role,configurationRevision:this.proposals.revision(),observedAt:new Date().toISOString(),
      capabilities:{inspection:{supported:true,qualified:true},changes:Object.keys(this.adapters).map(action=>({action,supported:true,qualified:this.adapters[action].qualified===true})),
        delegation:{supported:false,qualified:false,reason:'Runtime grant propagation and durable conversation adapters must be qualified before dispatch.'}},
      runtimeSettings:this.binding.kind==='hermes'?hermesRuntimeSettings(config,'Selected installation'):runtimeSettings(config,0,'Selected installation')});
  }
  paginate(rows,input){
    const offset=input.cursor?Number(input.cursor):0;invariant(Number.isSafeInteger(offset)&&offset>=0);
    const limit=input.limit??100;invariant(limit<=500&&limit>0);
    return {items:rows.slice(offset,offset+limit),total:rows.length,...(offset+limit<rows.length?{nextCursor:String(offset+limit)}:{})};
  }
  async resources(principal,input){
    authorize(principal,'inspect',[]);
    if(input.kind==='overview'){
      if(input.filters?.query&&/^\d{13}:[a-f\d-]{36}$/.test(input.filters.query))return this.envelope({operation:this.journal.byNonce(principal,input.filters.query)},'Durable admission lookup; no dispatch');
      return this.envelope({identity:this.identity(),operations:this.journal.list(principal)},'Selected installation and durable management journal');
    }
    if(['member','peer','edge'].includes(input.kind)){
      const result=await this.readFederation(input.kind);
      // Return typed source data, retaining actual server state rather than inventing health.
      return this.envelope(result.value,result.source,[result.qualification]);
    }
    if(input.kind==='integration'){
      const inventory=runtimeInventory(this.config()),servers=new Map(inventory.mcp_servers.map(s=>[s.name,s]));
      const rows=Object.entries(ENV_MAP).map(([id,mapping])=>({id,notes:mapping.notes,configuration:mapping.env.map(key=>({key,isSet:Boolean(environment(this.binding)[key])})),
        registered:servers.has(id)||servers.has(`${id}-mcp`),discovered:null,reachable:null,executionVerified:null,source:'Static NetClaw catalog and selected runtime configuration'}));
      return this.envelope(this.paginate(rows,input),'Selected installation configuration');
    }
    if(input.kind==='skill'){
      const directory=path.join(this.binding.home,this.binding.kind==='hermes'?'skills':'workspace/skills');
      const entries=fs.existsSync(directory)?fs.readdirSync(directory,{withFileTypes:true}).filter(e=>e.isDirectory()&&!e.isSymbolicLink()):[];
      const rows=entries.filter(e=>fs.existsSync(path.join(directory,e.name,'SKILL.md'))).map(e=>({id:e.name,installed:true,executionVerified:null,source:'Installed skill directory'}));
      return this.envelope(this.paginate(rows,input),'Selected installation skill files');
    }
    if(input.kind==='advisor')return this.envelope({enabled:environment(this.binding).JEV_ENABLED==='true',role:'advice-only',taskOwnedAssessments:this.journal.records('assessment',principal)},'Selected installation settings and owned assessments');
    if(input.kind==='network')return this.envelope({available:false,reason:'No current network observations collected by this management session.',sources:['configured','observed','historical','simulated','federation']},'Management observation boundary');
    fail('UNSUPPORTED');
  }
  snapshot(principal,input){
    authorize(principal,'inspect',[]);
    if(input.domain==='settings')return this.envelope({revision:this.proposals.revision(),runtime:this.identity().runtimeSettings,environment:configurationSnapshot(this.binding)},'Selected installation configuration');
    if(input.domain==='usage'){
      const data=this.binding.kind==='hermes'?{available:false,reason:'Hermes usage is scoped to owned completed requests; no aggregate is available.'}:readUsage(path.join(this.binding.home,'agents',gatewayAgentId(this.config()),'sessions'));
      return this.envelope({...data,externalAssistantUsage:null,billingNote:'NetClaw usage excludes Copilot, Claude Code and Codex inference.'},'Selected runtime retained usage');
    }
    if(input.domain==='security')return this.envelope({...securitySettings(environment(this.binding),null,null),effective:'unverified',hostConfinement:'unverified',openshell:'unverified',reason:'Stored mode is not evidence of runtime enforcement.'},'Selected installation environment');
    if(input.domain==='documentation'){
      const entries=JSON.parse(fs.readFileSync(path.join(this.root,'docs/reference/documents.json'),'utf8'));
      if(input.resourceId)return this.envelope(documentContent(this.root,entries,input.resourceId),'Bundled NetClaw documentation');
      return this.envelope(this.paginate(entries,input),'Bundled NetClaw documentation index');
    }
    if(input.domain==='knowledge')return this.envelope(this.workspace.snapshot(principal,input.resourceId),'Owned workspace artifacts');
    fail('UNSUPPORTED');
  }
  async call(name,args,principal=this.binding.principal){
    this.binding.assertCurrent();
    if(name==='operator_identity')return this.identity();
    if(name==='operator_resources')return this.resources(principal,args);
    if(name==='operator_snapshot')return this.snapshot(principal,args);
    if(name==='operator_workspace')return this.workspace.call(principal,args);
    if(name==='operator_operation_get'){
      const value=this.journal.get(principal,args.operationId);
      if(value.state==='unknown'&&value.kind==='conversation-request')return this.clean(await this.conversations.reconcile(principal,args.operationId));
      return this.clean(value);
    }
    if(name==='operator_request_submit')return this.clean(await this.conversations.submit(principal,args));
    if(name==='operator_cancel_request')return this.clean(await this.conversations.cancel(principal,args));
    if(name==='operator_events')return this.envelope({events:this.journal.events(principal,args.operationId,args.after,args.limit)},'Durable management events');
    if(name==='operator_change_prepare')return this.clean(await this.proposals.prepare(principal,args));
    if(name==='operator_client_prepare')return this.clients.prepare(principal,args);
    if(name==='operator_client_apply')return this.clients.apply(principal,args);
    if(name==='operator_client_revoke')return this.clients.revoke(principal,args);
    if(name==='operator_change_apply'){
      invariant(principal.surface==='operator','DENIED');
      this.journal.record('proposal',args.proposalId,principal);
      const lock=this.journal.lock('configuration',principal.principalId);
      let operation;
      try{operation=this.proposals.admitApply(principal,args);}finally{this.journal.unlock('configuration',lock);}
      if(operation.state==='admitted')await startOwnedWorker({root:this.root,binding:this.binding,operationId:operation.operationId,transient:{replacements:args.replacements||{}}});
      return operation;
    }
    if(name==='operator_evidence'){
      authorize(principal,'evidence',[]);
      if(args.kind==='gait')return this.envelope(await this.audit.log(args.limit),'Installation-specific GAIT');
      if(args.kind==='approval'&&args.id)return this.envelope(this.journal.record('proposal',args.id,principal),'Managed proposal');
      fail('UNSUPPORTED');
    }
    if(name==='operator_conversation_open'){
      return this.conversations.open(principal,args);
    }
    fail('UNQUALIFIED');
  }
  async close(){try{await this.runtime.close();await this.audit.close?.();}finally{this.journal.close();}}
}
