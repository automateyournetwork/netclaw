#!/usr/bin/env python3
"""Shared installer target contract; no network calls or package mutations."""
import argparse
import json
from pathlib import Path
import re

POLICY = json.loads((Path(__file__).resolve().parents[1] / 'config/installer-runtime.json').read_text())


def version(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value.strip())
    if not match:
        raise ValueError('Expected a stable major.minor.patch version')
    return tuple(map(int, match.groups()))


def node_supported(value, runtime='openclaw'):
    try:
        actual = version(value)
    except ValueError:
        return False
    return any(actual >= tuple(rule['min']) and (
        'max_exclusive' not in rule or actual < tuple(rule['max_exclusive'])
    ) for rule in POLICY['node_ranges'][runtime])


def npm_args(value):
    actual = version(value)
    args = ['install', '-g', POLICY['openclaw_package']]
    if actual >= (11, 16, 0):
        args.append('--allow-scripts=openclaw')
    return args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', choices=['openclaw', 'hermes'], default='openclaw')
    parser.add_argument('--node')
    parser.add_argument('--npm')
    args = parser.parse_args()
    if args.npm is not None:
        try:
            print('\n'.join(npm_args(args.npm)))
            return 0
        except ValueError as error:
            parser.error(str(error))
    print('Node.js ' + POLICY['node_descriptions'][args.runtime] +
          ' required; select a supported version with your Node version manager (for example nvm install 26).')
    return 0 if args.node is None or node_supported(args.node, args.runtime) else 1


if __name__ == '__main__':
    raise SystemExit(main())
