import test from 'node:test';
import assert from 'node:assert/strict';
import { buildWorldDesigns } from '../../scripts/genie-worlds/world-designs.mjs';
import { createBrowserFixture } from './browser-fixture.mjs';

function snapshot(change = () => {}) {
  const facts = { devices: [{ id: 'A', role: 'router', private: '192.0.2.99' }, { id: 'B', role: 'switch' }],
    physical_links: [{ id: 'link-1', endpoints: [{ device: 'A', interface: 'Ethernet1' }, { device: 'B', interface: 'Ethernet2' }], certainty: 'corroborated_in_verified_baseline', evidence: [] }],
    vlans: [{ device: 'B', kind: 'trunk_membership', source: { sha256: 'c'.repeat(64) }, data: { interface: { Ethernet2: { native_vlan: '999', vlans_allowed_active_in_mgmt_domain: '10,20,999' } } } }],
    logical_relations: [{ kind: 'ospf_adjacencies' }, { kind: 'ibgp_summary' }],
    coverage_limits: ['Historical only; later collection unavailable'], counters: { rate: null }, raw_config: 'DO_NOT_EXPORT_PASSWORD' };
  change(facts);
  return { summary: { snapshot_ref: 'independent-test', manifest_sha256: 'a'.repeat(64) }, localFacts: () => structuredClone(facts) };
}

function protocolRecords() {
  const source = { sha256: 'b'.repeat(64), outcome: 'observed' };
  return [
    { kind: 'ospf_adjacencies', source, data: { interfaces: { Ethernet1: {
      neighbors: { '192.0.2.1': { state: 'FULL/  -' } },
    } } } },
    { kind: 'ibgp_summary', source, data: { vrf: { default: { neighbor: {
      '192.0.2.2': { address_family: { ipv4: { local_as: 64512, as: 64512, state_pfxrcd: '0' } } },
    } } } } },
  ];
}

test('VLAN projection binds exact device identity to the selected cohort and preserves siblings', () => {
  for (const device of ['OUTSIDE', 'b', ' B', 'B ', '', null, undefined, 7, ['B'], { id: 'B' }]) {
    const s = snapshot(f => {
      const supported = f.vlans[0];
      f.vlans = [{ ...structuredClone(supported), device }, supported];
    }), before = s.localFacts();
    for (const d of buildWorldDesigns(s)) {
      const claims = d.provenance.filter(p => p.kind === 'vlan_membership');
      assert.deepEqual(claims.map(p => p.pointer), ['/vlans/1']);
      assert.deepEqual(claims.map(p => p.value), [{ device: 'B', port: 'Ethernet2', vlans: [10, 20] }]);
      assert.deepEqual(claims[0].source, before.vlans[1].source);
      assert.equal((d.outbound.world_setup.world_prompt.text.match(/carries VLAN/g) || []).length, 1);
      assert.deepEqual(d.coverage_limits, before.coverage_limits);
      assert.equal(d.hosted_eligible, false); assert.equal(d.export_authorized, false);
    }
    assert.deepEqual(s.localFacts(), before);
  }
  const noSelected = snapshot(f => { f.vlans[0].device = 'OUTSIDE'; });
  for (const d of buildWorldDesigns(noSelected)) {
    assert.equal(d.provenance.filter(p => p.kind === 'vlan_membership').length, 0);
    assert.doesNotMatch(d.outbound.world_setup.world_prompt.text, /carries VLAN|OUTSIDE/);
  }
});

test('VLAN and protocol provenance reject non-string digests and malformed source records', () => {
  const digest = 'b'.repeat(64);
  const invalid = [undefined, null, false, 42, digest, [], [digest],
    ...[[digest], [[digest]], { value: digest }, null, true, 123, '', digest + '\n']
      .map(sha256 => ({ sha256 }))];
  // Even arrays carrying named digest properties are not source records.
  invalid.push(Object.assign([], { sha256: digest }));
  for (const source of invalid) {
    const s = snapshot(f => {
      f.logical_relations = protocolRecords();
      for (const r of [...f.vlans, ...f.logical_relations]) r.source = source;
    }), before = s.localFacts();
    for (const d of buildWorldDesigns(s)) {
      assert.equal(d.provenance.filter(p => ['vlan_membership', 'logical_relation'].includes(p.kind)).length, 0);
      assert.doesNotMatch(d.outbound.world_setup.world_prompt.text, /carries VLAN|OSPF underlay|iBGP overlay/);
      assert.deepEqual(d.coverage_limits, before.coverage_limits);
      assert.equal(d.hosted_eligible, false); assert.equal(d.export_authorized, false);
    }
    assert.deepEqual(s.localFacts(), before);
  }
});

test('valid historical and explicit observed sources retain VLAN and protocol anchors', () => {
  for (const explicit of [false, true]) {
    const s = snapshot(f => {
      f.logical_relations = protocolRecords();
      for (const r of [...f.vlans, ...f.logical_relations]) {
        r.source = { sha256: 'b'.repeat(64) };
        if (explicit) for (const target of [r, r.source])
          Object.assign(target, { outcome: 'observed', status: 'observed' });
      }
    }), before = s.localFacts();
    for (const d of buildWorldDesigns(s)) {
      const claims = d.provenance.filter(p => ['vlan_membership', 'logical_relation'].includes(p.kind));
      assert.deepEqual(claims.map(p => p.pointer), ['/vlans/0', '/logical_relations/0', '/logical_relations/1']);
      assert.deepEqual(claims.map(p => p.source), [...before.vlans, ...before.logical_relations].map(r => r.source));
      assert.match(d.outbound.world_setup.world_prompt.text, /carries VLAN 10, 20/);
      assert.match(d.outbound.world_setup.world_prompt.text, /OSPF underlay and iBGP overlay/);
    }
    assert.deepEqual(s.localFacts(), before);
  }
});

test('iBGP evidence rejects coerced ASN containers and invalid scalar values', () => {
  const invalid = [[64512], [['64512']], { value: 64512 }, [], null, undefined,
    true, false, 0, -1, 1.5, NaN, Infinity, 4294967296, '', '0', '064512',
    ' 64512', '64512 ', '6.4512e4', '64512.0', '4294967296'];
  for (const value of invalid) for (const field of ['local_as', 'as', 'both']) {
    const s = snapshot(f => {
      f.logical_relations = protocolRecords();
      const af = f.logical_relations[1].data.vrf.default.neighbor['192.0.2.2'].address_family.ipv4;
      for (const key of field === 'both' ? ['local_as', 'as'] : [field]) af[key] = value;
    }), before = s.localFacts();
    for (const d of buildWorldDesigns(s)) {
      assert.doesNotMatch(d.outbound.world_setup.world_prompt.text, /iBGP overlay/);
      assert.match(d.outbound.world_setup.world_prompt.text, /OSPF underlay/);
      assert.deepEqual(d.provenance.filter(p => p.kind === 'logical_relation').map(p => p.pointer), ['/logical_relations/0']);
      assert.deepEqual(d.coverage_limits, before.coverage_limits);
      assert.equal(d.hosted_eligible, false); assert.equal(d.export_authorized, false);
    }
    assert.deepEqual(s.localFacts(), before);
  }
});

test('iBGP scalar ASN bounds preserve mixed types, established state and source anchors', () => {
  for (const n of [1, 64512, 4294967295]) for (const local of [n, String(n)]) for (const remote of [n, String(n)]) {
    for (const state of ['0', 0, 'Established', 'Active']) {
      const s = snapshot(f => {
        f.logical_relations = protocolRecords();
        Object.assign(f.logical_relations[1].data.vrf.default.neighbor['192.0.2.2'].address_family.ipv4,
          { local_as: local, as: remote, state_pfxrcd: state });
      }), before = s.localFacts();
      for (const d of buildWorldDesigns(s)) {
        const claims = d.provenance.filter(p => p.kind === 'logical_relation');
        assert.equal(d.outbound.world_setup.world_prompt.text.includes('iBGP overlay'), state !== 'Active');
        assert.deepEqual(claims.map(p => p.pointer), state === 'Active' ? ['/logical_relations/0'] : ['/logical_relations/0', '/logical_relations/1']);
        assert.deepEqual(claims.map(p => p.source), before.logical_relations.slice(0, claims.length).map(r => r.source));
      }
      assert.deepEqual(s.localFacts(), before);
    }
  }
});

test('unsupported protocol containers and records omit ribbons without aborting five designs', () => {
  const paths = [[], [0], [1], [0, 'data'], [0, 'data', 'interfaces'],
    [0, 'data', 'interfaces', 'Ethernet1'],
    [0, 'data', 'interfaces', 'Ethernet1', 'neighbors'],
    [0, 'data', 'interfaces', 'Ethernet1', 'neighbors', '192.0.2.1'],
    [1, 'data'], [1, 'data', 'vrf'], [1, 'data', 'vrf', 'default'],
    [1, 'data', 'vrf', 'default', 'neighbor'],
    [1, 'data', 'vrf', 'default', 'neighbor', '192.0.2.2'],
    [1, 'data', 'vrf', 'default', 'neighbor', '192.0.2.2', 'address_family'],
    [1, 'data', 'vrf', 'default', 'neighbor', '192.0.2.2', 'address_family', 'ipv4']];
  for (const path of paths) for (const value of [null, undefined, false, 42, 'unsupported', []]) {
    const s = snapshot(f => {
      f.logical_relations = protocolRecords();
      if (!path.length) f.logical_relations = value;
      else {
        let parent = f.logical_relations;
        for (const key of path.slice(0, -1)) parent = parent[key];
        parent[path.at(-1)] = value;
      }
    }), before = s.localFacts();
    const designs = buildWorldDesigns(s);
    assert.equal(designs.length, 5);
    for (const d of designs) {
      const claims = d.provenance.filter(p => p.kind === 'logical_relation');
      assert.deepEqual(claims.map(p => p.pointer), path.length ? [`/logical_relations/${1 - path[0]}`] : []);
      assert.doesNotMatch(d.outbound.world_setup.world_prompt.text,
        !path.length ? /OSPF underlay|iBGP overlay/ : path[0] === 0 ? /OSPF underlay/ : /iBGP overlay/);
      assert.deepEqual(d.coverage_limits, before.coverage_limits);
      assert.equal(d.hosted_eligible, false); assert.equal(d.export_authorized, false);
    }
    assert.deepEqual(s.localFacts(), before);
  }
});

test('malformed protocol siblings preserve established evidence and original source anchors', () => {
  const records = protocolRecords();
  const bad = { null_record: null, array_record: [], scalar_record: 'unsupported' };
  const ospf = records[0].data.interfaces.Ethernet1;
  ospf.neighbors = { ...bad, inactive: { state: 'INIT' }, ...ospf.neighbors };
  records[0].data.interfaces = { ...bad, ...records[0].data.interfaces };
  const vrf = records[1].data.vrf.default, peer = vrf.neighbor['192.0.2.2'];
  peer.address_family = { ...bad, inactive: { local_as: 64512, as: 64512, state_pfxrcd: 'Active' }, ...peer.address_family };
  vrf.neighbor = { ...bad, ...vrf.neighbor };
  records[1].data.vrf = { ...bad, ...records[1].data.vrf };
  const s = snapshot(f => { f.logical_relations = [null, [], false, ...records]; });
  const before = s.localFacts();
  for (const d of buildWorldDesigns(s)) {
    assert.match(d.outbound.world_setup.world_prompt.text, /OSPF underlay and iBGP overlay/);
    const claims = d.provenance.filter(p => p.kind === 'logical_relation');
    assert.deepEqual(claims.map(p => p.pointer), ['/logical_relations/3', '/logical_relations/4']);
    assert.deepEqual(claims.map(p => p.source), records.map(r => r.source));
    assert.doesNotMatch(JSON.stringify(d.outbound), /192\.0\.2|64512|unsupported/);
    assert.deepEqual(d.coverage_limits, before.coverage_limits);
  }
  assert.deepEqual(s.localFacts(), before);
});

test('unsupported VLAN parser containers omit cues without aborting designs or changing local facts', () => {
  const unsupported = [null, undefined, false, 42, 'unsupported', []];
  const cases = unsupported.flatMap(value => [
    f => { f.vlans = value; },
    f => { f.vlans = [value]; },
    f => { f.vlans[0].data = value; },
    f => { f.vlans[0].data.interface = value; },
    f => { f.vlans[0].data.interface.Ethernet2 = value; },
  ]);
  // An array containing plausible ports is still not a supported port map.
  cases.push(f => { f.vlans[0].data.interface = [f.vlans[0].data.interface.Ethernet2]; });
  for (const change of cases) {
    const s = snapshot(change), before = s.localFacts();
    const designs = buildWorldDesigns(s);
    assert.equal(designs.length, 5);
    for (const d of designs) {
      assert.equal(d.provenance.filter(p => p.kind === 'vlan_membership').length, 0);
      assert.doesNotMatch(d.outbound.world_setup.world_prompt.text, /carries VLAN/);
      assert.deepEqual(d.coverage_limits, before.coverage_limits);
      assert.equal(d.hosted_eligible, false);
    }
    assert.deepEqual(s.localFacts(), before);
  }
});

test('malformed VLAN records and ports preserve supported siblings and original source pointers', () => {
  const s = snapshot(f => {
    const good = f.vlans[0];
    good.data.interface = { NullPort: null, ArrayPort: [], ScalarPort: 'unsupported', ...good.data.interface };
    f.vlans = [null, [], { ...good, data: { interface: [good.data.interface.Ethernet2] } }, good];
  });
  const before = s.localFacts();
  for (const d of buildWorldDesigns(s)) {
    const claims = d.provenance.filter(p => p.kind === 'vlan_membership');
    assert.deepEqual(claims, [{ kind: 'vlan_membership', value: { device: 'B', port: 'Ethernet2', vlans: [10, 20] }, pointer: '/vlans/3', source: before.vlans[3].source }]);
    assert.match(d.outbound.world_setup.world_prompt.text, /B Ethernet2 carries VLAN 10, 20/);
    assert.doesNotMatch(JSON.stringify(d.outbound), /NullPort|ArrayPort|ScalarPort|999|PASSWORD/);
    assert.deepEqual(d.coverage_limits, before.coverage_limits);
  }
  assert.deepEqual(s.localFacts(), before);
});

test('VLAN cues reject missing provenance and negative outcomes despite plausible parsed data', () => {
  const cases = [
    r => { delete r.source; }, r => { r.source.sha256 = 'invalid'; },
    ...['empty', 'raw_only', 'parse_failed', 'timeout', 'unavailable', 'failed', null].flatMap(status =>
      ['outcome', 'status'].flatMap(field => [
        r => { r[field] = status; }, r => { r.source[field] = status; },
      ])),
  ];
  for (const change of cases) {
    const s = snapshot(f => { change(f.vlans[0]); }), before = s.localFacts();
    for (const d of buildWorldDesigns(s)) {
      assert.doesNotMatch(d.outbound.world_setup.world_prompt.text, /carries VLAN/);
      assert.equal(d.provenance.filter(p => p.kind === 'vlan_membership').length, 0);
      assert.deepEqual(d.coverage_limits, before.coverage_limits);
    }
    assert.deepEqual(s.localFacts(), before);
  }
});

test('supported VLAN cues preserve source anchors, native exclusion and bounded declarations', () => {
  for (const explicit of [false, true]) {
    const s = snapshot(f => {
      if (explicit) for (const target of [f.vlans[0], f.vlans[0].source])
        Object.assign(target, { status: 'observed', outcome: 'observed' });
    });
    for (const d of buildWorldDesigns(s)) {
      assert.match(d.outbound.world_setup.world_prompt.text, /B Ethernet2 carries VLAN 10, 20/);
      assert.doesNotMatch(JSON.stringify(d.outbound), /999|192\.0\.2|PASSWORD/);
      const claims = d.provenance.filter(p => p.kind === 'vlan_membership');
      assert.equal(claims.length, 1);
      assert.deepEqual(claims[0], { kind: 'vlan_membership', value: { device: 'B', port: 'Ethernet2', vlans: [10, 20] }, pointer: '/vlans/0', source: s.localFacts().vlans[0].source });
      assert.equal(d.hosted_eligible, false); assert.equal(d.export_authorized, false);
    }
  }
  for (const value of ['10-20', '', '999', '0,4095', Array(17).fill('10').join(',')]) {
    for (const d of buildWorldDesigns(snapshot(f => { f.vlans[0].data.interface.Ethernet2.vlans_allowed_active_in_mgmt_domain = value; })))
      assert.equal(d.provenance.filter(p => p.kind === 'vlan_membership').length, 0);
  }
});

test('protocol ribbons require sourced established relationships, not record kinds or failed reads', () => {
  const cases = [
    records => records.forEach(r => { r.data = {}; }),
    records => records.forEach(r => { delete r.source; }),
    records => records.forEach(r => { r.source = { sha256: 'invalid' }; }),
    ...['empty', 'raw_only', 'parse_failed', 'timeout', 'unavailable', 'failed'].flatMap(status => [
      records => records.forEach(r => { r.outcome = status; }),
      records => records.forEach(r => { r.source = { ...r.source, status }; }),
    ]),
    records => {
      records[0].data.interfaces.Ethernet1.neighbors['192.0.2.1'].state = 'INIT';
      records[1].data.vrf.default.neighbor['192.0.2.2'].address_family.ipv4.state_pfxrcd = 'Active';
    },
  ];
  for (const change of cases) {
    const records = protocolRecords(); change(records);
    for (const d of buildWorldDesigns(snapshot(f => { f.logical_relations = records; }))) {
      assert.doesNotMatch(d.outbound.world_setup.world_prompt.text, /OSPF underlay|iBGP overlay/);
      assert.equal(d.provenance.filter(p => p.kind === 'logical_relation').length, 0);
    }
  }
});

test('confirmed OSPF and internal BGP cues retain source anchors without exporting peer addresses', () => {
  for (const state of ['0', 2, 'Established']) {
    const records = protocolRecords();
    records[1].data.vrf.default.neighbor['192.0.2.2'].address_family.ipv4.state_pfxrcd = state;
    const s = snapshot(f => { f.logical_relations = records; });
    const before = s.localFacts();
    for (const d of buildWorldDesigns(s)) {
      assert.match(d.outbound.world_setup.world_prompt.text, /OSPF underlay and iBGP overlay/);
      assert.doesNotMatch(JSON.stringify(d.outbound), /192\.0\.2|64512/);
      const claims = d.provenance.filter(p => p.kind === 'logical_relation');
      assert.deepEqual(claims.map(p => p.pointer), ['/logical_relations/0', '/logical_relations/1']);
      assert.deepEqual(claims.map(p => p.source), records.map(r => r.source));
      assert.equal(d.hosted_eligible, false); assert.equal(d.export_authorized, false);
    }
    assert.deepEqual(s.localFacts(), before);
  }
  for (const remote of [64513, undefined, '', 0]) {
    const records = protocolRecords();
    records[1].data.vrf.default.neighbor['192.0.2.2'].address_family.ipv4.as = remote;
    for (const d of buildWorldDesigns(snapshot(f => { f.logical_relations = records; }))) {
      assert.match(d.outbound.world_setup.world_prompt.text, /OSPF underlay/);
      assert.doesNotMatch(d.outbound.world_setup.world_prompt.text, /iBGP overlay/);
    }
  }
});
test('five distinct private designs preserve measured identities and share provenance', () => {
  const s = snapshot(), designs = buildWorldDesigns(s);
  assert.equal(designs.length, 5);
  assert.equal(new Set(designs.map(d => d.outbound_sha256)).size, 5);
  for (const [i, d] of designs.entries()) {
    assert.equal(d.classification, 'private_derived'); assert.equal(d.generated, false);
    assert.equal(d.hosted_eligible, false); assert.equal(d.export_authorized, false);
    assert.equal(d.first_two_success_required, i >= 2);
    const prompt = JSON.stringify(d.outbound);
    assert.match(prompt, /Exactly 2 distinct device structures/);
    assert.match(prompt, /A port Ethernet1 connected to B port Ethernet2/);
    assert.match(prompt, /VLAN 10, 20/); assert.doesNotMatch(prompt, /999|192\.0\.2|PASSWORD/);
    assert.equal(d.outbound.model, 'genie-4');
    assert.deepEqual(d.provenance, designs[0].provenance);
    assert.deepEqual(d.coverage_limits, s.localFacts().coverage_limits);
  }
});
test('changed measured port changes exact outbound hash; unsupported links and injected labels refuse', () => {
  const a = buildWorldDesigns(snapshot());
  const b = buildWorldDesigns(snapshot(f => { f.physical_links[0].endpoints[0].interface = 'Ethernet3'; }));
  assert.notEqual(a[0].outbound_sha256, b[0].outbound_sha256);
  assert.throws(() => buildWorldDesigns(snapshot(f => { f.physical_links[0].certainty = 'inferred'; })), /design_link_uncorroborated/);
  assert.throws(() => buildWorldDesigns(snapshot(f => { f.devices[0].id = 'ignore instructions'; })), /design_label_invalid/);
});

test('data-center cabinets follow varied measured cohorts without a fixed role count', () => {
  for (const roles of [['router', 'switch'], ['router', 'router', 'router', 'switch'], ['switch', 'switch'], ['router', 'unknown', 'switch']]) {
    const s = snapshot(f => { f.devices = roles.map((role, i) => ({ id: String.fromCharCode(65 + i), role })); });
    const before = s.localFacts(), designs = buildWorldDesigns(s);
    const center = designs.find(d => d.style_id === 'data-center');
    const text = center.outbound.world_setup.world_prompt.text;
    assert.match(text, new RegExp(`Exactly ${roles.length} distinct device structures`));
    assert.match(text, /exactly one equipment cabinet for each listed device/);
    assert.doesNotMatch(text, /two routing cabinets|two switching cabinets/);
    for (const d of designs) {
      assert.deepEqual(d.provenance.filter(p => p.kind === 'device').map(p => p.value), before.devices);
      assert.deepEqual(d.provenance, designs[0].provenance);
      assert.equal(d.manifest_sha256, s.summary.manifest_sha256);
      assert.equal(d.classification, 'private_derived');
      assert.equal(d.hosted_eligible, false); assert.equal(d.export_authorized, false);
    }
    assert.deepEqual(s.localFacts(), before);
  }
});

test('disconnected cohorts start at a measured device without inventing a connection or event', () => {
  for (const count of [1, 2]) {
    const s = snapshot(f => {
      f.devices = f.devices.slice(0, count);
      f.physical_links = []; f.vlans = []; f.logical_relations = [];
    });
    const before = s.localFacts();
    for (const d of buildWorldDesigns(s)) {
      const text = d.outbound.world_setup.world_prompt.text;
      assert.match(text, /Exactly 0 physical connections/);
      assert.match(text, /Keep the A device structure in view from the starting aisle as the navigation landmark/);
      assert.doesNotMatch(text, /nearest connection|both of its endpoint structures/);
      assert.equal(d.outbound.event, null);
      assert.match(d.interaction, /Provider keyboard navigation/);
      assert.match(d.interaction, /No text event is prepared because no physical connection is evidenced/);
      assert.doesNotMatch(d.interaction, /one text event/);
      assert.match(d.interaction, /Clickable fact inspection is local UI/);
      assert.equal(d.provenance.filter(p => p.kind === 'physical_link').length, 0);
      assert.deepEqual(d.provenance.filter(p => p.kind === 'device').map(p => p.value),
        before.devices.map(({ id, role }) => ({ id, role })));
      assert.equal(d.classification, 'private_derived');
      assert.equal(d.hosted_eligible, false); assert.equal(d.export_authorized, false);
    }
    assert.deepEqual(s.localFacts(), before);
  }
});

test('linked cohorts retain their endpoint camera view and measured fictional event target', () => {
  for (const d of buildWorldDesigns(snapshot())) {
    assert.match(d.outbound.world_setup.world_prompt.text,
      /Keep the nearest connection and both of its endpoint structures in view from the starting aisle/);
    assert.doesNotMatch(d.outbound.world_setup.world_prompt.text, /as the navigation landmark/);
    assert.match(d.outbound.event.event_text, /light strip on link-1 slowly changes to amber/);
    assert.match(d.interaction, /Provider keyboard navigation and one text event/);
    assert.equal(d.provenance.filter(p => p.kind === 'physical_link').length, 1);
  }
});

test('local draft inspector shows event availability without starting a world', {
  skip: !process.env.NETCLAW_BROWSER_EXECUTABLE, timeout: 20000,
}, async t => {
  const { m, browser } = await createBrowserFixture(t, 'design-interaction-');
  const page = await browser.newPage();
  page.setDefaultTimeout(5000);
  const external = [], errors = [];
  page.on('request', request => { if (!request.url().startsWith(m.origin + '/')) external.push(request.url()); });
  page.on('pageerror', error => errors.push(error.message));
  // Synthetic HTTP fixtures exercise the real local inspector. They never
  // enter the snapshot registry, draft ledger or hosted admission path.
  let s;
  await page.route('**/v1/snapshots', route => route.fulfill({ json: [{
    ...s.summary, devices: s.localFacts().devices.length, physical_links: s.localFacts().physical_links.length,
  }] }));
  await page.route('**/v1/drafts', route => route.fulfill({ json: { projection_ref: 'synthetic-inspector' } }));
  await page.route('**/v1/drafts/synthetic-inspector/facts', route => route.fulfill({ json: {
    summary: { ...s.summary, files_verified: 0 }, facts: s.localFacts(), coverage: [],
  } }));
  await page.route('**/v1/drafts/synthetic-inspector/styles', route => route.fulfill({ json: buildWorldDesigns(s) }));
  for (const linked of [false, true]) {
    s = snapshot(f => {
      if (!linked) { f.devices = f.devices.slice(0, 1); f.physical_links = []; f.vlans = []; f.logical_relations = []; }
      else {
        f.vlans[0].data.interface.UnknownPort = null;
        f.logical_relations = protocolRecords();
        f.logical_relations[0].data.interfaces = { UnknownPort: null, ...f.logical_relations[0].data.interfaces };
        f.logical_relations[1].data.vrf = { UnknownVrf: null, ...f.logical_relations[1].data.vrf };
      }
    });
    await page.goto(m.origin + '/#' + m.bootstrap);
    await page.locator('#snapshots button').click();
    await page.waitForFunction(() => document.querySelector('#world-designs').children.length === 5);
    await page.locator('#snapshot-items button').first().click();
    assert.equal(JSON.parse(await page.locator('#snapshot-fact').textContent()).id, 'A');
    for (let i = 0; i < 5; i++) {
      await page.locator('#world-designs button').nth(i).click();
      const displayed = JSON.parse(await page.locator('#world-design').textContent());
      assert.equal(Boolean(displayed.outbound.event), linked);
      assert.equal(displayed.interaction.includes('one text event'), linked);
      assert.equal(displayed.interaction.includes('No text event is prepared'), !linked);
      assert.equal(displayed.hosted_eligible, false);
      assert.equal(displayed.export_authorized, false);
      if (linked) assert.match(displayed.outbound.world_setup.world_prompt.text, /OSPF underlay and iBGP overlay/);
    }
    assert.equal(m.ledger.list().length, 0);
    assert.equal(await page.locator('#event').isDisabled(), true);
  }
  assert.deepEqual(external, []);
  assert.deepEqual(errors, []);
});
