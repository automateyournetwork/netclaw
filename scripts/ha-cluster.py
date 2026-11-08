#!/usr/bin/env python3
"""Private maintainer NCFED HA control. No deployment/public setup entry point."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'mcp-servers/protocol-mcp'))
sys.path.insert(0, str(REPO / 'scripts/lib'))

from bgp.federation import protected_contract as c
from bgp.federation.ha.config import HAError, check, read_private, verify_manifest, install_marker
from bgp.federation.ha.authority import Authority
from bgp.federation.ha.lifecycle import Lifecycle, VoterChanges, EtcdMembership
from bgp.federation.ha.recovery import export_snapshot, verify_isolation, install_restored, activate_restored
from bgp.federation.ha.store import EtcdStore
from ha_cluster import write_new


def store_for(value, manifest):
    c.exact(value, 'endpoints ca_file certificate_file private_key_file username password_file')
    for name in ('ca_file', 'certificate_file', 'private_key_file', 'password_file'):
        check(Path(value[name]).is_absolute(), 'unsafe_private_file')
        read_private(value[name])
    return EtcdStore(value['endpoints'], prefix=f'/netclaw/ha/{manifest.cluster_id}/{manifest.generation}/',
        ca=value['ca_file'], certificate=value['certificate_file'], private_key=value['private_key_file'],
        username=value['username'], password=read_private(value['password_file'], 256).decode().strip())


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['setup', 'status', 'export', 'drain', 'retire', 'resume',
        'voter-prepare', 'voter-apply', 'voter-reconcile', 'restore-install', 'restore-activate'])
    p.add_argument('--config-file', required=True)
    p.add_argument('--config-sha256', required=True)
    p.add_argument('--role', choices=['border', 'member'], default='border')
    p.add_argument('--state-dir')
    p.add_argument('--node-id')
    p.add_argument('--acquire-authority', action='store_true', help='Explicit maintenance campaign; a busy authority is refused')
    p.add_argument('--out')
    p.add_argument('--admin-config-file', help='Separate private operator etcd administrator config; never a member credential')
    p.add_argument('--admin-config-sha256')
    p.add_argument('--action', choices=['add_learner', 'remove', 'promote'])
    p.add_argument('--target')
    p.add_argument('--change-id')
    p.add_argument('--old-manifest-file')
    p.add_argument('--snapshot-file')
    p.add_argument('--receipt-file')
    p.add_argument('--host-certificate-file')
    p.add_argument('--host-key-id')
    return p


def execute(args):
    # Root-owned production loader is shared with the actual federation service.
    # It validates private absolute paths, exact schema and the config hash.
    from bgp.federation.ha.factory import load_configuration
    config = load_configuration({'config_file': args.config_file, 'config_sha256': args.config_sha256}, role=args.role)
    anchor = read_private(config['anchor_certificate_file']).decode()
    manifest = verify_manifest(c.decode(read_private(config['manifest_file'])), anchor,
                               expected_key_id=config['anchor_key_id'])
    if args.command == 'setup':
        check(args.state_dir is not None and Path(args.state_dir).is_absolute(), 'state_directory_required')
        install_marker(args.state_dir, manifest)
        return {'schema_version': 1, **manifest.audience, 'ha_required': True}
    check(args.role == 'border', 'border_operator_required', 403)
    store = store_for(config['etcd'], manifest)
    authority, admin = Authority(store, manifest, config['node_id']), None
    try:
        if args.command.startswith('restore-'):
            required = ('old_manifest_file', 'snapshot_file', 'receipt_file', 'host_certificate_file', 'host_key_id')
            check(all(getattr(args, name) for name in required), 'restore_inputs_required')
            old = verify_manifest(c.decode(read_private(args.old_manifest_file)), anchor,
                                  expected_key_id=config['anchor_key_id'])
            snapshot = c.decode(read_private(args.snapshot_file, 4 * 1024 * 1024), 4 * 1024 * 1024)
            receipt = verify_isolation(c.decode(read_private(args.receipt_file)),
                read_private(args.host_certificate_file).decode(), expected_key_id=args.host_key_id,
                old_manifest=old, new_manifest=manifest, snapshot=snapshot)
            action = install_restored if args.command == 'restore-install' else activate_restored
            return action(store, snapshot, old, manifest, receipt)
        authority.bootstrap()
        if args.command == 'status':
            return Lifecycle(authority).status()
        if args.command == 'export':
            check(args.out is not None and Path(args.out).is_absolute(), 'export_path_required')
            snapshot = export_snapshot(store, manifest)
            write_new(args.out, c.encode(snapshot))
            return {'schema_version': 1, **manifest.audience, 'revision': snapshot['revision'],
                    'snapshot_sha256': c.sha256(snapshot), 'records': len(snapshot['records'])}
        check(args.acquire_authority, 'maintenance_authority_required', 403)
        check(authority.campaign(), 'authority_busy', 409)
        if args.command in ('drain', 'retire', 'resume'):
            check(args.node_id is not None, 'node_id_required')
            return getattr(Lifecycle(authority), args.command)(args.node_id)
        check(args.admin_config_file and args.admin_config_sha256, 'private_admin_config_required')
        raw = read_private(args.admin_config_file)
        check(hashlib.sha256(raw).hexdigest() == args.admin_config_sha256, 'ha_configuration_changed', 409)
        admin = store_for(c.decode(raw), manifest)
        changes = VoterChanges(authority, EtcdMembership(admin))
        if args.command == 'voter-prepare':
            check(args.action and args.target, 'voter_change_inputs_required')
            return changes.prepare(args.action, args.target)
        check(args.change_id is not None, 'change_id_required')
        return (changes.apply if args.command == 'voter-apply' else changes.reconcile)(args.change_id)
    finally:
        if authority.lease_id:
            try:
                store.revoke_lease(authority.lease_id)
            except HAError:
                # Never hide a committed result by retrying or recampaigning.
                pass
        if admin:
            admin.close()
        store.close()


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        print(json.dumps(execute(args), sort_keys=True))
        return 0
    except (HAError, c.ProtectedError) as exc:
        print(json.dumps({'ok': False, 'error': exc.code}), file=sys.stderr)
        return 1
    except Exception:
        # Private paths/credentials/subprocess output never become an accidental
        # traceback in a client or terminal transcript.
        print(json.dumps({'ok': False, 'error': 'private_operator_failure'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
