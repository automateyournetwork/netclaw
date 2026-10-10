import test from 'node:test';
import assert from 'node:assert/strict';
import { runtimeSettings } from './runtime-settings.js';
test('modern agent overrides are displayed and secrets never enter compatibility config', () => {
 const config = { agents: { defaults: {model:'provider/default', workspace:'/default'}, entries:{engineer:{model:{primary:'provider/actual@private-profile',fallbacks:['provider/fallback']},workspace:'/actual'}}},
 gateway:{mode:'local',bind:'loopback',port:18789,auth:{token:'SECRET'}},env:{PASSWORD:'SECRET'},mcp:{servers:{private:{env:{TOKEN:'SECRET'}}}} };
 const result=runtimeSettings(config,28,'/runtime/openclaw.json');
 const fields=Object.fromEntries(result.settings.map(x=>[x.label,x.value]));
 assert.equal(fields['Primary Model'],'provider/actual');assert.equal(fields.Workspace,'/actual');
 assert.equal(fields['Selected Agent'],'engineer');assert.equal(fields['Configuration source'],'/runtime/openclaw.json');
 assert.doesNotMatch(JSON.stringify(result),/SECRET|private-profile|PASSWORD|TOKEN/);
 assert.equal(result.config.agents.defaults.model.primary,'provider/actual');
});
test('legacy string model and unavailable config do not invent template defaults', () => {
 const result=runtimeSettings({agents:{list:[{id:'work',default:true,model:'provider/model'}]}},0,'runtime');
 assert.equal(result.config.agents.defaults.model.primary,'provider/model');
 assert.deepEqual(runtimeSettings(null,0,'missing').config,{});
 assert.match(JSON.stringify(runtimeSettings(null,0,'missing')),/Unavailable/);
});

test('Hermes settings use the rendered row contract and expose no credentials', async()=>{
 const {hermesRuntimeSettings}=await import('./runtime-settings.js');
 const data=hermesRuntimeSettings({model:{default:'qualified-model',provider:'anthropic'},secret:'do-not-render'},'/selected/config.yaml');
 assert.ok(Array.isArray(data.settings));
 assert.equal(Object.fromEntries(data.settings.map(r=>[r.label,r.value]))['Selected runtime'],'Hermes');
 assert.ok(!JSON.stringify(data).includes('do-not-render'));
 assert.ok(!JSON.stringify(hermesRuntimeSettings(null,'/missing')).includes('OpenClaw'));
});
