import test from "node:test";
import assert from "node:assert/strict";
import { openGoogle } from "../../scripts/genie-worlds/provider.mjs";
test("paid adapter refuses fixture and historical ordinary admission before network", async () => {
  let creates=0;
  const client={interactions:{create:async()=>{creates++;}}};
  for (const provider of ['fixture','google']) {
    await assert.rejects(openGoogle({ledger:{get:()=>({provider,state:'create_pending',usage_state:'reserved'})},id:'x',apiKey:'fake',client}),/paid_admission_required|campaign_session_required/);
  }
  assert.equal(creates,0);
});
