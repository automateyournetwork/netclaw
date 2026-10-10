import test from 'node:test';
import assert from 'node:assert/strict';
import { federationEndpoint, federationReadiness } from './federation.js';
const installation={installationId:'selected',kind:'hermes'};
test('selected federation requires matching identity, harness and readiness', async()=>{
  for(const value of [{}, {installation_id:'foreign',harness_type:'hermes',federation_ready:true}, {installation_id:'selected',harness_type:'openclaw',federation_ready:true}]) {
    assert.equal((await federationReadiness(installation,'http://localhost',async()=>({ok:true,json:async()=>value}))).ready,false);
  }
  assert.equal((await federationReadiness(installation,'http://localhost',async()=>({ok:true,json:async()=>({installation_id:'selected',harness_type:'hermes',federation_ready:true})}))).ready,true);
  assert.equal((await federationReadiness(installation,'http://localhost',async()=>{throw Error('offline');})).ready,false);
});
test('only selected local endpoints are accepted',()=>{
  assert.equal(federationEndpoint({BGP_API_PORT:'18179'}),'http://127.0.0.1:18179');
  for(const value of ['https://example.com','http://user:pass@localhost','http://localhost/foreign'])assert.throws(()=>federationEndpoint({NETCLAW_BGP_API:value}));
});
