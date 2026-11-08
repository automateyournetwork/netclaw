import test from 'node:test';
import assert from 'node:assert/strict';
import { load } from './load.mjs';
test('region label is display-only; unknown or spoofed names stay "Unknown region"', async () => {
  const { regionLabel, clusterNodeRegion, clusterFailoverNotice } = await load('src/client/cluster.ts');
  assert.equal(regionLabel('https://nne1-3fa9c2.automateyournetwork.com'), 'Montreal');
  assert.equal(regionLabel('ew1-b71d04.automateyournetwork.com'), 'Belgium');
  assert.equal(regionLabel('ase1-9c2e55.automateyournetwork.com'), 'Singapore');
  for (const bad of ['https://evil.example/nne1-3fa9c2.automateyournetwork.com', 'nne1-3fa9c.automateyournetwork.com', 'nne1-3fa9c2.automateyournetwork.com.evil.io', '', undefined]) assert.equal(regionLabel(bad), 'Unknown region');
  assert.equal(clusterNodeRegion(undefined, 'x'), 'Unknown region');
  const c = { node_id: 'a', manifest: { manifest: { nodes: [{ node_id: 'b', endpoints: { https: 'https://ew1-b71d04.automateyournetwork.com' } }] } }, authority: { state: 'follower', leader_node_id: 'b' } };
  assert.equal(clusterFailoverNotice(c), 'Forwarding to the Belgium authority.');
  assert.match(clusterFailoverNotice({ node_id: 'a', authority: { state: 'no_quorum' } }), /No quorum/);
  assert.equal(clusterFailoverNotice({ node_id: 'a', authority: { state: 'leader', leader_node_id: 'a' } }), undefined);
});
