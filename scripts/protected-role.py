#!/usr/bin/env python3
"""Validate or launch an already provisioned protected role; never creates a home."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'lib'))
from protected_role import validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', required=True)
    parser.add_argument('action', choices=('validate', 'run'))
    args = parser.parse_args()
    try:
        cfg, environment = validate(args.contract)
        if args.action == 'validate':
            print(json.dumps({'valid': True, 'installation_id': cfg['installation_id'],
                              'role': cfg['role'], 'control_only': cfg['control_only']}))
            return 0
        # Final validation precedes replacing this process. No caller environment,
        # arbitrary executable, shell, bootstrap or fallback home is inherited.
        os.chdir(cfg['home']); os.umask(0o077)
        executable = cfg['python']
        os.execve(executable, [executable, '-I', '-B', str(Path(cfg['source_root']) / 'scripts/federation-control.py'), 'run'], environment)
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps({'error': 'protected_role_refused'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
