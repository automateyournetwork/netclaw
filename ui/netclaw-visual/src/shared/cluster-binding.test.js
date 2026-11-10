import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { verifyClusterDescriptor, clusterAudience, clusterReviewMatches, clusterCanDecide, clusterStatusText, regionLabel, clusterNodeRegion, clusterFailoverNotice } from './cluster-binding.js';
const fixture = JSON.parse(fs.readFileSync(new URL('../../../../tests/fixtures/ha-179/cluster-golden.json', import.meta.url)));
const value = fixture.descriptors[0], options = { pin: fixture.pin, origin: value.manifest.manifest.nodes[0].endpoints.https, installationId: value.installation_id, now: fixture.now_ms };
test('Python-generated P256 manifest binds distinct node and stable cluster audience', async () => {
 const result = await verifyClusterDescriptor(value, options);
 assert.equal(result.pin.manifest_sha256, fixture.canonical_manifest_sha256);
 assert.notEqual(result.descriptor.installation_id, result.pin.cluster_id);
 assert.equal(clusterAudience(result.descriptor, fixture.principal), clusterAudience(fixture.descriptors[1], fixture.principal));
 await assert.rejects(verifyClusterDescriptor(value, {...options, pin:undefined}), /cluster_onboarding_required/);
 const initial = await verifyClusterDescriptor(value, {...options, pin:undefined, acceptedAnchor:fixture.anchor_key_id});
 assert.deepEqual(initial.pin, fixture.pin);
});
test('trusted endpoint selection preserves generation and monotone signed manifest', async () => {
 const second = fixture.descriptors[1];
 await verifyClusterDescriptor(second, {...options, origin:second.manifest.manifest.nodes[1].endpoints.https, installationId:second.installation_id});
 const updated = await verifyClusterDescriptor(fixture.updated_descriptor, {...options, origin:second.manifest.manifest.nodes[1].endpoints.https, installationId:second.installation_id});
 await assert.rejects(verifyClusterDescriptor(value, {...options, pin:updated.pin}), /stale_manifest/);
});
test('untrusted anchor, endpoint, node, generation, signature and reused revision are refused', async () => {
 for (const change of [d=>d.generation='11111111-1111-4111-8111-111111111111',d=>d.node_id='11111111-1111-4111-8111-111111111111',d=>d.installation_id=d.cluster_id,d=>d.manifest.manifest.organization='forged',d=>d.anchor_key_id='a'.repeat(64),d=>d.authority.state='available']) {
  const d=structuredClone(value);change(d);await assert.rejects(verifyClusterDescriptor(d, options));
 }
 await assert.rejects(verifyClusterDescriptor(value, {...options,origin:'https://unregistered.example.test'}));
 await assert.rejects(verifyClusterDescriptor(value, {...options,pin:{...fixture.pin,manifest_sha256:'a'.repeat(64)}}));
 await assert.rejects(verifyClusterDescriptor(value, {...options,now:Date.UTC(2041,0,1)}));
});
test('old issuer is retained for status but old epoch and quorum loss cannot enable decision', () => {
 const c=value.manifest.manifest, n=c.nodes[0];
 const operation={review:{cluster:{cluster_id:c.cluster_id,generation:c.generation,manifest_revision:1,issuer_node_id:n.node_id,authority_epoch:7},border:{installation_id:n.installation_id,key_id:n.key_id},principal:fixture.principal}};
 assert.equal(clusterReviewMatches(value,operation.review,fixture.principal),true);
 assert.equal(clusterCanDecide(value,operation),true);
 assert.equal(clusterCanDecide({...value,authority:{...value.authority,epoch:8}},operation),false);
 assert.equal(clusterCanDecide(fixture.no_quorum,operation),false);
 assert.equal(clusterCanDecide(fixture.retired,operation),false);
 assert.match(clusterStatusText(fixture.no_quorum),/quorum/i);
});

test('cross-language negative golden descriptors fail closed and unknown work never becomes a new decision',async()=>{
 for(const row of fixture.negative_descriptors)await assert.rejects(verifyClusterDescriptor(row.descriptor,{pin:row.pin,now:fixture.now_ms}),error=>error.code===row.error,row.case);
 assert.equal(clusterCanDecide(fixture.descriptors[0],fixture.unknown_operation),false);
});

test('region label is display-only and unknown names stay usable', () => {
 assert.equal(regionLabel('https://nne1-3fa9c2.automateyournetwork.com'),'Montreal');
 assert.equal(regionLabel('ew1-b71d04.automateyournetwork.com'),'Belgium');
 assert.equal(regionLabel('ase1-9c2e55.automateyournetwork.com'),'Singapore');
 for (const bad of ['https://evil.example/nne1-3fa9c2.automateyournetwork.com','nne1-3fa9c.automateyournetwork.com','nne1-3fa9c2.automateyournetwork.com.evil.io','',undefined]) assert.equal(regionLabel(bad),'Unknown region');
 assert.equal(clusterNodeRegion(undefined,'x'),'Unknown region');
 assert.equal(clusterFailoverNotice({node_id:'a',authority:{state:'no_quorum'}}).includes('No quorum'),true);
 assert.equal(clusterFailoverNotice({node_id:'a',authority:{state:'leader',leader_node_id:'a'}}),'');
});
