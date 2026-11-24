"""Local-only normalization. Generated scenery is never an input to this module."""
from datetime import datetime, timezone
import hashlib
import json
import re
from fractions import Fraction

COMMANDS = ('show version', 'show ip interface brief', 'show lldp neighbors detail')
DETAILED_COMMANDS = COMMANDS + ('show cdp neighbors detail', 'show interfaces', 'show interfaces')
PROFILES = {'initial': (COMMANDS, 180), 'detailed': (DETAILED_COMMANDS, 240)}


def label(value):
    return re.sub(r'[\x00-\x1f\x7f]', '', str(value))[:128]


def cdp_claims(parsed, provenance, observation):
    """Extract IOS-XE Genie CDP detail claims, without binding ports or expiry.

    Only the installed parser's index shape is supported. A hold-time reading
    has no qualified acquisition instant; it cannot manufacture expires_at.
    Identity text is exact or unavailable, never a truncated matching alias.
    """
    if not isinstance(parsed, dict):
        return None
    rows, count = parsed.get('index', {}), parsed.get('total_entries_displayed')
    if not isinstance(rows, dict) or type(count) is not int or count != len(rows):
        return None
    if count > 256:
        raise ValueError('neighbor_limit')
    if any(not isinstance(row, dict) or not re.fullmatch(r'[1-9][0-9]*', str(key))
           for key, row in rows.items()):
        return None
    def identity(value):
        return value if isinstance(value, str) and value and label(value) == value else None
    claims = []
    for key, row in rows.items():
        path = ['index', str(key)]
        local, remote, port = (identity(row.get(k)) for k in
                              ('local_interface', 'device_id', 'port_id'))
        complete = all((local, remote, port))
        hold = row.get('hold_time')
        claims.append({**provenance, 'protocol':'cdp', 'local_interface':local,
                       'remote_claim':remote, 'remote_identity_kind':'cdp_device_id',
                       'remote_port':port, 'source_path':path,
                       'field_paths':{name:path+[field] for name,field in
                           (('local_interface','local_interface'),('remote_claim','device_id'),
                            ('remote_port','port_id'),('hold_time_seconds','hold_time')) if field in row},
                       'started_at':observation.get('started_at'),
                       'finished_at':observation['finished_at'],
                       'hold_time_seconds':hold if type(hold) is int and 0 <= hold <= 65535 else None,
                       'expires_at':None, 'resolved_device_ref':None,
                       'certainty':'one_sided' if complete else 'unknown',
                       'reason':'identity_unresolved' if complete else 'incomplete_identity'})
    return claims


def lldp_claims(parsed, provenance, observation):
    """Extract installed IOS-XE LLDP detail fields, without alias/subtype inference.

    Genie expands local/remote interface names and keys neighbors by system name.
    Neither those keys nor a MAC-looking chassis value establishes an on-wire
    subtype. Preserve parser-reported identities and require later qualification.
    Count agreement also detects collapsed repeated neighbor keys.
    """
    if not isinstance(parsed, dict) or type(parsed.get('total_entries')) is not int:
        return None
    count = parsed['total_entries']
    if count > 256:
        raise ValueError('neighbor_limit')
    interfaces = parsed.get('interfaces', {})
    if count < 0 or not isinstance(interfaces, dict):
        return None
    if len(interfaces) > 256:
        raise ValueError('neighbor_limit')
    def identity(value):
        return value if (isinstance(value, str) and value and label(value) == value
                         and value not in ('N/A', 'not advertised')) else None
    claims = []
    for interface, data in interfaces.items():
        if (not isinstance(interface, str) or not isinstance(data, dict)
                or not isinstance(data.get('port_id'), dict)
                or ('if_name' in data and data['if_name'] != interface)):
            return None
        local_path = ['interfaces', interface]
        if len(data['port_id']) > 256:
            raise ValueError('neighbor_limit')
        for port, detail in data['port_id'].items():
            if (not isinstance(port, str) or not isinstance(detail, dict)
                    or not isinstance(detail.get('neighbors'), dict)):
                return None
            if len(detail['neighbors']) > 256:
                raise ValueError('neighbor_limit')
            for neighbor, row in detail['neighbors'].items():
                if (not isinstance(neighbor, str) or not isinstance(row, dict)
                        or ('port_id' in row and row['port_id'] != port)
                        or ('neighbor_id' in row and row['neighbor_id'] != neighbor)):
                    return None
                if len(claims) >= 256:
                    raise ValueError('neighbor_limit')
                path = local_path + ['port_id', port, 'neighbors', neighbor]
                local, remote, remote_port = (identity(data.get('if_name')),
                    identity(row.get('chassis_id')), identity(row.get('port_id')))
                complete = all((local, remote, remote_port))
                hold = row.get('time_remaining')
                paths = {name:path+[field] for name,field in
                    (('remote_claim','chassis_id'), ('remote_port','port_id'),
                     ('hold_time_seconds','time_remaining')) if field in row}
                if 'if_name' in data:
                    paths['local_interface'] = local_path + ['if_name']
                claims.append({**provenance, 'protocol':'lldp', 'local_interface':local,
                    'remote_claim':remote, 'remote_identity_kind':'chassis_id',
                    'remote_port':remote_port, 'remote_port_kind':'port_id',
                    'chassis_id_subtype':None, 'port_id_subtype':None,
                    'source_path':path, 'field_paths':paths,
                    'started_at':observation.get('started_at'),
                    'finished_at':observation['finished_at'],
                    'hold_time_seconds':hold if type(hold) is int and 0 <= hold <= 65535 else None,
                    'expires_at':None, 'resolved_device_ref':None,
                    'certainty':'one_sided' if complete else 'unknown',
                    'reason':'identity_unresolved' if complete else 'incomplete_identity'})
    return claims if len(claims) == count else None


def interface_readings(parsed, provenance, observation):
    """Bounded IOS-XE ShowInterfaces fields, not inventory bindings or rates.

    Genie expands names and derives oper_status from line_protocol. Preserve
    parser fields separately; neither proves a native alias or acquisition time.
    BW is not a qualified directional capacity and is deliberately excluded.
    """
    if not isinstance(parsed, dict) or not parsed:
        return None
    if len(parsed) > 256:
        raise ValueError('interface_limit')
    state_fields = ('enabled', 'oper_status', 'line_protocol')
    for name, row in parsed.items():
        if (not isinstance(name, str) or not name or label(name) != name
                or not isinstance(row, dict)
                or not any(k in row for k in (*state_fields, 'counters'))
                or not isinstance(row.get('counters', {}), dict)):
            return None
    readings = []
    for name, row in sorted(parsed.items()):
        common = {**provenance, 'classification':'private',
                  'command':observation['command'], 'interface_name':name,
                  'started_at':observation.get('started_at'),
                  'finished_at':observation['finished_at']}
        state = {}
        for field in state_fields:
            value = row.get(field)
            valid = type(value) is bool if field == 'enabled' else value in ('up', 'down')
            state[field] = dict(value=value if valid else None,
                source_path=[name, field] if field in row else None,
                certainty='observed' if valid else 'unknown',
                reason=None if valid else 'field_missing' if field not in row else 'invalid_state')
        counters = row.get('counters', {})
        samples = []
        for field, direction, units in (('in_octets','in','bytes'), ('out_octets','out','bytes'),
                                         ('in_pkts','in','packets'), ('out_pkts','out','packets')):
            value = counters.get(field)
            valid = type(value) is int and 0 <= value < 2**64
            samples.append({**common, 'field':field, 'direction':direction, 'units':units,
                'value':str(value) if valid else None,
                'source_path':[name,'counters',field] if field in counters else None,
                'outcome':'observed' if valid else 'unknown',
                'reason':None if valid else 'field_missing' if field not in counters else 'invalid_counter',
                'sampled_at':None, 'incarnation':None, 'width':None})
        readings.append({**common, 'source_path':[name], 'resolved_interface_id':None,
                         'state':state, 'counter_samples':samples})
    return readings


def normalize(observations, now=None, *, profile='initial'):
    """Normalize allowlisted fields; leave relationships unresolved without identity proof."""
    if profile not in PROFILES:
        raise ValueError('collection_profile')
    commands = PROFILES[profile][0]
    if not isinstance(observations, list) or len(observations) > 4 * len(commands):
        raise ValueError('observation_limit')
    devices = {o['device_ref'] for o in observations}
    if len(devices) > 4:
        raise ValueError('device_limit')
    now = now or datetime.now(timezone.utc)
    facts, neighbors, interfaces = [], [], []
    for o in observations:
        if o['command'] not in commands or o['classification'] != 'private':
            raise ValueError('private_observation_required')
        stamp = datetime.fromisoformat(o['finished_at'].replace('Z', '+00:00'))
        stale = (now - stamp).total_seconds() > 300
        provenance = {'observation_id': o['id'], 'device_ref': o['device_ref'],
                      'observed_at': o['finished_at'], 'sha256': o['sha256'],
                      'parser_version': o['parser_version'], 'stale': stale}
        def add(kind, value, source_path):
            facts.append({**provenance, 'kind': kind, 'value': value,
                          'source_path': source_path, 'certainty': 'observed'})
        if o['outcome'] != 'observed':
            facts.append({**provenance, 'kind': o['command'], 'value': None,
                          'source_path': None, 'certainty': 'unknown', 'outcome': o['outcome']})
            continue
        if o['command'] in ('show cdp neighbors detail', 'show lldp neighbors detail'):
            is_cdp = o['command'] == 'show cdp neighbors detail'
            claims = (cdp_claims if is_cdp else lldp_claims)(o.get('parsed'), provenance, o)
            if claims is not None:
                if len(neighbors) + len(claims) > 256:
                    raise ValueError('neighbor_limit')
                neighbors.extend(claims)
                add(('cdp' if is_cdp else 'lldp') + '.reported_entries', len(claims),
                    ['total_entries_displayed' if is_cdp else 'total_entries'])
                continue
        if o['command'] == 'show interfaces':
            readings = interface_readings(o.get('parsed'), provenance, o)
            if readings is not None:
                interfaces.extend(readings)
                continue
        # Unqualified shapes and interface counter continuity remain unknown.
        if o['command'] not in COMMANDS or o['command'] == 'show lldp neighbors detail':
            facts.append({**provenance, 'kind': o['command'], 'value': None,
                          'source_path': None, 'certainty': 'unknown',
                          'outcome': o['outcome'], 'reason': 'normalization_unqualified'})
            continue
        parsed = o.get('parsed') or {}
        if o['command'] == 'show version':
            for name in ('version', 'hostname', 'platform', 'os'):
                value = parsed.get('version', {}).get(name)
                if value is not None:
                    add(name, label(value), ['version', name])
        elif o['command'] == 'show ip interface brief':
            for interface, value in list(parsed.get('interface', {}).items())[:256]:
                for name in ('status', 'protocol', 'ip_address'):
                    if name in value:
                        add('interface.' + name, {'interface': label(interface), 'value': label(value[name])}, ['interface', interface, name])
    return {'classification': 'private', 'facts': facts, 'neighbor_observations': neighbors,
            'interface_observations': interfaces,
            'links': [], 'link_coverage': 'unresolved_neighbor_identities',
            'hosted_eligible': False}


def evidence_hash(raw):
    return hashlib.sha256(raw.encode('utf8')).hexdigest()


def interface_counter_graph(devices, interfaces, observations, identity_observations,
                            *, graph_id, now):
    """Assemble private parser counter evidence using qualified exact aliases.

    This narrow interface-only bridge does not qualify inventory aliases, infer
    neighbors or combine parser states into health. Its returned normalization
    retains those separate readings for the later discovery/state assembler.
    Missing native sample slots and unresolved local names stay explicit outside
    geometry. No sample timestamp, capacity or continuity assertion is created.
    """
    if (not isinstance(observations, list) or len(observations) > 8
            or any(not isinstance(o, dict) or o.get('command') != 'show interfaces'
                   for o in observations)):
        raise ValueError('interface_observations_required')
    if not isinstance(identity_observations, list) or len(identity_observations) > 120:
        raise ValueError('identity_observation_limit')
    slots = set()
    counts = {}
    for source in observations:
        device = source.get('device_ref')
        if not isinstance(device, str):
            raise ValueError('invalid_graph_source')
        counts[device] = counts.get(device, 0) + 1
        if counts[device] > 2:
            raise ValueError('interface_sample_limit')
        slot = source.get('sample_index')
        if type(slot) is int and slot in (1, 2):
            if (device, slot) in slots:
                raise ValueError('duplicate_interface_sample')
            slots.add((device, slot))
    catalog = identity_observations + observations
    # Validate identity proofs, ownership, intervals and the entire observation
    # catalog before using any alias. Duplicate IDs cannot overwrite evidence.
    local_graph(devices, interfaces, [], catalog, graph_id=graph_id, now=now)
    normalized = normalize(observations, profile='detailed',
                           now=datetime.fromisoformat(now.replace('Z', '+00:00')))
    entries, unbound = _counter_inputs(interfaces, observations, normalized)
    graph = local_graph(devices, interfaces, [], catalog, graph_id=graph_id, now=now,
                        counters=entries)
    return dict(classification='private', hosted_eligible=False, graph=graph,
                normalization=normalized, unbound_interfaces=unbound)


def _counter_inputs(interfaces, observations, normalized):
    """Return graph inputs, never concatenate independently rendered graphs."""
    index = {}
    for port in interfaces:
        for identity in port['identities']:
            if identity['kind'] == 'interface_name':
                index.setdefault((port['device_id'], identity['value']), set()).add(port['id'])
    sources = {o['id']: o for o in observations}
    entries, unbound, occupied = {}, [], set()
    for reading in normalized['interface_observations']:
        matches = index.get((reading['device_ref'], reading['interface_name']), set())
        source = sources[reading['observation_id']]
        slot = source.get('sample_index')
        reason = ('unmatched_interface' if not matches else 'ambiguous_interface' if len(matches) != 1
                  else 'sample_slot_unknown' if type(slot) is not int or slot not in (1, 2) else None)
        if reason:
            unbound.append(dict(observation_id=reading['observation_id'], device_ref=reading['device_ref'],
                                interface_name=reading['interface_name'], reason=reason))
            continue
        port_id = next(iter(matches))
        key = (port_id, slot)
        if key in occupied:
            raise ValueError('duplicate_interface_sample')
        occupied.add(key)
        for sample in reading['counter_samples']:
            key = (port_id, sample['field'])
            digest = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:24]
            entry = entries.setdefault(key, dict(id='counter-'+digest, interface_id=port_id,
                field=sample['field'], direction=sample['direction'], first=None, second=None))
            # An absent field has no source path. Keep its unknown extraction in
            # normalization; do not invent evidence for a nonexistent field.
            if sample['source_path'] is None:
                continue
            proof = {k: source[k] for k in ('device_ref','source','command','parser_version','outcome','sha256')}
            proof.update(observation_id=source['id'], source_path=list(sample['source_path']))
            sample_id = 'sample-'+hashlib.sha256(json.dumps([source['id'], *key]).encode()).hexdigest()[:24]
            entry['first' if slot == 1 else 'second'] = dict(sample, id=sample_id,
                device_id=reading['device_ref'], interface_id=port_id, evidence=proof)
    return ([entries[k] for k in sorted(entries)],
            sorted(unbound, key=lambda r:(r['observation_id'],r['interface_name'])))


def cdp_neighbor_graph(devices, interfaces, observations, identity_observations,
                       *, graph_id, now):
    """Bind exact CDP device/port IDs to qualified inventory, without collecting."""
    return _neighbor_graph(devices, interfaces, observations, identity_observations,
                           graph_id=graph_id, now=now, protocol='cdp')


def lldp_neighbor_graph(devices, interfaces, observations, identity_observations,
                        *, graph_id, now):
    """Bind LLDP chassis/port IDs; absent native subtypes remain unknown.

    Normalization retains subtype nulls and field paths. System names and
    MAC-looking text never supply aliases or a chassis subtype. Inventory alias
    qualification is still a native dependency, not established by this bridge.
    """
    return _neighbor_graph(devices, interfaces, observations, identity_observations,
                           graph_id=graph_id, now=now, protocol='lldp')


def _neighbor_graph(devices, interfaces, observations, identity_observations,
                    *, graph_id, now, protocol):
    """Bind normalized discovery claims to qualified inventory, without collecting.

    Local parser interface names require exact device-scoped interface_name
    aliases. Remote chassis/CDP IDs and port IDs retain their types; no label, hostname,
    abbreviation or interface-name fallback is permitted. Unknown expiry remains
    unknown even with reciprocal evidence. Unbindable claims stay outside geometry.
    """
    if (not isinstance(observations, list) or len(observations) > 4
            or any(not isinstance(o, dict) or o.get('command') != 'show '+protocol+' neighbors detail'
                   or not isinstance(o.get('device_ref'), str) for o in observations)):
        raise ValueError(protocol+'_observations_required')
    if len({o['device_ref'] for o in observations}) != len(observations):
        raise ValueError('duplicate_'+protocol+'_capture')
    if not isinstance(identity_observations, list) or len(identity_observations) > 124:
        raise ValueError('identity_observation_limit')
    catalog = identity_observations + observations
    # Validate the entire inventory proof catalog before using any identity.
    local_graph(devices, interfaces, [], catalog, graph_id=graph_id, now=now)
    normalized = normalize(observations, profile='detailed',
                           now=datetime.fromisoformat(now.replace('Z', '+00:00')))
    claims, unbound = _neighbor_inputs(interfaces, observations, normalized)
    graph = local_graph(devices, interfaces, claims, catalog, graph_id=graph_id, now=now)
    return dict(classification='private', hosted_eligible=False, graph=graph,
                normalization=normalized, unbound_neighbors=unbound)


def _neighbor_inputs(interfaces, observations, normalized):
    """Bind both discovery protocols before joint conflict resolution."""
    index = {}
    for port in interfaces:
        for identity in port['identities']:
            if identity['kind'] == 'interface_name':
                index.setdefault((port['device_id'], identity['value']), set()).add(port['id'])
    sources = {o['id']: o for o in observations}
    claims, unbound = [], []
    for reading in normalized['neighbor_observations']:
        matches = index.get((reading['device_ref'], reading['local_interface']), set())
        complete = all(reading.get(k) for k in ('local_interface','remote_claim','remote_port'))
        reason = ('incomplete_identity' if not complete else
                  'unmatched_local_interface' if not matches else
                  'ambiguous_local_interface' if len(matches) != 1 else None)
        claim_id = 'claim-'+hashlib.sha256(json.dumps(
            [reading['observation_id'], reading['source_path']]).encode()).hexdigest()[:24]
        if reason:
            unbound.append(dict(reading, id=claim_id, reason=reason))
            continue
        source = sources[reading['observation_id']]
        proof = {k: source[k] for k in ('device_ref','source','command','parser_version','outcome','sha256')}
        proof.update(observation_id=source['id'], source_path=list(reading['source_path']))
        claims.append(dict(id=claim_id, device_id=reading['device_ref'],
            local_interface_id=next(iter(matches)), protocol=reading['protocol'],
            remote_identities=[dict(kind=reading['remote_identity_kind'],value=reading['remote_claim'])],
            remote_port=dict(kind='port_id',value=reading['remote_port']),
            started_at=reading['started_at'], finished_at=reading['finished_at'],
            expires_at=None, evidence=proof))
    return claims, sorted(unbound, key=lambda r:r['id'])


def detailed_collection_graph(devices, interfaces, observations, identity_observations,
                              *, graph_id, now):
    """Compose one finite detailed collection offline using qualified aliases.

    Preserve separate parser state observations; neither discovery nor counter
    values establish health. Native identity/capture/continuity qualification is
    external to this pure bridge. No read, retry or hosted projection occurs.
    """
    commands = PROFILES['detailed'][0]
    if (not isinstance(observations, list) or len(observations) > 24
            or any(not isinstance(o, dict) or o.get('command') not in commands
                   or not isinstance(o.get('device_ref'), str) for o in observations)):
        raise ValueError('detailed_observations_required')
    if not isinstance(identity_observations, list) or len(identity_observations) > 128-len(observations):
        raise ValueError('identity_observation_limit')
    counts, slots = {}, set()
    for source in observations:
        key = (source['device_ref'], source['command'])
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > (2 if source['command'] == 'show interfaces' else 1):
            raise ValueError('detailed_read_limit')
        if source['command'] == 'show interfaces':
            slot = source.get('sample_index')
            if type(slot) is int and slot in (1, 2):
                if (key[0], slot) in slots:
                    raise ValueError('duplicate_interface_sample')
                slots.add((key[0], slot))
    catalog = identity_observations + observations
    # Validate every proof and cross-protocol ID before using any aliases.
    local_graph(devices, interfaces, [], catalog, graph_id=graph_id, now=now)
    normalized = normalize(sorted(observations, key=lambda o:o['id']), profile='detailed',
                           now=datetime.fromisoformat(now.replace('Z', '+00:00')))
    claims, unbound_neighbors = _neighbor_inputs(interfaces, observations, normalized)
    counters, unbound_interfaces = _counter_inputs(interfaces, observations, normalized)
    graph = local_graph(devices, interfaces, claims, catalog, graph_id=graph_id,
                        now=now, counters=counters)
    index = {}
    for port in interfaces:
        for identity in port['identities']:
            if identity['kind'] == 'interface_name':
                index.setdefault((port['device_id'],identity['value']),set()).add(port['id'])
    states = []
    sources = {o['id']:o for o in observations}
    for reading in normalized['interface_observations']:
        matches = index.get((reading['device_ref'],reading['interface_name']),set())
        state = {k:reading[k] for k in ('observation_id','device_ref','interface_name',
            'command','parser_version','sha256','started_at','finished_at','stale','state')}
        state.update(source=sources[reading['observation_id']]['source'],
            resolved_interface_id=next(iter(matches)) if len(matches)==1 else None,
            binding_reason=None if len(matches)==1 else 'unmatched_interface' if not matches else 'ambiguous_interface')
        states.append(state)
    # Local evidence only; these independent fields do not alter graph health
    # or geometry. Eight bounded interface captures contain at most 2048 rows.
    if len(states) > 2048:
        raise ValueError('interface_state_limit')
    graph['interface_states'] = states
    return dict(classification='private', hosted_eligible=False, graph=graph,
                normalization=normalized, interface_states=states,
                unbound_neighbors=unbound_neighbors, unbound_interfaces=unbound_interfaces)


def resolve_neighbors(devices, interfaces, observations, *, now):
    """Resolve explicit typed identities from frozen local evidence, never labels.

    Pure offline API: the native parser must supply qualified inventory identity
    bindings and discovery expiry. No inventory wiring or address-based inference.
    This intermediate result is not yet the renderer's localGraph envelope.
    """
    def need(ok):
        if not ok:
            raise ValueError('invalid_neighbor_input')

    def text(s):
        return isinstance(s, str) and 0 < len(s) <= 128 and label(s) == s

    def stamp(s):
        need(isinstance(s, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', s))
        return datetime.fromisoformat(s.replace('Z', '+00:00'))

    def proof(p, device_id):
        need(isinstance(p, dict) and all(text(p.get(k)) for k in
             ('observation_id', 'source', 'command', 'parser_version')))
        need(isinstance(p.get('sha256'), str) and re.fullmatch(r'[a-f0-9]{64}', p['sha256']))
        need(isinstance(p.get('source_path'), list) and 0 < len(p['source_path']) <= 16
             and all(text(x) for x in p['source_path']))
        need(p.get('device_ref') == device_id and p.get('outcome') == 'observed')
        return {**{k: p[k] for k in ('observation_id', 'device_ref', 'outcome', 'source', 'command', 'parser_version', 'sha256')},
                'source_path': list(p['source_path'])}

    def identity(i, kinds):
        need(isinstance(i, dict) and i.get('kind') in kinds and text(i.get('value')))
        return i['kind'], i['value']

    device_kinds = ('chassis_id', 'cdp_device_id', 'hostname')
    port_kinds = ('port_id', 'interface_name')
    clock = stamp(now)
    for rows, limit in ((devices, 4), (interfaces, 1024), (observations, 256)):
        need(isinstance(rows, list) and len(rows) <= limit)
        need(all(isinstance(r, dict) and text(r.get('id')) for r in rows))
        need(len({r['id'] for r in rows}) == len(rows))
    device_ids = {d['id'] for d in devices}
    ports = {p['id']: p for p in interfaces}
    device_index, port_index, bindings = {}, {}, {}
    for rows, kinds, index in ((devices, device_kinds, device_index), (interfaces, port_kinds, port_index)):
        for row in rows:
            if rows is interfaces:
                need(row.get('device_id') in device_ids)
            entries = row.get('identities')
            need(isinstance(entries, list) and len(entries) <= 16)
            for entry in entries:
                key = identity(entry, kinds)
                if rows is interfaces:
                    key = (row['device_id'], *key)
                index.setdefault(key, set()).add(row['id'])
                bindings.setdefault((row['id'], key), []).append(proof(entry.get('evidence'), row.get('device_id', row['id'])))

    claims, resolved = [], []
    for o in sorted(observations, key=lambda o: o['id']):
        need(o.get('device_id') in device_ids and o.get('local_interface_id') in ports)
        need(ports[o['local_interface_id']]['device_id'] == o['device_id'])
        need(o.get('protocol') in ('lldp', 'cdp'))
        start, end = stamp(o.get('started_at')), stamp(o.get('finished_at'))
        expiry = stamp(o['expires_at']) if o.get('expires_at') is not None else None
        need(start <= end <= clock and (expiry is None or expiry >= end))
        remote = o.get('remote_identities')
        need(isinstance(remote, list) and 0 < len(remote) <= 16)
        keys = sorted(set(identity(i, device_kinds) for i in remote))
        remote_port = identity(o.get('remote_port'), port_kinds)
        claim = {k: o[k] for k in ('id', 'device_id', 'local_interface_id', 'protocol', 'started_at', 'finished_at')}
        claim.update(remote_identities=[dict(kind=k, value=v) for k, v in keys],
                     remote_port=dict(kind=remote_port[0], value=remote_port[1]),
                     expires_at=o.get('expires_at'), evidence=proof(o.get('evidence'), o['device_id']),
                     identity_evidence=[], resolved_device_id=None, resolved_interface_id=None,
                     certainty='unknown', reason=None, stale=(clock-end).total_seconds() > 300,
                     expired=expiry is not None and clock >= expiry)
        claims.append(claim)
        need(claim['evidence']['command'] == 'show '+o['protocol']+' neighbors detail')
        candidates = [device_index.get(k, set()) for k in keys]
        matches = set.intersection(*candidates)
        if any(not c for c in candidates):
            claim['reason'] = 'unmatched_identity'; continue
        if not matches:
            claim.update(certainty='conflict', reason='conflicting_identity'); continue
        if len(matches) != 1:
            claim['reason'] = 'ambiguous_identity'; continue
        target = next(iter(matches))
        if target == o['device_id']:
            claim.update(certainty='conflict', reason='self_neighbor'); continue
        claim['resolved_device_id'] = target
        for k in keys:
            claim['identity_evidence'].extend(bindings[(target, k)])
        port_key = (target, *remote_port)
        matches = port_index.get(port_key, set())
        if len(matches) != 1:
            claim['reason'] = 'unmatched_port' if not matches else 'ambiguous_port'; continue
        target_port = next(iter(matches))
        claim['resolved_interface_id'] = target_port
        claim['identity_evidence'].extend(bindings[(target_port, port_key)])
        # The local endpoint is an explicit inventory ID, with its own proof.
        for entry in ports[o['local_interface_id']]['identities']:
            claim['identity_evidence'].append(proof(entry['evidence'], o['device_id']))
        if not ports[o['local_interface_id']]['identities']:
            claim['reason'] = 'local_identity_unverified'; continue
        claim['reason'] = ('stale' if claim['stale'] else 'expired' if claim['expired']
                           else 'expiry_unknown' if expiry is None else None)
        claim['certainty'] = 'one_sided' if claim['reason'] is None else 'unknown'
        resolved.append((claim, start, expiry))

    # Multiple claimed physical peers at either port are a visible conflict.
    peers, groups = {}, {}
    for claim, start, expiry in resolved:
        a, b = claim['local_interface_id'], claim['resolved_interface_id']
        peers.setdefault(a, set()).add(b); peers.setdefault(b, set()).add(a)
        groups.setdefault(tuple(sorted((a, b))), []).append((claim, start, expiry))
    links = []
    for endpoints, entries in sorted(groups.items()):
        conflict = any(len(peers[p]) > 1 for p in endpoints)
        fresh = [(c, s, e) for c, s, e in entries if c['reason'] is None]
        reverse = any(a['local_interface_id'] == b['resolved_interface_id']
                      and a['resolved_interface_id'] == b['local_interface_id']
                      and a['evidence']['observation_id'] != b['evidence']['observation_id']
                      and max(sa, sb) < min(ea, eb)
                      for a, sa, ea in fresh for b, sb, eb in fresh)
        certainty = 'conflict' if conflict else 'corroborated' if reverse else 'one_sided' if fresh else 'unknown'
        if conflict:
            for claim, _, _ in entries:
                claim.update(certainty='conflict', reason='competing_peer_claims')
        links.append(dict(id='link-'+hashlib.sha256(json.dumps(endpoints).encode()).hexdigest()[:24],
                          endpoints=list(endpoints), certainty=certainty, status='conflict' if conflict else 'unknown',
                          observation_ids=[c['id'] for c, _, _ in entries]))
    return dict(classification='private', hosted_eligible=False, evaluated_at=now,
                neighbor_observations=claims, links=links)


def counter_rate(first, second, continuity=None, capacity=None):
    """Derive a private rate; inputs are local normalized records, never tool grants.

    Values are decimal strings at this JSON boundary to preserve 64-bit counters.
    Matching incarnation labels alone do not prove continuity. The adapter must
    supply evidence that excludes resets AND wraps across this exact sample pair.
    No collection, polling, identity inference or rollover correction occurs here.
    """
    result = {'classification': 'private', 'hosted_eligible': False,
              'sample_ids': [], 'value': None, 'delta': None, 'units': None,
              'elapsed_seconds': None, 'certainty': 'unknown',
              'reason': 'missing_sample', 'evidence': [], 'sample_intervals': [],
              'utilization_percent': None, 'utilization_reason': 'rate_unknown'}

    def unknown(reason):
        result['reason'] = reason
        return result

    def stamp(value):
        if not isinstance(value, str) or not re.fullmatch(
                r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', value):
            raise ValueError('timestamp')
        return datetime.fromisoformat(value.replace('Z', '+00:00'))

    def identity(value):
        return isinstance(value, str) and 0 < len(value) <= 128 and label(value) == value

    def evidence(value):
        return (isinstance(value, dict)
                and all(identity(value.get(k)) for k in
                        ('observation_id', 'source', 'command', 'parser_version'))
                and isinstance(value.get('sha256'), str)
                and re.fullmatch(r'[a-f0-9]{64}', value['sha256'])
                and isinstance(value.get('source_path'), list)
                and 0 < len(value['source_path']) <= 16
                and all(identity(p) for p in value['source_path']))

    def proof(value):
        return {**{k: value[k] for k in
                   ('observation_id', 'source', 'command', 'parser_version', 'sha256')},
                'source_path': list(value['source_path'])}

    if first is None or second is None:
        return result
    values, times = [], []
    for sample in (first, second):
        if not isinstance(sample, dict):
            return unknown('invalid_sample')
        if not all(identity(sample.get(k)) for k in
                   ('id', 'device_id', 'interface_id', 'incarnation', 'field')):
            return unknown('invalid_identity')
        if sample.get('classification') != 'private' or not evidence(sample.get('evidence')):
            return unknown('missing_provenance')
        if sample.get('outcome') != 'observed':
            return unknown('sample_unavailable')
        if sample.get('units') not in ('bytes', 'packets', 'errors') or sample.get('direction') not in ('in', 'out'):
            return unknown('invalid_counter_kind')
        value, width = sample.get('value'), sample.get('width')
        if (not isinstance(value, str) or not re.fullmatch(r'0|[1-9][0-9]{0,19}', value)
                or (width is not None and (type(width) is not int or width not in (32, 64)))
                or int(value) >= 2 ** (width or 64)):
            return unknown('invalid_counter_value')
        try:
            start, end, sampled = (stamp(sample.get(k)) for k in
                                   ('started_at', 'finished_at', 'sampled_at'))
        except (ValueError, TypeError):
            return unknown('invalid_interval')
        if not start <= sampled <= end:
            return unknown('invalid_interval')
        values.append(int(value)); times.append((start, end, sampled))
        result['sample_ids'].append(sample['id'])
        result['sample_intervals'].append({k: sample[k] for k in
                                           ('started_at', 'finished_at', 'sampled_at')})
        # Copy only the provenance contract; do not propagate arbitrary payloads.
        result['evidence'].append(proof(sample['evidence']))
    if first['id'] == second['id'] or first['evidence']['observation_id'] == second['evidence']['observation_id']:
        return unknown('duplicate_sample')
    for key in ('device_id', 'interface_id', 'incarnation', 'field', 'units', 'direction', 'width'):
        if first.get(key) != second.get(key):
            return unknown('identity_or_counter_changed')
    elapsed = times[1][2] - times[0][2]
    microseconds = (elapsed.days * 86400 + elapsed.seconds) * 1000000 + elapsed.microseconds
    if microseconds <= 0 or times[1][0] < times[0][1]:
        return unknown('invalid_interval')
    if (not isinstance(continuity, dict)
            or continuity.get('sample_ids') != result['sample_ids']
            or continuity.get('verdict') != 'verified_no_reset_or_wrap'
            or not evidence(continuity.get('evidence'))):
        return unknown('continuity_unverified')
    if values[1] < values[0]:
        return unknown('counter_decreased')
    rate = Fraction((values[1] - values[0]) * 1000000, microseconds)
    result.update(value=float(rate), delta=str(values[1] - values[0]),
                  units=first['units'] + '/s', elapsed_seconds=microseconds / 1000000,
                  certainty='derived', reason=None,
                  continuity_evidence=proof(continuity['evidence']),
                  utilization_reason='capacity_unavailable')
    if capacity is None:
        return result
    if (not isinstance(capacity, dict)
            or any(capacity.get(k) != first[k] for k in ('device_id', 'interface_id', 'incarnation', 'direction'))
            or not evidence(capacity.get('evidence'))
            or capacity.get('units') != 'bits/s'
            or not isinstance(capacity.get('value'), str)
            or not re.fullmatch(r'[1-9][0-9]{0,19}', capacity['value'])
            or capacity.get('sample_ids') != result['sample_ids']):
        result['utilization_reason'] = 'capacity_unverified'
    elif first['units'] != 'bytes':
        result['utilization_reason'] = 'counter_not_bytes'
    else:
        percent = rate * 800 / int(capacity['value'])
        result['capacity_evidence'] = proof(capacity['evidence'])
        result['capacity'] = {'value': capacity['value'], 'units': 'bits/s',
                              'direction': capacity['direction']}
        # Impossible physical rates are a conflict, never clamped into credibility.
        if percent > 100:
            result['utilization_reason'] = 'capacity_conflict'
        else:
            result.update(utilization_percent=float(percent), utilization_reason=None)
    return result


def local_graph(devices, interfaces, claims, observations, *, graph_id, now, counters=None):
    """Bridge qualified identity inputs to the private renderer, without collecting.

    Observations are a bounded catalog of actual capture intervals and outcomes.
    Identity/claim proofs must match it exactly. No missing interval/hash is made up.
    Unresolved claims and failed reads are retained outside geometric links.
    """
    resolved = resolve_neighbors(devices, interfaces, claims, now=now)
    def need(ok):
        if not ok:
            raise ValueError('invalid_graph_source')
    need(isinstance(graph_id, str) and 0 < len(graph_id) <= 128 and label(graph_id) == graph_id)
    need(isinstance(observations, list) and len(observations) <= 128)
    catalog, coverage, evidence = {}, [], {}
    device_ids = {d['id'] for d in devices}
    for o in observations:
        need(isinstance(o, dict))
        for key in ('id', 'source', 'command', 'parser_version'):
            need(isinstance(o.get(key), str) and 0 < len(o[key]) <= 128 and label(o[key]) == o[key])
        need(o['id'] not in catalog and o.get('device_ref') in device_ids)
        need(o.get('outcome') in ('observed','empty','raw_only','parse_failed','timeout','unavailable'))
        for key in ('started_at','finished_at'):
            need(isinstance(o.get(key), str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', o[key]))
        start, end, clock = [datetime.fromisoformat(x.replace('Z','+00:00')) for x in (o['started_at'],o['finished_at'],now)]
        need(start <= end <= clock)
        sha = o.get('sha256')
        need((isinstance(sha,str) and re.fullmatch(r'[a-f0-9]{64}',sha)) or (sha is None and o['outcome'] in ('timeout','unavailable')))
        need(o.get('failure_reason') in (None,'evidence_limit'))
        need(type(o.get('capture_outcome_unknown',False)) is bool)
        catalog[o['id']] = o
        coverage.append({k:o.get(k) for k in ('id','device_ref','source','command','parser_version','started_at','finished_at','outcome','sha256')})
        coverage[-1].update(failure_reason=o.get('failure_reason'),capture_outcome_unknown=o.get('capture_outcome_unknown',False))
    def bind(p, interval=None):
        need(isinstance(p,dict) and isinstance(p.get('observation_id'),str))
        need(isinstance(p.get('source_path'),list) and 0<len(p['source_path'])<=16 and all(isinstance(v,str) and 0<len(v)<=128 and label(v)==v for v in p['source_path']))
        o = catalog.get(p['observation_id'])
        need(o is not None and all(o.get(k) == p.get(k) for k in ('device_ref','outcome','source','command','parser_version','sha256')))
        need(o['outcome'] == 'observed')
        if interval:
            need(all(o[k] == interval[k] for k in ('started_at','finished_at')))
        record = {k:o[k] for k in ('source','started_at','finished_at','sha256','outcome','device_ref','command','parser_version')}
        record.update(observation_id=o['id'],source_path=list(p['source_path']))
        eid = 'evidence-'+hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()[:24]
        evidence[eid] = dict(record,id=eid)
        return eid
    def inventory(row, port=False):
        refs = sorted(set(bind(i['evidence']) for i in row['identities']))
        need(bool(refs))
        name=row.get('label');need(isinstance(name,str) and 0<len(name)<=128 and label(name)==name)
        result=dict(id=row['id'],label=name,evidence_ids=refs)
        if port:
            need(row.get('status') in ('up','down','unknown','conflict'))
            # Port state requires its own evidence, never identity/discovery alone.
            state=row.get('state_evidence')
            need(row['status']=='unknown' or isinstance(state,dict))
            need(state is None or isinstance(state,dict))
            if state is not None:
                need(state.get('device_ref')==row['device_id'] and state.get('command') in ('show ip interface brief','show interfaces'))
                result['state_evidence_id']=bind(state)
                result['evidence_ids']=sorted(set(refs+[result['state_evidence_id']]))
            result.update(device_id=row['device_id'],status=row['status'])
        else:
            need(row.get('role') in ('router','switch','unknown'))
            result['role']=row['role']
        return result
    graph=dict(schema=1,classification='private',id=graph_id,
               devices=[inventory(d) for d in sorted(devices,key=lambda r:r['id'])],
               interfaces=[inventory(p,True) for p in sorted(interfaces,key=lambda r:r['id'])],links=[],evidence=[],discovery=[],coverage=[])
    claim_refs={}
    for c in resolved['neighbor_observations']:
        refs=sorted(set([bind(c['evidence'],c)]+[bind(p) for p in c['identity_evidence']]))
        claim_refs[c['id']]=refs
        graph['discovery'].append(dict(id=c['id'],device_id=c['device_id'],local_interface_id=c['local_interface_id'],
            remote_interface_id=c['resolved_interface_id'],remote_identities=c['remote_identities'],remote_port=c['remote_port'],protocol=c['protocol'],certainty=c['certainty'],reason=c['reason'],
            stale=c['stale'],expired=c['expired'],expires_at=c['expires_at'],evidence_ids=refs,discovery_evidence_id=bind(c['evidence'],c)))
    for link in resolved['links']:
        graph['links'].append({**{k:link[k] for k in ('id','endpoints','certainty')},
                              'evidence_ids':sorted(set(e for cid in link['observation_ids'] for e in claim_refs[cid]))})
    # Counter helpers retain decimal deltas; graph binding adds catalog ownership.
    need(counters is None or isinstance(counters,list) and len(counters)<=512)
    graph['counters']=[]; counter_ids=set(); ports={p['id']:p for p in graph['interfaces']}
    for entry in counters or []:
        need(isinstance(entry,dict))
        for key in ('id','interface_id','field'):
            need(isinstance(entry.get(key),str) and 0<len(entry[key])<=128 and label(entry[key])==entry[key])
        need(entry['id'] not in counter_ids and entry['interface_id'] in ports and entry.get('direction') in ('in','out'))
        counter_ids.add(entry['id']); owner=ports[entry['interface_id']]['device_id']
        for sample in (entry.get('first'),entry.get('second')):
            if isinstance(sample,dict):
                need(sample.get('device_id')==owner and sample.get('interface_id')==entry['interface_id'])
                need(sample.get('field')==entry['field'] and sample.get('direction')==entry['direction'])
        result=counter_rate(entry.get('first'),entry.get('second'),entry.get('continuity'),entry.get('capacity'))
        def counter_bind(proof,interval=None,sample=False):
            need(proof.get('command') in (('show interfaces',) if sample else ('show interfaces','show version')))
            return bind(dict(proof,device_ref=owner,outcome='observed'),interval)
        sample_refs=[counter_bind(p,i,True) for p,i in zip(result['evidence'],result['sample_intervals'])]
        row={k:v for k,v in result.items() if k not in ('classification','hosted_eligible','evidence','continuity_evidence','capacity_evidence')}
        row.update(id=entry['id'],interface_id=entry['interface_id'],field=entry['field'],direction=entry['direction'],sample_evidence_ids=sample_refs)
        refs=list(sample_refs)
        # Observed values do not require a sample instant or continuity proof.
        # Keep them separate from counter_rate's stricter paired derivation.
        row['observed_samples']=[]
        for slot in ('first','second'):
            sample=entry.get(slot)
            if not isinstance(sample,dict) or not isinstance(sample.get('evidence'),dict):
                continue
            need(sample.get('classification')=='private')
            need(isinstance(sample.get('id'),str) and 0<len(sample['id'])<=128 and label(sample['id'])==sample['id'])
            need(sample.get('units') in ('bytes','packets','errors'))
            eid=counter_bind(sample['evidence'],sample,True);refs.append(eid)
            sampled=sample.get('sampled_at')
            if sampled is not None:
                need(isinstance(sampled,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z',sampled))
                need(datetime.fromisoformat(sample['started_at'].replace('Z','+00:00')) <= datetime.fromisoformat(sampled.replace('Z','+00:00')) <= datetime.fromisoformat(sample['finished_at'].replace('Z','+00:00')))
            value=sample.get('value')
            valid=(sample.get('outcome')=='observed' and isinstance(value,str)
                   and re.fullmatch(r'0|[1-9][0-9]{0,19}',value) and int(value)<2**64)
            row['observed_samples'].append(dict(slot=slot,id=sample['id'],value=value if valid else None,
                units=sample['units'],outcome='observed' if valid else 'unknown',
                started_at=sample['started_at'],finished_at=sample['finished_at'],sampled_at=sampled,evidence_id=eid))
        for key in ('continuity','capacity'):
            if key+'_evidence' in result:
                row[key+'_evidence_id']=counter_bind(result[key+'_evidence'],sample=key=='capacity');refs.append(row[key+'_evidence_id'])
        row['evidence_ids']=sorted(set(refs));graph['counters'].append(row)
    graph['counters'].sort(key=lambda r:r['id'])
    need(all(len(r['evidence_ids']) <= 24 for rows in ('devices','interfaces','links','discovery') for r in graph[rows]))
    need(len(evidence)<=2048)
    graph['evidence']=[evidence[k] for k in sorted(evidence)]
    graph['coverage']=sorted(coverage,key=lambda c:c['id'])
    return graph
