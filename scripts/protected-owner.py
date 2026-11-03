#!/usr/bin/env python3
"""Trusted local operator authority for the opt-in R02 protected profile."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mcp-servers/protocol-mcp'))
from bgp.federation.protected_owner import OwnerAuthority, private_file
from bgp.federation.protected_contract import ProtectedError, decode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', '--runtime-home', dest='home')
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('--display-name', required=True)
    commands.add_parser('ticket')
    commands.add_parser('revoke')
    args = parser.parse_args()
    try:
        if args.home:
            home = Path(args.home).expanduser().absolute()
            installation = decode(private_file(home / 'netclaw-hud/installation.json'))['installationId']
        else:
            from bgp.federation.runtime import selected
            runtime = selected()
            home, installation = runtime.home, runtime.installation
        if not installation:
            raise ProtectedError('installation_uninitialized')
        owner = OwnerAuthority(home / 'netclaw-federation', installation)
        if args.command == 'init':
            result = {'principal': owner.init(args.display_name), 'installation_id': installation}
        elif args.command == 'ticket':
            result = {'ticket': owner.ticket(), 'expires_in_seconds': 600}
        else:
            result = owner.revoke()
        print(json.dumps(result))
        return 0
    except (ProtectedError, OSError, KeyError) as exc:
        print(json.dumps({'error': getattr(exc, 'code', 'owner_unavailable')}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
