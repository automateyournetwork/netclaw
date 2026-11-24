#!/usr/bin/env python3
"""Remove only DNS names and expected A targets from this fresh generation."""
import argparse
import importlib.util
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('generation', type=Path)
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location('dns', Path(__file__).resolve().parents[2] / 'scripts/ha-dns-godaddy.py')
    dns = importlib.util.module_from_spec(spec); spec.loader.exec_module(dns)
    client = dns.Client(dns.auth_header(dns.load_env()))
    summary = json.loads((a.generation / 'summary.json').read_text())
    for node in summary['nodes']:
        label = node['code'] + '-' + node['id6']
        assert dns.LABEL_RE.fullmatch(label) and node['dns'] == label + '.' + dns.ZONE
        assert node['installation_id'].startswith(node['id6'])
        for kind, name in [('A', label), ('TXT', '_acme-challenge.' + label)]:
            path = '/v1/domains/%s/records/%s/%s' % (dns.ZONE, kind, name)
            status, body = client._req('GET', path)
            if status == 404 or status == 200 and not body:
                continue
            assert status == 200 and isinstance(body, list), 'dns_inventory_failed'
            if kind == 'A':
                assert all(row['data'] == node['public'] for row in body), 'dns_target_changed'
            status, _ = client._req('DELETE', path)
            assert status in (204, 404), 'dns_retirement_failed'
            status, body = client._req('GET', path)
            assert status == 404 or status == 200 and not body, 'dns_absence_not_verified'
    print(json.dumps({'generation': summary['generation'], 'dns_verified_empty': True}))


if __name__ == '__main__': main()
