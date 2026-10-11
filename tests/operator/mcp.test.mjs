import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { installationFixture } from './fixtures.mjs';
const require=createRequire(new URL('../../mcp-servers/netclaw-operator-mcp/package.json',import.meta.url));
const {Client}=require('@modelcontextprotocol/client');
const {StdioClientTransport}=require('@modelcontextprotocol/client/stdio');
test('real official MCP handshake binds identity, serves bounded inventory and rejects arbitrary methods',async t=>{
  const fixture=installationFixture(t),client=new Client({name:'synthetic-operator-test',version:'1.0.0'});
  const transport=new StdioClientTransport({command:process.execPath,args:[fileURLToPath(new URL('../../scripts/netclaw-operator.mjs',import.meta.url)),
    '--home',fixture.home,'--runtime','openclaw','--installation',fixture.installationId],stderr:'pipe'});
  let diagnostics='';transport.stderr?.on('data',chunk=>diagnostics+=chunk);
  t.after(()=>client.close());await client.connect(transport,{timeout:10000});
  const tools=await client.listTools();assert.equal(tools.tools.length,15);
  const identity=await client.callTool({name:'operator_identity',arguments:{}});
  assert.equal(identity.structuredContent.installationId,fixture.installationId);assert.equal(identity.structuredContent.contract.major,1);
  const resources=await client.callTool({name:'operator_resources',arguments:{kind:'integration',limit:2}});
  assert.equal(resources.structuredContent.data.items.length,2);assert.equal(resources.structuredContent.data.nextCursor,'2');
  const bad=await client.callTool({name:'operator_identity',arguments:{approved:true}});assert.equal(bad.isError,true);
  try{const result=await client.callTool({name:'shell',arguments:{command:'noop'}});assert.equal(result.isError,true);}catch(error){assert.ok(error);}
  assert.equal(diagnostics,'');
});
