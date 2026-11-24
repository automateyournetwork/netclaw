import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, mkdirSync, rmSync, symlinkSync, chmodSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { loadOfflineSnapshot } from '../../scripts/genie-worlds/offline-snapshot.mjs';
const sha = s => createHash('sha256').update(s).digest('hex');
function fixture(t, mutation = null) {
  process.umask(0o077);
  const root = mkdtempSync(join(resolve(process.env.NETCLAW_TEST_TMP || '.spec200-local/tests'), 'offline-snapshot-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const facts = {schema:1, classification:'private', mode:'frozen_historical_snapshot', snapshot_id:'independent-test', google_export_authorized:false, devices:[{id:'synthetic-router'}], physical_links:[], coverage_limits:['Historical test data'], verified_baseline_window:{start_unix:1,end_unix:2}, enrichment_window:{start_unix:3,end_unix:4}};
  const files = {'world-facts.json':JSON.stringify(facts), 'coverage.json':JSON.stringify({outcomes:{unavailable:1,empty_raw:2}})};
  const manifest = Object.fromEntries(Object.entries(files).map(([n,s]) => [n,sha(s)]));
  mutation?.(manifest, files);
  for (const [n,s] of Object.entries(files)) writeFileSync(join(root,n),s,{mode:0o600});
  const bytes=JSON.stringify(manifest), hash=sha(bytes);
  writeFileSync(join(root,'SHA256SUMS.json'),bytes,{mode:0o600});
  writeFileSync(join(root,'SEAL.json'),JSON.stringify({snapshot_id:facts.snapshot_id,manifest_sha256:hash}),{mode:0o600});
  return {root,hash};
}
test('offline reader preserves historical windows and unknown/empty coverage without network',t=>{
  const {root,hash}=fixture(t); const old=globalThis.fetch;
  globalThis.fetch=()=>{throw Error('network forbidden');};
  try {
    const snapshot=loadOfflineSnapshot(root,hash);
    assert.equal(snapshot.summary.network_required,false);
    assert.equal(snapshot.summary.hosted_eligible,false);
    assert.equal(snapshot.summary.coverage_outcomes.unavailable,1);
    assert.equal(snapshot.summary.coverage_outcomes.empty_raw,2);
    assert.equal(snapshot.localFacts().verified_baseline_window.start_unix,1);
    const copy=snapshot.localFacts();copy.devices[0].id='changed';
    assert.equal(snapshot.localFacts().devices[0].id,'synthetic-router');
    assert.equal('facts' in snapshot.summary,false);
  } finally {globalThis.fetch=old;}
});
test('pinned manifest and content tampering are rejected',t=>{
  const {root,hash}=fixture(t);
  assert.throws(()=>loadOfflineSnapshot(root,'0'.repeat(64)),/snapshot_manifest_changed/);
  writeFileSync(join(root,'world-facts.json'),'{}');
  assert.throws(()=>loadOfflineSnapshot(root,hash),/snapshot_artifact_changed/);
});
test('manifest traversal and unmanifested content are rejected',t=>{
  const a=fixture(t,m=>m['../outside']='0'.repeat(64));
  assert.throws(()=>loadOfflineSnapshot(a.root,a.hash),/snapshot_member_escape/);
  const b=fixture(t);writeFileSync(join(b.root,'unexpected.txt'),'unbound');
  assert.throws(()=>loadOfflineSnapshot(b.root,b.hash),/snapshot_unmanifested_file/);
});
test('symlink and group-readable artifacts are rejected',t=>{
  const a=fixture(t);rmSync(join(a.root,'coverage.json'));symlinkSync('world-facts.json',join(a.root,'coverage.json'));
  assert.throws(()=>loadOfflineSnapshot(a.root,a.hash),/snapshot_symlink/);
  const b=fixture(t);chmodSync(join(b.root,'coverage.json'),0o644);
  assert.throws(()=>loadOfflineSnapshot(b.root,b.hash),/snapshot_private_ownership/);
});
