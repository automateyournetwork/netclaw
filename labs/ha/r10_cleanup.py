#!/usr/bin/env python3
"""Retire a fresh R10 run after its private evidence export.

Inventory errors fail closed. Names alone never select VMs, disks or addresses.
No ledger entry is closed here: the caller must first obtain a verified-empty
receipt. This also leaves the finite watchdog available when cleanup fails.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from r10_watchdog import owned_group, owned_gcp, validate


def command(args):
    r = subprocess.run(args, capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise RuntimeError('cloud_command_failed:' + ' '.join(args[:3]))
    return json.loads(r.stdout) if r.stdout.strip() else None


def private_json(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(value, f, indent=2)


def exported(path):
    root = path.parent.resolve()
    doc = json.loads(path.read_text())
    if not doc.get('files'):
        raise ValueError('nonempty_export_required')
    for relative, digest in doc['files'].items():
        p = root / relative
        if p.is_symlink() or not p.resolve().is_relative_to(root) or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError('export_hash_mismatch')


def inventory(m):
    out = {'azure_groups': [], 'azure_resources': [], 'gcp': {}}
    if m['azure_groups']:
        suffix = ['--subscription', m['subscription_id'], '-o', 'json']
        groups = command([m['az'], 'group', 'list', *suffix])
        for group in groups:
            if group['name'] in m['azure_groups']:
                if not owned_group(group, m):
                    raise ValueError('azure_group_ownership_mismatch')
                out['azure_groups'].append(group)
        out['azure_resources'] = command([m['az'], 'resource', 'list', '--tag', 'run-id=' + m['run_id'], *suffix])
    if m.get('gcp'):
        g = m['gcp']
        for kind in ('instances', 'disks', 'addresses', 'firewall-rules'):
            rows = command([g['gcloud'], 'compute', kind, 'list', '--project', g['project'], '--format=json'])
            selected = []
            for row in rows:
                if kind == 'firewall-rules':
                    if row['name'] in g['firewalls']:
                        # Creation binds this exact name to the fresh run in its description.
                        if row.get('description') != 'netclaw-spec=198 run-id=' + m['run_id']:
                            raise ValueError('firewall_ownership_mismatch')
                        selected.append(row)
                elif (row.get('labels') or {}).get('run-id') == m['run_id']:
                    if not owned_gcp(row, m):
                        raise ValueError('gcp_ownership_mismatch')
                    selected.append(row)
            out['gcp'][kind] = selected
        # Boot disks created by gcloud are not automatically labelled. Bind their
        # immutable selfLink to the already-owned VM before it is removed.
        all_disks = command([g['gcloud'], 'compute', 'disks', 'list', '--project', g['project'], '--format=json'])
        links = {d['source'] for vm in out['gcp']['instances'] for d in vm.get('disks', []) if d.get('boot') and d.get('autoDelete')}
        selected_links = {d['selfLink'] for d in out['gcp']['disks']}
        out['gcp']['disks'] += [d for d in all_disks if d['selfLink'] in links - selected_links]
    return out


def retire(m, before):
    for group in before['azure_groups']:
        command([m['az'], 'group', 'delete', '--subscription', m['subscription_id'], '-n', group['name'], '--yes', '--no-wait'])
    if not m.get('gcp'):
        return
    g = m['gcp']
    for kind in ('instances', 'disks', 'addresses', 'firewall-rules'):
        # Re-read after instance deletion (auto-delete boot disks may be gone).
        current = command([g['gcloud'], 'compute', kind, 'list', '--project', g['project'], '--format=json'])
        for old in before['gcp'][kind]:
            now = next((x for x in current if x.get('id') == old.get('id') and x['name'] == old['name']), None)
            if now is None:
                continue
            if kind != 'firewall-rules' and kind != 'disks' and not owned_gcp(now, m):
                raise ValueError('ownership_changed')
            if kind == 'disks' and now.get('users'):
                raise ValueError('disk_still_attached')
            args = [g['gcloud'], 'compute', kind, 'delete', now['name'], '--project', g['project'], '--quiet']
            if now.get('zone'):
                args += ['--zone', now['zone'].rsplit('/', 1)[-1]]
            elif now.get('region'):
                args += ['--region', now['region'].rsplit('/', 1)[-1]]
            elif kind == 'addresses':
                args += ['--global']
            command(args)


def empty(now, before):
    return not (now['azure_groups'] or now['azure_resources'] or any(now['gcp'].values()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest', type=Path)
    ap.add_argument('--export', type=Path, required=True)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.manifest.is_symlink() or a.manifest.stat().st_mode & 0o077 or a.manifest.stat().st_uid != os.getuid():
        raise ValueError('private_manifest_required')
    m = json.loads(a.manifest.read_text())
    validate(m)
    exported(a.export)
    before = inventory(m)
    receipt = a.manifest.parent / ('cleanup-%d.json' % time.time_ns())
    private_json(receipt, {'run_id': m['run_id'], 'before': before, 'export': str(a.export), 'apply': a.apply})
    if not a.apply:
        print(json.dumps({'plan': str(receipt)})); return
    retire(m, before)
    # This process may run asynchronously; the operator continues receiving updates.
    for _ in range(60):
        now = inventory(m)
        # Explicitly check originally bound boot-disk IDs, even when unlabelled.
        residual = []
        if m.get('gcp'):
            g = m['gcp']
            disks = command([g['gcloud'], 'compute', 'disks', 'list', '--project', g['project'], '--format=json'])
            ids = {d['id'] for d in before['gcp']['disks']}
            residual = [d for d in disks if d['id'] in ids]
        if empty(now, before) and not residual:
            verified = receipt.with_name(receipt.stem + '-verified.json')
            private_json(verified, {'run_id': m['run_id'], 'verified_empty': True, 'observed_at': time.time(), 'inventory': now, 'boot_disks_remaining': residual})
            print(json.dumps({'verified_empty': True, 'receipt': str(verified)})); return
        time.sleep(10)
    raise RuntimeError('cleanup_not_verified_empty')


if __name__ == '__main__':
    main()
