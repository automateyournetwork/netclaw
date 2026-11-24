import { need, hash } from './model.mjs';

const STYLES = Object.freeze([
  ['blueprint', 'Futuristic technical blueprint',
    'A walkable engineering drawing made physical: translucent smoked-glass routing halls, brushed titanium switching rooms, crisp cyan cable channels and warm white port rings. A charcoal drafting grid extends across a solid floor. Each evidenced cable is one continuous visible conduit. Precise construction, believable materials and restrained holographic VLAN planes.'],
  ['fantasy', 'Living fantasy network',
    'A luminous hand-painted fantasy realm: routing citadels of pale stone, switching groves with copper-leaf canopies, and exactly the evidenced connections as walkable root-and-crystal bridges. VLAN groups occupy distinct small garden terraces. Gentle motes and swaying leaves give the realm life. Ports are clearly bounded bronze gates.'],
  ['network-city', 'Cinematic network city',
    'A miniature cinematic metropolis at blue hour: routing towers and switching stations joined only by the evidenced elevated transit paths. VLAN groups have colored plaza canopies. Wet stone, restrained neon wayfinding and warm interior light. One continuous street-level viewpoint, quiet architectural scale.'],
  ['packet-scale', 'Inside the network machinery',
    'A playful macro-scale network machine: routing chambers, switch matrices and huge interface gates connected by transparent cable conduits. Ceramic, brass and translucent polymer surfaces. Illustrative glowing packet capsules move slowly; their speed and number do not claim measured traffic. VLAN groups are distinct colored sorting bays.'],
  ['data-center', 'Realistic future data center',
    'A photorealistic future equipment facility with exactly one equipment cabinet for each listed device; cabinet roles follow the measured device roster. Clean service aisles, believable fiber trays, visible bounded interface sockets, cool overhead lighting and warm status lamps. Show only evidenced inter-device cable paths. VLAN groups are local colored cable-management zones.'],
]);

const label = value => {
  need(typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9./_-]{0,95}$/.test(value), 'design_label_invalid');
  return value;
};

const isRecord = value => value !== null && typeof value === 'object' && !Array.isArray(value);
// Unsupported parser entries remain in local facts, never protocol evidence.
const entries = value => isRecord(value) ? Object.values(value).filter(isRecord) : [];
function sourcedObservation(record) {
  // The sealed baseline predates explicit outcome fields. Its parsed state and
  // source digest are required; any later negative outcome overrides that state.
  if (!isRecord(record.source) || typeof record.source.sha256 !== 'string'
    || record.source.sha256.length !== 64 || !/^[a-f0-9]{64}$/.test(record.source.sha256)) return false;
  for (const evidence of [record, record.source])
    for (const field of ['outcome', 'status'])
      if (evidence[field] !== undefined && evidence[field] !== 'observed') return false;
  return true;
}

function confirmedProtocol(record) {
  if (!isRecord(record) || !isRecord(record.data) || !sourcedObservation(record)) return false;
  if (record.kind === 'ospf_adjacencies')
    return entries(record.data?.interfaces).some(port => entries(port.neighbors).some(peer =>
      typeof peer.state === 'string' && /^FULL(?:\s*\/\s*(?:-|DR|BDR|DROTHER))?$/i.test(peer.state)));
  if (record.kind !== 'ibgp_summary') return false;
  const asn = value => (typeof value === 'number' || typeof value === 'string')
    && /^(?:[1-9]\d{0,9})$/.test(String(value)) && Number(value) <= 4294967295;
  return entries(record.data?.vrf).some(vrf => entries(vrf.neighbor).some(peer =>
    entries(peer.address_family).some(af => {
      const state = af.state_pfxrcd;
      // A numeric prefix count (including zero) denotes an established session
      // in this Genie summary shape. Matching ASNs distinguish iBGP from eBGP.
      return asn(af.local_as) && asn(af.as) && Number(af.local_as) === Number(af.as)
        && (state === 'Established' || (typeof state === 'string' && /^\d+$/.test(state))
          || (Number.isSafeInteger(state) && state >= 0));
    })));
}

// Deliberately local-only. No provider adapter imports this builder. An exact
// export grant is a separate future boundary; these are private-derived drafts.
export function buildWorldDesigns(snapshot) {
  const facts = snapshot.localFacts();
  const selectedDevices = new Set(facts.devices.map(d => d.id));
  const claims = [], description = [];
  facts.devices.forEach((d, i) => {
    const id = label(d.id), role = label(d.role);
    description.push(`${id}: ${role}`);
    claims.push({ kind: 'device', value: { id, role }, pointer: `/devices/${i}`, source: d.source || null });
  });
  const links = facts.physical_links.map((l, i) => {
    const id = label(l.id);
    need(l.certainty === 'corroborated_in_verified_baseline', 'design_link_uncorroborated');
    const ends = l.endpoints.map(e => `${label(e.device)} port ${label(e.interface)}`);
    claims.push({ kind: 'physical_link', value: { id, endpoints: l.endpoints }, pointer: `/physical_links/${i}`, evidence: l.evidence || [] });
    return `${id}: ${ends.join(' connected to ')}`;
  });
  const vlanGroups = [];
  for (const [i, entry] of (Array.isArray(facts.vlans) ? facts.vlans : []).entries()) {
    if (!isRecord(entry) || entry.kind !== 'trunk_membership' || !sourcedObservation(entry)
      || !selectedDevices.has(entry.device)) continue;
    // Unsupported parser containers remain in local facts. Only record-shaped
    // port maps/entries can supply cues; preserve supported sibling observations.
    if (!isRecord(entry.data) || !isRecord(entry.data.interface)) continue;
    for (const [port, data] of Object.entries(entry.data.interface)) {
      if (!isRecord(data)) continue;
      const value = data.vlans_allowed_active_in_mgmt_domain;
      // Ranges and missing parser fields remain in the local inspector. Never
      // expand arbitrary unbounded VLAN declarations into a visual claim.
      if (typeof value !== 'string' || !/^\d{1,4}(,\d{1,4}){0,15}$/.test(value)) continue;
      const vlans = value.split(',').map(Number).filter(v => v > 0 && v < 4095 && String(v) !== String(data.native_vlan));
      if (!vlans.length) continue;
      vlanGroups.push(`${label(entry.device)} ${label(port)} carries VLAN ${vlans.join(', ')}`);
      claims.push({ kind: 'vlan_membership', value: { device: entry.device, port, vlans }, pointer: `/vlans/${i}`, source: entry.source });
    }
  }
  const protocolKinds = [];
  for (const [i, relation] of (Array.isArray(facts.logical_relations) ? facts.logical_relations : []).entries()) {
    if (isRecord(relation) && Object.hasOwn(relation,'device') && !selectedDevices.has(relation.device)) continue;
    if (!confirmedProtocol(relation)) continue;
    protocolKinds.push(relation.kind);
    claims.push({ kind: 'logical_relation', value: { protocol: relation.kind },
      pointer: `/logical_relations/${i}`, source: relation.source });
  }
  const protocolText = [protocolKinds.includes('ospf_adjacencies') ? 'OSPF underlay' : null,
    protocolKinds.includes('ibgp_summary') ? 'iBGP overlay' : null].filter(Boolean).join(' and ');
  const camera = links.length
    ? 'Keep the nearest connection and both of its endpoint structures in view from the starting aisle.'
    : `Keep the ${label(facts.devices[0].id)} device structure in view from the starting aisle as the navigation landmark. No physical connections are evidenced; do not add any.`;
  const common = `Immersive first-person walkable network exhibition, continuous eye-level viewpoint. Exactly ${facts.devices.length} distinct device structures: ${description.join('; ')}. Exactly ${links.length} physical connections: ${links.join('; ')}. ${vlanGroups.length ? vlanGroups.join('; ') + '.' : ''} ${protocolText ? `Use distinct fine light ribbons as an illustration of ${protocolText}; these ribbons are not additional physical links.` : ''} Preserve each device identity and the exact adjacency arrangement while walking and looking back. ${camera} Use large simple device labels, not invented numeric readouts. All observations are a frozen historical network snapshot; scenery is illustrative, never current health or a routing simulation. Management connections are excluded. Traffic animations are decorative, never measured counters. Keep routes clear for navigation. Audio: soft footsteps and a quiet environmental hum. No cuts, teleportation or extra network structures.`;
  return STYLES.map(([id, title, style], i) => {
    const text = common + '\n\nVisual direction: ' + style;
    const event = facts.physical_links.length ? {
      event_id: 'snapshot-link-amber-v1',
      event_text: `The visible light strip on ${label(facts.physical_links[0].id)} slowly changes to amber. Keep the physical connection and both endpoint structures intact. This is one fictional lighting event; no other structure or measured network state changes.`,
    } : null;
    const outbound = { model: 'genie-4', world_setup: { event_type: 'world_setup', world_prompt: { text } }, event };
    need(Buffer.byteLength(JSON.stringify(outbound)) <= 8192, 'design_projection_bound');
    return { schema: 1, style_id: id, title, order: i + 1, classification: 'private_derived',
      snapshot_ref: snapshot.summary.snapshot_ref, manifest_sha256: snapshot.summary.manifest_sha256,
      generated: false, hosted_eligible: false, export_authorized: false,
      first_two_success_required: i >= 2, outbound, outbound_sha256: hash(outbound),
      provenance: claims, coverage_limits: facts.coverage_limits,
      local_only_fields: ['IP addresses and prefixes', 'raw configuration and credentials', 'counter samples and unqualified rates', 'complete routing tables', 'management interfaces'],
      interaction: (event ? 'Provider keyboard navigation and one text event.'
        : 'Provider keyboard navigation. No text event is prepared because no physical connection is evidenced.')
        + ' Clickable fact inspection is local UI; no persistent provider object API is assumed.' };
  });
}
