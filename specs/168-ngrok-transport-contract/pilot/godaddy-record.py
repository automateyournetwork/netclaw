#!/usr/bin/env python3
"""Create one absent pilot A record. Read-only unless --apply is explicit.

The operator credential stays local. Existing/conflicting records are never
overwritten. A failed/unknown write outcome must be reconciled through GET.
"""
import argparse
import datetime
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if args.receipt.exists():
        parser.error('Choose a new receipt path; retain prior outcomes')
    wanted = json.loads(args.record.read_text())
    assert set(wanted) == {'zone', 'name', 'type', 'data', 'ttl'}
    assert wanted['type'] == 'A' and wanted['ttl'] == 600
    assert ipaddress.IPv4Address(wanted['data']).is_global
    for key in ('zone', 'name'):
        assert re.fullmatch(r'[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?', wanted[key])
    spec = importlib.util.spec_from_file_location('literal_env', ROOT / 'scripts/write-env.py')
    env_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(env_module)
    env = env_module.values(args.env_file.read_text())
    if env.get('GODADDY_PAT'):
        authorization = 'Bearer ' + env['GODADDY_PAT']
    elif env.get('GODADDY_API_KEY') and env.get('GODADDY_API_SECRET'):
        authorization = 'sso-key ' + env['GODADDY_API_KEY'] + ':' + env['GODADDY_API_SECRET']
    else:
        raise ValueError('GoDaddy credential unavailable')
    receipt = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'wanted': wanted, 'applyRequested': args.apply, 'operations': []}

    def save():
        args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
        args.receipt.chmod(0o600)

    def request(kind, method='GET', body=None):
        url = f"https://api.godaddy.com/v1/domains/{wanted['zone']}/records/{kind}/{wanted['name']}"
        req = urllib.request.Request(url, method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={'Authorization': authorization, 'Content-Type': 'application/json'})
        operation = {'method': method, 'type': kind, 'outcome': 'unknown'}
        receipt['operations'].append(operation)
        save()  # Record potential mutation before sending, including unknown outcomes.
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                operation.update(status=response.status, outcome='responded')
                raw = response.read(65537)
                if len(raw) > 65536:
                    raise ValueError('Oversized DNS response')
                value = json.loads(raw) if raw.strip() else None
                if method == 'GET':
                    operation['records'] = value
                return value
        except urllib.error.HTTPError as error:
            operation.update(status=error.code, outcome='rejected')
            raise RuntimeError('GoDaddy request rejected; inspect sanitized receipt') from None
        finally:
            save()

    baseline = {kind: request(kind) for kind in ('A', 'AAAA', 'CNAME')}
    assert all(isinstance(v, list) for v in baseline.values())
    if baseline['AAAA'] or baseline['CNAME']:
        raise ValueError('Conflicting DNS record; no changes made')
    same = len(baseline['A']) == 1 and baseline['A'][0].get('data') == wanted['data'] and baseline['A'][0].get('ttl') == wanted['ttl']
    if baseline['A'] and not same:
        raise ValueError('Existing A record differs; refusing overwrite')
    if args.apply and not same:
        request('A', 'PUT', [{'data': wanted['data'], 'ttl': wanted['ttl']}])
        after = request('A')
        assert len(after) == 1 and after[0]['data'] == wanted['data'] and after[0]['ttl'] == wanted['ttl']
    receipt['outcome'] = 'verified' if args.apply or same else 'prepared'
    save()
    print(json.dumps({'outcome': receipt['outcome'], 'record': wanted, 'changed': args.apply and not same}))


if __name__ == '__main__':
    main()
