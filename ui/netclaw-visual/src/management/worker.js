import { spawn } from 'node:child_process';
import path from 'node:path';
import { invariant } from './errors.js';

/** Start only our fixed worker. It owns work independently of the MCP transport. */
export async function startOwnedWorker({ root, binding, operationId, transient = {}, env = process.env }) {
  invariant(/^[a-f\d-]{36}$/.test(operationId));
  binding.assertCurrent();
  const child = spawn(process.execPath, [path.join(root,'scripts/netclaw-management-worker.mjs'),
    '--home',binding.home,'--runtime',binding.kind,'--installation',binding.installationId,'--operation',operationId],
  { cwd:root, detached:true, shell:false, env, stdio:['pipe','ignore','ignore'], windowsHide:true });
  await new Promise((resolve,reject) => { child.once('error',reject); child.once('spawn',resolve); });
  // Secret replacements, if present, exist only in this authenticated local pipe.
  child.stdin.on('error',()=>{}); child.stdin.end(JSON.stringify(transient)); child.unref();
  return { workerStarted:true };
}

export async function runOwnedOperation({ journal, operationId, binding, audit, reauthorize, dispatch, workerIdentity = { pid:process.pid,start:new Date().toISOString() } }) {
  binding.assertCurrent();
  const lease = journal.claim(operationId, workerIdentity);
  if (!lease) return { dispatched:false };
  let dispatched=false, heartbeatError=false;
  const timer=setInterval(()=>{try{journal.renew(operationId,lease);}catch{heartbeatError=true;}},5000); timer.unref();
  try {
    const input=journal.input(operationId,lease);
    await reauthorize(input);
    await audit.record({operationId,state:'before-dispatch'});
    binding.assertCurrent();await reauthorize(input);
    invariant(!heartbeatError,'UNKNOWN_OUTCOME');
    // Persist the dispatch intent before calling an external runtime. A crash from
    // here onward is uncertain, even if an acknowledgement was never received.
    journal.event(operationId,'dispatch-intent',{});dispatched=true;
    const result=await dispatch(input,{ attachReference:reference=>journal.attachReference(operationId,lease,reference),
      reauthorize:()=>reauthorize(input), event:(type,data)=>journal.event(operationId,type,data) });
    await reauthorize(input); invariant(!heartbeatError,'UNKNOWN_OUTCOME');
    await audit.record({operationId,state:'completed'});
    return journal.finish(operationId,lease,'succeeded',result);
  } catch(error) {
    // Do not pretend that an exception after dispatch proves no effect.
    return journal.finish(operationId,lease,dispatched?'unknown':'failed',{code:dispatched?'UNKNOWN_OUTCOME':(error.code||'SOURCE_UNAVAILABLE')});
  } finally {clearInterval(timer);}
}
