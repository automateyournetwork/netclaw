#!/usr/bin/env python3
"""Coordinator-only recovery inspection driver; never stops or starts a runtime.

The coordinator separately authorizes and serializes actual lab faults. This
helper exports a reviewable sequence, observes exact owned identities and signs
isolation evidence. Controlled state-machine tests are not REAL qualification.
"""
import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'mcp-servers/protocol-mcp'))
sys.path.insert(0, str(REPO / 'scripts/lib'))

from bgp.federation import protected_contract as c
from bgp.federation.ha.config import HAError, check, read_private, verify_manifest
from ha_cluster import HostIsolation, process_observation


def plan():
    return {'schema_version': 1, 'classification': 'PLAN_ONLY', 'requires_serial_coordinator': True,
        'scope': 'fresh-owned-r08-only',
        'steps': [
            {'step': 1, 'action': 'capture', 'requires': 'all three exact voter and Border IDs plus every executor running; private host signer outside runtimes'},
            {'step': 2, 'action': 'export', 'requires': 'linearizable full-prefix export and immutable per-runtime evidence hashes before faults'},
            {'step': 3, 'action': 'isolate', 'requires': 'coordinator stops recorded Border/executor processes; stops and disconnects recorded containers; restart disabled; export evidence retained'},
            {'step': 4, 'action': 'issue', 'requires': 'fresh actual host inspections; no boolean or paused-container substitution'},
            {'step': 5, 'action': 'restore-install', 'requires': 'fresh signed node identities/new generation and unused private etcd namespace; same organization/anchor'},
            {'step': 6, 'action': 'fenced-check', 'requires': 'campaign/new prepare denied; original operation/claim/resource records unchanged'},
            {'step': 7, 'action': 'restore-activate', 'requires': 'one-use receipt within five minutes; status authority only; global execution fence remains'},
            {'step': 8, 'action': 'negative-check', 'requires': 'new-ID protected execution refused; original status remains; actual model/MCP counters unchanged'},
            {'step': 9, 'action': 'export-and-cleanup', 'requires': 'private correlated evidence plus reviewed owned-only cleanup; no active state overwritten'}]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['plan', 'process-identity', 'capture', 'issue'])
    p.add_argument('--root'); p.add_argument('--manifest-file'); p.add_argument('--new-manifest-file')
    p.add_argument('--anchor-certificate-file'); p.add_argument('--anchor-key-id')
    p.add_argument('--host-certificate-file'); p.add_argument('--host-private-key-file')
    p.add_argument('--owner'); p.add_argument('--subjects-file'); p.add_argument('--pid', type=int)
    p.add_argument('--snapshot-file'); p.add_argument('--exports-file')
    args = p.parse_args(argv)
    try:
        if args.command == 'plan':
            result = plan()
        elif args.command == 'process-identity':
            result = process_observation(args.pid)
        else:
            required = ('root', 'manifest_file', 'anchor_certificate_file', 'anchor_key_id',
                        'host_certificate_file', 'host_private_key_file')
            check(all(getattr(args, key) for key in required), 'private_host_inputs_required')
            anchor = read_private(args.anchor_certificate_file).decode()
            old = verify_manifest(c.decode(read_private(args.manifest_file)), anchor, expected_key_id=args.anchor_key_id)
            host = HostIsolation(args.root, args.host_certificate_file, args.host_private_key_file)
            if args.command == 'capture':
                check(args.owner and args.subjects_file, 'owned_inventory_required')
                result = host.capture(old, args.owner, c.decode(read_private(args.subjects_file)))
            else:
                check(args.new_manifest_file and args.snapshot_file and args.exports_file, 'restore_inputs_required')
                new = verify_manifest(c.decode(read_private(args.new_manifest_file)), anchor,
                                      expected_key_id=args.anchor_key_id, minimum_revision=old.revision + 1)
                result = host.issue(old, new, args.snapshot_file, args.exports_file)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (HAError, c.ProtectedError) as exc:
        print(json.dumps({'ok': False, 'error': exc.code}), file=sys.stderr)
        return 1
    except Exception:
        print(json.dumps({'ok': False, 'error': 'private_host_inspection_failure'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
