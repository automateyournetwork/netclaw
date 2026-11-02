#!/usr/bin/env python3
"""Prepare fresh R01 private material locally. No listeners or cloud API calls."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import sys
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'mcp-servers/protocol-mcp'))
from bgp.federation import certs
from bgp.federation.endpoint_registry import validate
from bgp.federation.manager import FederationManager, peer_identity
from bgp.federation.risk import RiskManager


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('x') as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')
    path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cloud-ip', required=True)
    args = parser.parse_args()
    ip = ipaddress.ip_address(args.cloud_ip)
    if ip.version != 4 or not ip.is_global:
        parser.error('Use the observed reserved cloud IPv4 address')
    output = args.output.resolve()
    os.umask(0o077)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    cloud_home = Path('/var/lib/netclaw-r01/claw')
    homes = {'border': output / 'cloud-home', 'member': output / 'member', 'external': output / 'external'}
    destinations = {**homes, 'border': cloud_home}
    ids = {role: str(uuid.uuid4()) for role in homes}
    risk_name = 'r01-20261101'
    # NCFED's lower-AS initiator must be the on-prem outbound caller.
    asns = {'border': 64520, 'member': 64520, 'external': 64519}
    rids = {'border': '198.18.168.1', 'member': '198.18.168.2', 'external': '198.18.168.3'}
    managers, risks = {}, {}
    for role, home in homes.items():
        home.mkdir(mode=0o700)
        write(home / 'netclaw-hud/installation.json', {'schemaVersion': 1, 'installationId': ids[role]})
        write(home / 'openclaw.json', {'agents': {'defaults': {'workspace': str(destinations[role] / 'workspace')}}})
        (home / 'workspace').mkdir(mode=0o700)
        managers[role] = FederationManager(base_dir=str(home / 'n2n'))
        risks[role] = RiskManager(managers[role])
        risks[role].set_role('member' if role == 'member' else 'border',
                            risk_name=risk_name if role != 'external' else 'r01-external',
                            enabled_stacks='both' if role != 'member' else 'in2n',
                            self_member_id=risk_name + '/onprem' if role == 'member' else None)
    anchor, _ = risks['border'].ensure_risk_ca()
    risks['border'].hub_credential()
    token = risks['border'].issue_token(label='R01 on-prem pilot', ttl_seconds=86400)
    tls = {}
    for role in ('border', 'external'):
        name = ('r01-gcp-montreal.lobsternet.automateyournetwork.com' if role == 'border'
                else 'external.r01.example.test')
        ca, ca_key = certs.create_risk_ca('R01 TLS ' + role)
        certificate, key = certs.issue_cert(ca, ca_key, name, san=name)
        tls[role] = {'name': name, 'ca': ca, 'cert': certificate, 'key': key}
        for label, value in [('ca', ca), ('server', certificate), ('server-key', key)]:
            write(homes[role] / ('transport/' + label + '.pem'), value)
        # TLS issuer keys are not needed by the running service; retain only in
        # this private local evidence directory, outside the cloud secret payload.
        write(output / ('issuer-' + role + '.key'), ca_key)
    entries = {}
    for role in ('border', 'external'):
        home = destinations[role]
        entries[role] = dict(id='external', direction='listen', service='en2n',
            profile='en2n-tls13-v1', transport='direct_tcp',
            routing_host=str(ip) if role == 'border' else '127.0.0.1',
            routing_port=42102 if role == 'border' else 42103,
            address_ref='gcp-r01-primary' if role == 'border' else 'local-external-loopback',
            tls_server_name=tls[role]['name'], ca_file=str(home / 'transport/ca.pem'),
            application_identity=peer_identity(asns[role], rids[role]),
            application_trust=certs.key_fingerprint(tls[role]['cert']),
            bind_host='10.168.0.2' if role == 'border' else '127.0.0.1',
            bind_port=42102 if role == 'border' else 42103,
            cert_file=str(home / 'transport/server.pem'), key_file=str(home / 'transport/server-key.pem'))
    internal = dict(entries['border'], id='members', service='in2n', profile='in2n-tls-exporter-v1',
                    routing_port=42101, bind_port=42101, application_identity=risk_name + '/border',
                    application_trust=anchor)
    for role in ('border', 'external'):
        other = 'external' if role == 'border' else 'border'
        remote = {k: v for k, v in entries[other].items() if k not in ('bind_host', 'bind_port', 'cert_file', 'key_file')}
        remote.update(id='peer', direction='dial', ca_file=str(destinations[role] / 'transport/peer-ca.pem'))
        write(homes[role] / 'transport/peer-ca.pem', tls[other]['ca'])
        own_entries = [internal, entries[role], remote] if role == 'border' else [entries[role], remote]
        doc = dict(schemaVersion=2, installationId=ids[role], revision=1, entries=own_entries)
        validate(doc, ids[role]); write(homes[role] / 'transport/registry.json', doc)
        managers[role].local_consent(asns[other], rids[other], 'R01 ' + other)
    member_entry = {k: v for k, v in internal.items() if k not in ('bind_host', 'bind_port', 'cert_file', 'key_file')}
    member_entry.update(direction='dial', ca_file=str(homes['member'] / 'transport/ca.pem'))
    write(homes['member'] / 'transport/ca.pem', tls['border']['ca'])
    doc = dict(schemaVersion=2, installationId=ids['member'], revision=1, entries=[member_entry])
    validate(doc, ids['member']); write(homes['member'] / 'transport/registry.json', doc)
    for role, home in homes.items():
        dest = destinations[role]
        environment = dict(NETCLAW_RUNTIME='openclaw', OPENCLAW_STATE_DIR=str(dest),
            OPENCLAW_CONFIG_PATH=str(dest / 'openclaw.json'), N2N_BASE_DIR=str(dest / 'n2n'),
            N2N_ENDPOINT_REGISTRY=str(dest / 'transport/registry.json'), N2N_ENABLED='true',
            N2N_ROLE='member' if role == 'member' else 'border',
            N2N_RISK_NAME=risk_name if role != 'external' else 'r01-external',
            N2N_ENABLED_STACKS='both', NETCLAW_LOCAL_AS=str(asns[role]),
            NETCLAW_ROUTER_ID=rids[role], NETCLAW_DRY_RUN='true', NETCLAW_MESH_OPEN='false',
            NETCLAW_BGP_PEERS='[]', BGP_LISTEN_HOST='127.0.0.1', BGP_LISTEN_PORT='14179',
            BGP_API_PORT='14180', NETCLAW_BGP_API='http://127.0.0.1:14180',
            N2N_DISPLAY_NAME='R01 cloud Border' if role == 'border' else 'R01 on-prem ' + role,
            N2N_CERT_MODE='enforce', HUD_HOST='127.0.0.1', HUD_UI_PORT='13000', HUD_PORT='13001')
        if role == 'member':
            environment.update(N2N_MEMBER_ID=risk_name + '/onprem', N2N_BORDER_REGISTRY_ID='members',
                               N2N_ENROLLMENT_TOKEN=token['token'])
        write(home / '.env', ''.join(k + '=' + json.dumps(v) + '\n' for k, v in environment.items()))
        managers[role].close()
    for home in homes.values():
        for item in home.rglob('*'):
            item.chmod(0o700 if item.is_dir() else 0o600)
    payload = output / 'cloud-secret.tar.gz'
    with tarfile.open(payload, 'w:gz') as archive:
        for item in sorted(homes['border'].rglob('*')):
            archive.add(item, arcname=str(item.relative_to(homes['border'])), recursive=False)
    if payload.stat().st_size > 65536:
        raise ValueError('Cloud secret payload exceeds Secret Manager limit')
    receipt = dict(installationIds=ids, cloudHome=str(cloud_home), memberHome=str(homes['member']),
        externalHome=str(homes['external']), cloudIp=str(ip), tlsName=tls['border']['name'],
        enrollmentExpires=token['expires_at'], secretBytes=payload.stat().st_size,
        secretSha256=hashlib.sha256(payload.read_bytes()).hexdigest(),
        tlsKeyFingerprint=certs.key_fingerprint(tls['border']['cert']),
        borderIdentity=risk_name + '/border', externalIdentity=entries['border']['application_identity'])
    write(output / 'material-receipt.json', receipt)
    print(json.dumps({'prepared': True, 'cloudSecretBytes': receipt['secretBytes'],
                      'cloudSecretSha256': receipt['secretSha256'], 'servicesStarted': False}))


if __name__ == '__main__':
    main()
