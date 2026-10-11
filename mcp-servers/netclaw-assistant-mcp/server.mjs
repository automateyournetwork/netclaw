import { McpServer } from '@modelcontextprotocol/server';
import { StdioServerTransport } from '@modelcontextprotocol/server/stdio';
import { schemas,parseAssistantInput } from './schemas.mjs';
import { safeError,fail,invariant } from '../../ui/netclaw-visual/src/management/errors.js';
import { authorize } from '../../ui/netclaw-visual/src/management/policy.js';

export async function assistantCall(service,credentialRef,name,raw){
  const input=parseAssistantInput(name,raw),grant=service.clients.resolve(credentialRef);
  if(name==='netclaw_status'){
    const identity=service.identity();return {installationId:identity.installationId,harness:identity.harness,role:identity.role,configurationRevision:identity.configurationRevision,
      capabilities:identity.capabilities,grant:{id:grant.grantId,generation:grant.generation,actions:grant.actions,targets:grant.targets,disclosure:grant.disclosure,expiresAt:grant.expiresAt},
      billing:'NetClaw usage does not include the external assistant’s inference.'};
  }
  if(name==='netclaw_inventory'){
    authorize(grant,'inspect',[]);
    invariant(['overview','integration','skill'].includes(input.kind),'DENIED');
    const result=await service.resources(grant,input);
    if(input.kind==='overview')return {installationId:service.binding.installationId,harness:service.binding.kind,operations:service.journal.list(grant)};
    // Minimal disclosure does not expose configured file paths, variable names or arbitrary descriptions.
    return {...result,data:{items:(result.data.items||[]).map(row=>({id:row.id,registered:row.registered,installed:row.installed,executionVerified:row.executionVerified})),total:result.data.total,...(result.data.nextCursor?{nextCursor:result.data.nextCursor}:{})}};
  }
  if(name==='netclaw_evidence'){
    authorize(grant,'evidence',[]);invariant(grant.disclosure.includes(input.kind==='usage'?'usage':'evidence'),'DENIED');
    if(input.kind==='usage')return service.envelope({scope:'This client grant’s owned operations',operations:service.journal.list(grant).map(({operationId,state,result})=>({operationId,state,usage:result?.usage??null}))},'Owned NetClaw request usage');
    fail('UNQUALIFIED');
  }
  if(name==='netclaw_propose_change'){
    authorize(grant,'propose',input.targets);const value=await service.proposals.prepare(grant,input);
    return {operationId:value.operationId,proposalId:value.proposalId,state:value.state,approvalRequired:true,review:'Human review and independent approval are required. This client cannot apply changes.'};
  }
  if(name==='netclaw_request_status'){
    authorize(grant,'inspect',[]);const result=input.requestId?service.journal.get(grant,input.requestId):service.journal.byNonce(grant,input.nonce);invariant(result,'DENIED');
    return service.clean({...result,...(!grant.disclosure.includes('conversation')?{result:result.result?{usage:result.result.usage??null,code:result.result.code,summary:'Owned result available for human review.'}:undefined}:{})});
  }
  if(name==='netclaw_request'){authorize(grant,'delegate',[service.binding.installationId]);fail('UNQUALIFIED');}
  if(name==='netclaw_cancel'){authorize(grant,'cancel',[]);service.journal.get(grant,input.requestId);fail('UNQUALIFIED');}
  fail('DENIED');
}
export function assistantServer(service,credentialRef){
  const server=new McpServer({name:'netclaw-assistant',version:'0.1.0'});
  for(const [name,inputSchema] of Object.entries(schemas))server.registerTool(name,{inputSchema,
    description:`Scoped NetClaw ${name.replace('netclaw_','').replaceAll('_',' ')}. No self-approval or private operator access.`,
    annotations:{readOnlyHint:['netclaw_status','netclaw_inventory','netclaw_evidence','netclaw_request_status'].includes(name),openWorldHint:false},
  },async args=>{
    try{const value=service.clean(await assistantCall(service,credentialRef,name,args));return{content:[{type:'text',text:JSON.stringify(value)}],structuredContent:value};}
    catch(error){const value={error:safeError(error)};return{isError:true,content:[{type:'text',text:JSON.stringify(value)}],structuredContent:value};}
  });return server;
}
export async function serveAssistant(service,credentialRef){service.clients.resolve(credentialRef);const server=assistantServer(service,credentialRef);await server.connect(new StdioServerTransport());return server;}
