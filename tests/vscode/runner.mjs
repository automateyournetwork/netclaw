import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import net from 'node:net';
import { installationFixture,nonce } from '../operator/fixtures.mjs';
import {ManagementService} from '../../ui/netclaw-visual/src/management/service.js';
const root=fileURLToPath(new URL('../../',import.meta.url)),extension=path.join(root,'extensions/netclaw-vscode');
const require=createRequire(path.join(extension,'package.json'));
const {runTests}=require('@vscode/test-electron');
const a=installationFixture(),b=installationFixture(null,'hermes');
if(process.env.NETCLAW_TEST_RAG_PYTHON&&process.env.NETCLAW_TEST_RAG_CACHE&&process.env.NETCLAW_TEST_LIVE_GAIT==='1'){
  fs.appendFileSync(path.join(a.home,'.env'),`RAG_MCP_PYTHON=${process.env.NETCLAW_TEST_RAG_PYTHON}\nHF_HOME=${process.env.NETCLAW_TEST_RAG_CACHE}\n`);
  const backend=new ManagementService({root,home:a.home,kind:a.kind});
  try{
    const upload=await backend.call('operator_workspace',{action:'rag-upload',nonce:nonce(),args:{name:'editor-qualification.md',content:Buffer.from('# Editor reference\n\nThe synthetic lab change window is violet Thursday. Always capture a baseline.').toString('base64')}});
    const op=await backend.call('operator_workspace',{action:'rag-index',nonce:nonce(),args:{id:upload.uploadId}});
    let state,deadline=Date.now()+150000;
    do{state=await backend.call('operator_operation_get',{operationId:op.operationId});if(['succeeded','failed','unknown'].includes(state.state))break;await new Promise(r=>setTimeout(r,200));}while(Date.now()<deadline);
    if(state.state!=='succeeded')throw Error('RAG editor fixture preparation failed: '+JSON.stringify(state));
  }finally{await backend.close();}
}
const profile=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'netclaw150-editor-')));
fs.mkdirSync(path.join(profile,'user','User'),{recursive:true});
fs.writeFileSync(path.join(profile,'user','User','settings.json'),JSON.stringify({'telemetry.telemetryLevel':'off','update.mode':'none','extensions.autoUpdate':false,'workbench.startupEditor':'none','security.workspace.trust.startupPrompt':'never'}));
let debugPort;
if(process.env.NETCLAW_TEST_PLAYWRIGHT){const server=net.createServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));debugPort=server.address().port;await new Promise(resolve=>server.close(resolve));}
try{
  await runTests({version:process.env.VSCODE_VERSION||'1.102.0',...(process.env.VSCODE_EXECUTABLE?{vscodeExecutablePath:process.env.VSCODE_EXECUTABLE}:{}),
    extensionDevelopmentPath:extension,extensionTestsPath:path.join(extension,'test','editor.cjs'),reuseMachineInstall:false,
    extensionTestsEnv:{NETCLAW_TEST_FIXTURES:JSON.stringify([a,b]),NETCLAW_TEST_ROOT:root,NETCLAW_TEST_NODE:process.execPath,NETCLAW_TEST_REPORT:path.join(profile,'report.json'),NETCLAW_TEST_REAL_RAG:process.env.NETCLAW_TEST_RAG_PYTHON?'1':'0',...(debugPort?{NETCLAW_TEST_CDP_PORT:String(debugPort),NETCLAW_TEST_PLAYWRIGHT:process.env.NETCLAW_TEST_PLAYWRIGHT,NETCLAW_TEST_SCREENSHOTS:path.join(profile,'screenshots')}:{})},
    launchArgs:['--user-data-dir',path.join(profile,'user'),'--extensions-dir',path.join(profile,'extensions'),'--skip-welcome','--skip-release-notes','--disable-extensions','--disable-telemetry',...(debugPort?[`--remote-debugging-port=${debugPort}`]:[])],
  });
  const report=JSON.parse(fs.readFileSync(path.join(profile,'report.json'),'utf8'));
  console.log(JSON.stringify({...report,scope:'Synthetic installations in actual desktop editor; not real owner WSL or production qualification.'},null,2));
}finally{a.cleanup();b.cleanup();}
