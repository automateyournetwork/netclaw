import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import net from 'node:net';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import { installationFixture,nonce } from './fixtures.mjs';
import { ManagementService } from '../../ui/netclaw-visual/src/management/service.js';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const enabled=process.env.NETCLAW_TEST_OPENCLAW_ENTRY&&process.env.NETCLAW_TEST_LIVE_GAIT==='1';
test('real isolated OpenClaw, controlled provider and detached management worker preserve contextual turns', {skip:!enabled,timeout:180000},async t=>{
  const fixture=installationFixture(null,'openclaw'),children=[],streams=[];let service;
  t.after(async()=>{
    if(service)await service.close();
    for(const child of children.reverse()){if(child.exitCode===null){child.kill('SIGTERM');await once(child,'exit').catch(()=>{});}}
    streams.forEach(s=>s.close());fixture.cleanup();
  });
  const provider=spawn('python3',['-u',path.join(root,'tests/operator/controlled-provider.py')],{stdio:['pipe','pipe','ignore']});children.push(provider);
  const lines=createInterface({input:provider.stdout});const iterator=lines[Symbol.asyncIterator]();
  const {url}=JSON.parse((await iterator.next()).value);
  const probe=net.createServer();await new Promise(resolve=>probe.listen(0,'127.0.0.1',resolve));const port=probe.address().port;await new Promise(resolve=>probe.close(resolve));
  const workspace=path.join(fixture.home,'workspace');fs.mkdirSync(workspace,{mode:0o700});
  fs.writeFileSync(fixture.configPath,JSON.stringify({models:{providers:{fixture:{baseUrl:url,apiKey:'${OPENAI_API_KEY}',api:'openai-completions',models:[{id:'hud-fixture',name:'hud-fixture',contextWindow:64000,maxTokens:4096}]}}},agents:{defaults:{model:{primary:'fixture/hud-fixture'},workspace}},tools:{deny:['*']},gateway:{mode:'local',port,auth:{mode:'token',token:'${OPENCLAW_GATEWAY_TOKEN}'}}}),{mode:0o600});
  fs.writeFileSync(path.join(fixture.home,'.env'),'OPENCLAW_GATEWAY_TOKEN=fixture-private-token-150\nOPENAI_API_KEY=fixture-only\n',{mode:0o600});
  const log=fs.openSync(path.join(fixture.root,'gateway.log'),'wx',0o600);
  const gateway=spawn(process.execPath,[process.env.NETCLAW_TEST_OPENCLAW_ENTRY,'gateway','run','--port',String(port),'--bind','loopback'],{env:{PATH:`${path.dirname(process.execPath)}:${process.env.PATH}`,HOME:fixture.home,OPENCLAW_STATE_DIR:fixture.home,OPENCLAW_CONFIG_PATH:fixture.configPath,OPENCLAW_GATEWAY_TOKEN:'fixture-private-token-150',OPENAI_API_KEY:'fixture-only'},stdio:['ignore',log,log]});fs.closeSync(log);children.push(gateway);
  service=new ManagementService({...fixture,root});
  let ready=false;
  for(let attempt=0;attempt<150;attempt++){
    assert.equal(gateway.exitCode,null,'isolated gateway remains running');
    try{ready=(await service.runtime.readiness()).ready;if(ready)break;}catch{}
    await delay(300);
  }
  assert.equal(ready,true,'real gateway ready');
  const conversation=await service.call('operator_conversation_open',{nonce:nonce(),view:'chat'});
  for(const prompt of ['remember violet','what colour?']){
    const input={nonce:nonce(),conversationId:conversation.conversationId,prompt,contextIds:[]};
    const admitted=await service.call('operator_request_submit',input);
    await service.close();service=null; // The owned worker outlives this façade.
    let result;
    for(let attempt=0;attempt<300;attempt++){
      await delay(200);service=new ManagementService({...fixture,root});
      result=service.journal.get(service.binding.principal,admitted.operationId);
      if(['succeeded','failed','unknown'].includes(result.state))break;
      await service.close();service=null;
    }
    assert.equal(result?.state,'succeeded',JSON.stringify(result));assert.match(result.result.output,/violet/i);
    assert.equal((await service.call('operator_request_submit',input)).operationId,admitted.operationId);
    const worker=JSON.parse(service.journal._row(admitted.operationId).worker);
    for(let attempt=0;attempt<100;attempt++){try{process.kill(worker.pid,0);await delay(50);}catch{break;}}
  }
  provider.stdin.write('count\n');assert.equal(JSON.parse((await iterator.next()).value).requests,2);
  assert.equal(gateway.exitCode,null,'disconnect never stopped the existing runtime');
});

const hermesEnabled=process.env.NETCLAW_TEST_HERMES_PYTHON&&process.env.NETCLAW_TEST_HERMES_SOURCE&&process.env.NETCLAW_HUD_BRIDGE_PYTHON&&process.env.NETCLAW_TEST_LIVE_GAIT==='1';
test('real pinned Hermes companion and detached management worker preserve contextual turns', {skip:!hermesEnabled,timeout:180000},async t=>{
  const fixture=installationFixture(null,'hermes'),children=[];let service;
  t.after(async()=>{
    if(service)await service.close();
    for(const child of children.reverse()){if(child.exitCode===null){child.kill('SIGTERM');await once(child,'exit').catch(()=>{});}}
    fixture.cleanup();
  });
  const provider=spawn('python3',['-u',path.join(root,'tests/operator/controlled-provider.py')],{stdio:['pipe','pipe','ignore']});children.push(provider);
  const iterator=createInterface({input:provider.stdout})[Symbol.asyncIterator]();const {url}=JSON.parse((await iterator.next()).value);
  const probe=net.createServer();await new Promise(resolve=>probe.listen(0,'127.0.0.1',resolve));const port=probe.address().port;await new Promise(resolve=>probe.close(resolve));
  fs.writeFileSync(fixture.configPath,JSON.stringify({model:{default:'hud-fixture',provider:'custom',base_url:url},mcp_servers:{}}),{mode:0o600});
  const key='fixture-only-hermes-private-token-150';
  fs.writeFileSync(path.join(fixture.home,'.env'),`NETCLAW_HERMES_HUD_API_KEY=${key}\nNETCLAW_HERMES_HUD_PORT=${port}\nOPENAI_API_KEY=fixture-only\nOPENAI_BASE_URL=${url}\n`,{mode:0o600});
  const log=fs.openSync(path.join(fixture.root,'companion.log'),'wx',0o600);
  const companion=spawn(process.env.NETCLAW_TEST_HERMES_PYTHON,['-u',path.join(root,'mcp-servers/hermes-hud-mcp/hermes_api.py'),'--home',fixture.home,'--source',process.env.NETCLAW_TEST_HERMES_SOURCE,'--installation',fixture.installationId,'--port',String(port)],{env:{PATH:process.env.PATH,HOME:fixture.home,NETCLAW_HERMES_HUD_API_KEY:key,OPENAI_API_KEY:'fixture-only',OPENAI_BASE_URL:url,HERMES_HOME:fixture.home,PYTHON_DOTENV_DISABLED:'1'},stdio:['ignore',log,log]});fs.closeSync(log);children.push(companion);
  service=new ManagementService({...fixture,root});let ready=false;
  for(let attempt=0;attempt<100;attempt++){
    assert.equal(companion.exitCode,null,'pinned companion remains running');
    try{ready=(await service.runtime.readiness()).ready;if(ready)break;}catch{}
    await delay(300);
  }
  assert.equal(ready,true,'real protected companion ready');
  const conversation=await service.call('operator_conversation_open',{nonce:nonce(),view:'chat'});
  for(const prompt of ['remember violet','what colour?']){
    const input={nonce:nonce(),conversationId:conversation.conversationId,prompt,contextIds:[]};
    const admitted=await service.call('operator_request_submit',input);await service.close();service=null;
    let result;
    for(let attempt=0;attempt<300;attempt++){
      await delay(200);service=new ManagementService({...fixture,root});result=service.journal.get(service.binding.principal,admitted.operationId);
      if(['succeeded','failed','unknown'].includes(result.state))break;
      await service.close();service=null;
    }
    assert.equal(result?.state,'succeeded',JSON.stringify(result));assert.match(result.result.output,/violet/i);
    assert.equal((await service.call('operator_request_submit',input)).operationId,admitted.operationId);
    const worker=JSON.parse(service.journal._row(admitted.operationId).worker);
    for(let attempt=0;attempt<100;attempt++){try{process.kill(worker.pid,0);await delay(50);}catch{break;}}
  }
  provider.stdin.write('count\n');assert.equal(JSON.parse((await iterator.next()).value).requests,2);
  assert.equal(companion.exitCode,null,'disconnect preserves the selected runtime');
});
