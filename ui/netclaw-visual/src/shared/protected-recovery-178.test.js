import test from 'node:test';
import assert from 'node:assert/strict';
import { createProtectedOperationsApi } from './protected-operations-client.js';
test('R07 protected requests refuse redirects and preserve ambiguous failures without retries', async t => {
 const original=globalThis.fetch, calls=[];t.after(()=>globalThis.fetch=original);
 globalThis.fetch=async(_url,options)=>{calls.push(options);throw Error('redirect or offline');};
 const api=createProtectedOperationsApi('border');await assert.rejects(api.status({client_nonce:'original'}),/nothing was resent/);assert.equal(calls.length,1);assert.equal(calls[0].redirect,'error');
});
