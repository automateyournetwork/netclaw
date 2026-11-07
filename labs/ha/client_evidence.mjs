/** Source-only helpers for coordinator-owned REAL client qualification. No network or effects. */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createHash, X509Certificate, verify } from 'node:crypto';
import { clusterCanonical, verifyClusterDescriptor, clusterReviewMatches } from '../../ui/netclaw-visual/src/shared/cluster-binding.js';
export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export const canonical = clusterCanonical;
export function privateFile(file, limit = 4 * 1024 * 1024) {
  assert.ok(path.isAbsolute(file), 'Absolute private path required');
  const s = fs.lstatSync(file);
  assert.ok(s.isFile() && !s.isSymbolicLink() && s.uid === process.getuid() && !(s.mode & 0o077) && s.size <= limit, 'Owned private bounded file required');
  return fs.readFileSync(file);
}
export function privateDirectory(directory) {
  assert.ok(path.isAbsolute(directory));
  const s = fs.lstatSync(directory);assert.ok(s.isDirectory() && !s.isSymbolicLink() && s.uid === process.getuid() && !(s.mode & 0o077), 'Existing owned private directory required');
  return directory;
}
export function writeArtifact(directory, name, value) {
  privateDirectory(directory);assert.match(name,/^[a-z0-9_.-]{1,100}$/);
  const file=path.join(directory,name),raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value,null,2)+'\n');
  const fd=fs.openSync(file,'wx',0o600);try{fs.writeFileSync(fd,raw);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
  return {file,sha256:sha256(raw),bytes:raw.length};
}
export function verifyEnvelope(envelope, certificate, schema) {
  assert.equal(envelope.schema,schema);assert.deepEqual(Object.keys(envelope).sort(),['payload','schema','signature']);
  const cert=new X509Certificate(certificate),key=cert.publicKey;
  assert.equal(key.asymmetricKeyType,'ec');assert.equal(key.asymmetricKeyDetails.namedCurve,'prime256v1');
  assert.equal(envelope.signature.algorithm,'ecdsa-p256-sha256');assert.equal(envelope.signature.key_id,sha256(key.export({format:'der',type:'spki'})));
  const signature=Buffer.from(envelope.signature.value,'base64url');assert.equal(signature.toString('base64url'),envelope.signature.value);
  const body=Buffer.from(canonical({schema,payload:envelope.payload}));
  assert.ok(verify('sha256',Buffer.concat([Buffer.from('netclaw.r02/'+schema+'\0'),body]),key,signature),'Original artifact signature must verify');
  return {payload:envelope.payload,digest:sha256(body)};
}
export function validateReference(row, descriptor, principal) {
  assert.ok(row && /^[A-Za-z0-9_.:-]{1,200}$/.test(row.reference?.operation_id) && /^[A-Za-z0-9_.:-]{1,200}$/.test(row.reference?.client_nonce));
  assert.equal(row.review_digest,sha256(canonical(row.review)));assert.ok(clusterReviewMatches(descriptor,row.review,principal));
  assert.ok(Number.isSafeInteger(row.attempt_count) && row.attempt_count >= 0 && row.attempt_count <= 1);
}
export async function loadQualification(configFile, surface) {
  const config=JSON.parse(privateFile(configFile,65536));
  assert.equal(config.schema_version,1);assert.equal(config.classification,'REAL');assert.equal(config.surface,surface);
  assert.ok(['original_once','prepare_review','authority','no_quorum','stale_review','original_result','endpoint_recovery','cold_recovery'].includes(config.phase));
  assert.ok(/^[a-f0-9]{40}$/.test(config.source_commit));
  const origin=new URL(config.origin);assert.equal(origin.protocol,'https:');assert.equal(config.origin,origin.origin);
  privateDirectory(config.evidence_directory);privateDirectory(config.profile_directory);
  const bytes=privateFile(config.record_file);assert.equal(sha256(bytes),config.record_sha256,'Original record bundle must match coordinator pin');
  const bundle=JSON.parse(bytes);assert.equal(bundle.classification,'REAL');assert.equal(bundle.schema_version,1);assert.equal(bundle.source_commit,config.source_commit);
  const verified=await verifyClusterDescriptor(bundle.descriptor,{pin:bundle.pin});
  const node=verified.descriptor.manifest.manifest.nodes.find(n=>n.endpoints.https.replace(/\/$/,'')===config.origin);assert.ok(node,'Selected HTTPS origin must be enrolled');
  if(['original_once','prepare_review'].includes(config.phase)){
    assert.ok(bundle.selection && bundle.expected_review);
    for(const k of ['principal','member','model_profile','tool_call'])assert.ok(bundle.expected_review[k]);
    assert.deepEqual(bundle.expected_review.principal,bundle.principal);
    assert.ok(path.isAbsolute(config.once_file));privateDirectory(path.dirname(config.once_file));
    return {config,bundle,node,counters_sha256:sha256(privateFile(config.counter_file))};
  }
  validateReference(bundle.completed,bundle.descriptor,bundle.principal);
  const completed=bundle.completed,receipt=verifyEnvelope(completed.result_envelope,completed.member_certificate,'netclaw.execution.result.v2');
  const acceptance=completed.ack_envelope.payload.acceptance,nodeAck=bundle.descriptor.manifest.manifest.nodes.find(n=>n.node_id===acceptance?.node_id);assert.ok(nodeAck);
  const ack=verifyEnvelope(completed.ack_envelope,nodeAck.certificate,'netclaw.execution.ack.v2');
  assert.equal(receipt.payload.operation_id,completed.reference.operation_id);assert.equal(ack.payload.operation_id,completed.reference.operation_id);assert.equal(ack.payload.receipt_sha256,receipt.digest);assert.equal(ack.payload.attempt_id,receipt.payload.attempt_id);
  for(const k of ['principal','border','member','model_profile','cluster'])assert.deepEqual(receipt.payload[k],completed.review[k]);
  for(const k of ['border','member','cluster'])assert.deepEqual(ack.payload[k],receipt.payload[k]);
  assert.equal(ack.payload.acceptance.border.installation_id,nodeAck.installation_id);assert.equal(ack.payload.acceptance.border.key_id,nodeAck.key_id);
  assert.equal(receipt.payload.tool_call_sha256,sha256(canonical(completed.review.tool_call)));assert.equal(completed.attempt_count,1);assert.equal(completed.reference.decision_sent,true);
  if(bundle.stale){validateReference(bundle.stale,bundle.descriptor,bundle.principal);assert.equal(bundle.stale.attempt_count,0);}
  if(config.phase==='stale_review')assert.ok(bundle.stale,'Original pending review record required');
  const counters=privateFile(config.counter_file); // Actual runner export, owned by coordinator. Never rewritten here.
  return {config,bundle,node,receipt,ack,counters_sha256:sha256(counters)};
}
export function assertOriginal(operation, expected, resultDigest) {
  assert.equal(operation.operation_id,expected.reference.operation_id);assert.equal(operation.client_nonce,expected.reference.client_nonce);assert.equal(operation.review_digest,expected.review_digest);
  assert.deepEqual(operation.review,expected.review);assert.equal(operation.attempt_count,expected.attempt_count);
  if(resultDigest){assert.equal(operation.result?.digest || operation.result_reference?.digest,resultDigest);if(operation.result)assert.equal(operation.result.verified,true);}
}
export function unchangedCounters(context) {assert.equal(sha256(privateFile(context.config.counter_file)),context.counters_sha256,'REAL cumulative counters changed during recovery-only qualification');}

export function claimOriginal(context) {
 const {config}=context;assert.ok(['original_once','prepare_review'].includes(config.phase));
 const fd=fs.openSync(config.once_file,'wx',0o600);try{fs.writeFileSync(fd,JSON.stringify({schema_version:1,source_commit:config.source_commit,record_sha256:config.record_sha256,claimed_at_ms:Date.now(),state:'original_once_claimed'}));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
}
export function assertExactReview(operation, context) {
 const expected=context.bundle.expected_review;
 for(const key of ['principal','member','model_profile','tool_call'])assert.deepEqual(operation.review[key],expected[key]);
 assert.equal(operation.review_digest,sha256(canonical(operation.review)));assert.equal(operation.state,'review_pending');
 assert.ok(clusterReviewMatches(context.bundle.descriptor,operation.review,context.bundle.principal));
 assert.equal(operation.attempt_count,0);assert.equal(operation.may_have_executed,false);
 assert.equal(operation.review.limits.max_tool_calls,1);assert.ok(operation.review.limits.max_inference_calls<=2);assert.ok(operation.review.limits.expires_at_ms>Date.now());
}
