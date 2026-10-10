import test from 'node:test';
import assert from 'node:assert/strict';
import {branchSeed} from './branch-context.js';
test('branch-point prefixes are immutable, exclude later parent turns and survive a nested fork',()=>{
 const nodes=[{id:'root',messages:[{role:'user',content:'first'},{role:'assistant',content:'answer one'}]}];
 const a={id:'a',parentId:'root',seedContext:branchSeed(nodes,'root','answer one'),messages:[]};nodes.push(a);
 nodes[0].messages.push({role:'user',content:'later parent'},{role:'assistant',content:'answer two'});
 const b={id:'b',parentId:'root',seedContext:branchSeed(nodes,'root','answer two'),messages:[]};nodes.push(b);
 a.messages.push({role:'user',content:'branch A'});
 const nested=branchSeed(nodes,'a');assert.equal(a.seedContext.length,2);assert.equal(b.seedContext.length,4);
 assert.deepEqual(nested.map(m=>m.content),['first','answer one','branch A']);assert.equal(JSON.stringify(nested).includes('later parent'),false);
 nodes[0].messages[0].content='edited';assert.equal(a.seedContext[0].content,'first');
});
