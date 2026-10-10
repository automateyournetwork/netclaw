#!/usr/bin/env node
import fs from 'node:fs';
import { supportsHudNode } from './hud-node-version.mjs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import net from 'node:net';
import { resolveRuntime, selectRuntime, readPrivate, writePrivate } from './runtime-selection.mjs';
import { parseEnvData } from '../ui/netclaw-visual/src/security/private-files.js';
import { hudPorts, hudHost } from '../ui/netclaw-visual/src/security/local-access.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=process.argv.slice(2), env={...process.env};
for (const [flag,key] of [['--runtime','NETCLAW_RUNTIME'],['--home','HUD_HOME']]) {
  const index=args.indexOf(flag); if(index>=0) { if(!args[index+1]) throw Error(flag+' requires a value'); env[key]=args[index+1]; args.splice(index,2); }
}
if(env.HUD_HOME) {
  if(!env.NETCLAW_RUNTIME) throw Error('--home requires --runtime openclaw or --runtime hermes');
  env[env.NETCLAW_RUNTIME==='hermes'?'HERMES_HOME':'OPENCLAW_HOME']=env.HUD_HOME;
}
const children=[];
const stop=()=>{ for(const child of children) { try { process.kill(-child.pid,'SIGTERM'); } catch { child.kill(); } } };
process.once('SIGINT',stop); process.once('SIGTERM',stop);
try {
  const mode=args[0] || 'start';
  if (mode==='select') {
    const selected=selectRuntime(args[1] || env.NETCLAW_RUNTIME,args[2] || env.HUD_HOME,env);
    console.log(`Selected ${selected.kind}: ${selected.home}`);
  } else {
    const selected=resolveRuntime({env,initialize:mode==='start' && !args.includes('--dry-run')});
    if(!['start','status','--dry-run'].includes(mode)) throw Error('Usage: netclaw hud [start|status|select KIND HOME] [--runtime KIND --home PATH] [--dry-run]');
    if(mode==='status' || args.includes('--dry-run')) {
      let readiness={ready:false,code:'runtime_stopped',executionVerified:false};
      if(selected.kind==='hermes' && mode==='status') {
        try {
          const auth=readPrivate(path.join(selected.statePath,'companion-auth.json'));
          const response=await fetch(`http://127.0.0.1:${auth.port || 8643}/health/detailed`,{headers:{Authorization:'Bearer '+auth.key},signal:AbortSignal.timeout(1500)});
          const status=await response.json();
          if(response.ok && status.installationId===selected.installationId)readiness=status;
        } catch {} // Observation only: no spawn, key generation or credential prompt.
      }
      console.log(JSON.stringify({...selected,configurationPresent:fs.existsSync(selected.configPath),legacyRepositoryEnvFallback:selected.kind==='openclaw' && fs.existsSync(path.join(root,'.env')),migrationGuidance:selected.kind==='openclaw'?'Repository .env fallback is retained. Use scripts/import-env.py explicitly to consolidate selected-home values.':undefined,readiness},null,2));
    }
    else {
      if(!supportsHudNode()) throw Error('HUD requires Node 24.19+ (qualified runtime).');
      if(!fs.existsSync(selected.configPath)) throw Error(`Run ${selected.kind} setup for the selected home before launching the HUD.`);
      const ui=path.join(root,'ui/netclaw-visual');
      // Parse only the selected home's literal dotenv. Explicit process values win.
      const configured=fs.existsSync(selected.envPath)?parseEnvData(fs.readFileSync(selected.envPath,'utf8')):{};
      Object.assign(env,{...configured,...env}, {NETCLAW_RUNTIME:selected.kind,NETCLAW_HUD_INSTALLATION_ID:selected.installationId});
      if(selected.kind==='hermes') { for(const key of Object.keys(env)) if(key.startsWith('OPENCLAW_')) delete env[key]; env.HERMES_HOME=selected.home; }
      else Object.assign(env,{OPENCLAW_HOME:selected.home,OPENCLAW_STATE_DIR:selected.home,OPENCLAW_CONFIG_PATH:selected.configPath});
      const ports=hudPorts(env), companionPort=Number(env.NETCLAW_HERMES_HUD_PORT || 8643);
      if(selected.kind==='hermes' && (!Number.isInteger(companionPort)||companionPort<1024||companionPort>65535||Object.values(ports).includes(companionPort))) throw Error('Invalid or conflicting companion port.');
      const endpoints=[['HUD API','127.0.0.1',ports.api],['HUD UI',hudHost(env),ports.ui]];
      if(selected.kind==='hermes')endpoints.push(['Hermes companion','127.0.0.1',companionPort]);
      // Probe before creating credentials or starting children. The actual bind
      // still rejects a race; never attach to or stop an unrelated listener.
      for(const [label,host,port] of endpoints)await new Promise((resolve,reject)=>{
        const probe=net.createServer();
        probe.once('error',()=>reject(Error(`${label} port ${port} is unavailable. Stop its owner or select different ports.`)));
        probe.listen({host,port,exclusive:true},()=>probe.close(resolve));
      });
      if(!fs.existsSync(path.join(ui,'node_modules/vite/bin/vite.js'))) throw Error('Install HUD dependencies: cd ui/netclaw-visual && npm ci');
      const launch=(command,argv,cwd)=>{
        const child=spawn(command,argv,{cwd,env,stdio:'inherit',detached:process.platform!=='win32'}); children.push(child);
        child.once('error',()=>{console.error('HUD child could not start.');stop();process.exitCode=1;});
        child.once('exit',code=>{if(code)process.exitCode=code;stop();}); return child;
      };
      if(selected.kind==='hermes') {
        const authFile=path.join(selected.statePath,'companion-auth.json');
        let auth; try { auth=readPrivate(authFile); } catch(error) { if(error.code!=='ENOENT')throw error; auth={key:randomBytes(32).toString('hex')};writePrivate(authFile,auth); }
        if(!/^[a-f0-9]{64}$/.test(auth.key)) throw Error('Private companion credential is invalid.');
        env.NETCLAW_HERMES_HUD_API_KEY=auth.key;
        const base=path.join(selected.home,'python-runtimes/hermes-hud-agent');
        const source=env.NETCLAW_HERMES_SOURCE || path.join(base,'source');
        const python=env.NETCLAW_HERMES_PYTHON || path.join(base,'venv/bin/python');
        if(!fs.existsSync(python)) throw Error('Install the private companion first: ./scripts/install.sh --runtime hermes --add hermes-hud');
        const port=companionPort;
        if(auth.port!==port)writePrivate(authFile,{...auth,port});
        launch(python,[path.join(root,'mcp-servers/hermes-hud-mcp/hermes_api.py'),'--home',selected.home,'--source',source,'--installation',selected.installationId,'--port',String(port)],root);
        let ready=false;
        for(let n=0;n<100;n++) {
          if(children[0].exitCode!==null)break;
          try { const response=await fetch(`http://127.0.0.1:${port}/health/detailed`,{headers:{Authorization:'Bearer '+auth.key},signal:AbortSignal.timeout(500)}); const status=await response.json(); if(response.ok && status.ready && status.installationId===selected.installationId) {ready=true;break;} } catch {}
          await new Promise(resolve=>setTimeout(resolve,300));
        }
        if(!ready)throw Error('Hermes companion readiness failed. Verify the pinned source, selected configuration and installed tool runtimes.');
      }
      launch(process.execPath,['server.js'],ui);
      launch(process.execPath,['node_modules/vite/bin/vite.js'],ui);
      console.log(`${selected.kind} HUD: http://localhost:${env.HUD_UI_PORT || 3000}/ · Ctrl+C stops these HUD processes.`);
    }
  }
} catch(error) { stop(); console.error(error.message); process.exitCode=1; }
