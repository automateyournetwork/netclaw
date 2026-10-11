#!/usr/bin/env node
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { safeError,ManagementError } from '../ui/netclaw-visual/src/management/errors.js';
import { supportsHudNode } from './hud-node-version.mjs';

try {
  if(!supportsHudNode())throw new ManagementError('INCOMPATIBLE');
  const {values}=parseArgs({options:{home:{type:'string'},runtime:{type:'string'},installation:{type:'string'}},strict:true,allowPositionals:false});
  if(!values.home||!values.runtime)throw new Error('Explicit existing home and runtime are required.');
  const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
  const {ManagementService}=await import('../ui/netclaw-visual/src/management/service.js');
  const {serveOperator}=await import('../mcp-servers/netclaw-operator-mcp/server.mjs');
  const service=new ManagementService({root,home:values.home,kind:values.runtime,expectedInstallationId:values.installation});
  const server=await serveOperator(service);let closing=false;
  const close=async()=>{if(closing)return;closing=true;await server.close().catch(()=>{});await service.close().catch(()=>{});};
  process.stdin.on('end',close);process.once('SIGTERM',()=>close().finally(()=>process.exit(0)));
}catch(error){process.stderr.write(JSON.stringify({error:safeError(error)})+'\n');process.exitCode=1;}
