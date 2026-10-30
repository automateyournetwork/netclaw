// Controlled API issuer fixture. Synthetic bytes only; never an operator UI.
import fs from 'node:fs';
import crypto from 'node:crypto';
import { createLocalChangePolicy } from '../../ui/netclaw-visual/terminal-change-policy.js';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const devices=input.devices.map(d=>({...d,supported:true}));
const policy=createLocalChangePolicy({directory:input.root,listDevices:()=>devices});
const saved=policy.save({revision:'initial',enabled:true,deviceIds:devices.map(d=>d.id),confirmLab:true});
const candidate=policy.captureCandidate({content:input.content});
const request={id:crypto.randomUUID(),request:'Apply the exact synthetic candidate to this isolated fixture; verify OSPF and management.',changeMode:'local-lab',targetDeviceIds:devices.map(d=>d.id),policyRevision:saved.revision,
  migration:{...candidate,harness:input.harness,testbed:input.testbed,profile:'ospf-routing-v1'}};
const prepared=policy.begin(request.id,request,policy.resolve(request));
if (input.prepareOnly) console.log(JSON.stringify({change:prepared,candidate}));
else {
  for(const d of prepared.devices) for(const f of ['baselinePath','rollbackPath']) fs.writeFileSync(d[f],'SYNTHETIC_LIVE_BASELINE fixture only\n',{mode:0o600});
  const report={baseline:devices.map(d=>({device:d.id,summary:'Synthetic baseline fixture'})),rollback:devices.map(d=>({device:d.id,summary:'Synthetic rollback fixture'}))};
  const change=policy.prepared(prepared,report);
  console.log(JSON.stringify({change,candidate,grant:change.applyGrants[0]}));
}
