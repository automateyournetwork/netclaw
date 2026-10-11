#!/usr/bin/env node
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { ManagementError,safeError } from '../ui/netclaw-visual/src/management/errors.js';
import { supportsHudNode } from './hud-node-version.mjs';
try{
  if(!supportsHudNode())throw new ManagementError('INCOMPATIBLE');
  const {values}=parseArgs({options:{home:{type:'string'},runtime:{type:'string'},installation:{type:'string'},'grant-ref':{type:'string'}},strict:true,allowPositionals:false});
  if(!values.home||!values.runtime||!values.installation||!values['grant-ref'])throw new ManagementError('INVALID_INPUT');
  const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
  const {ManagementService}=await import('../ui/netclaw-visual/src/management/service.js');
  const {serveAssistant}=await import('../mcp-servers/netclaw-assistant-mcp/server.mjs');
  const service=new ManagementService({root,home:values.home,kind:values.runtime,expectedInstallationId:values.installation});
  const server=await serveAssistant(service,values['grant-ref']);let closing=false;
  const close=async()=>{if(closing)return;closing=true;await server.close().catch(()=>{});await service.close().catch(()=>{});};
  process.stdin.on('end',close);process.once('SIGTERM',()=>close().finally(()=>process.exit(0)));
}catch(error){process.stderr.write(JSON.stringify({error:safeError(error)})+'\n');process.exitCode=1;}
