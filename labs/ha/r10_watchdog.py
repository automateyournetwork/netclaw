"""Finite R10 cleanup watchdog. Only exact run-owned Azure groups and GCP resources may be removed.

GCP scope (manifest key `gcp`: project, gcloud, firewalls): instances and addresses must carry labels netclaw-spec=198 and
run-id=<run>; firewall rules cannot be labelled, so only the exact `nc198-` names listed in the manifest are removed.

The manifest and evidence directory live outside source, mode0700/0600. Run once
per minute through launchd. This is a host-dependent fallback, not an Azure spend cap.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time


def owned_group(value, manifest):
    tags = value.get('tags') or {}
    return (value.get('name') in manifest['azure_groups'] and tags.get('netclaw-spec') == '198'
            and tags.get('run-id') == manifest['run_id'])


def owned_gcp(item, manifest):
    labels = item.get('labels') or {}
    return (str(item.get('name', '')).startswith('nc198-') and labels.get('netclaw-spec') == '198'
            and labels.get('run-id') == manifest['run_id'])


def gcp_cleanup(data, runner=subprocess.run):
    """Delete run-owned GCP instances/addresses (label-verified) and listed firewall rules. Returns evidence rows."""
    g = data['gcp']; evidence = []
    base = [g['gcloud'], 'compute']; proj = ['--project', g['project']]
    for kind, extra in (('instances', ['--zone']), ('addresses', ['--region'])):
        r = runner(base + [kind, 'list'] + proj + ['--filter', 'labels.run-id=' + data['run_id'], '--format', 'json'],
                   capture_output=True, text=True, timeout=120)
        if r.returncode:
            evidence.append({'kind': kind, 'read_exit': r.returncode}); continue
        for item in json.loads(r.stdout or '[]'):
            if not owned_gcp(item, data):
                evidence.append({'kind': kind, 'name': item.get('name'), 'refused': 'ownership_mismatch'}); continue
            where = (item.get('zone') or item.get('region') or '').rsplit('/', 1)[-1]
            r = runner(base + [kind, 'delete', item['name']] + proj + [extra[0], where, '--quiet'],
                       capture_output=True, text=True, timeout=300)
            evidence.append({'kind': kind, 'name': item['name'], 'cleanup_submit_exit': r.returncode})
    for name in g.get('firewalls', []):
        r = runner(base + ['firewall-rules', 'delete', name] + proj + ['--quiet'], capture_output=True, text=True, timeout=120)
        evidence.append({'kind': 'firewall-rules', 'name': name, 'cleanup_submit_exit': r.returncode})
    return evidence


def validate(data):
    if not data.get('run_id'):
        raise SystemExit('invalid owned resource scope')
    groups = data.get('azure_groups', [])
    if any(not x.startswith('rg-nc198-') for x in groups):
        raise SystemExit('invalid owned resource scope')
    g = data.get('gcp')
    if g is not None and (not g.get('project') or not g.get('gcloud')
                          or any(not str(x).startswith('nc198-') for x in g.get('firewalls', []))):
        raise SystemExit('invalid owned resource scope')
    if not groups and g is None:
        raise SystemExit('invalid owned resource scope')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    path = Path(a.manifest).absolute()
    if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise SystemExit('private manifest required')
    data = json.loads(path.read_text())
    validate(data)
    data.setdefault('azure_groups', [])
    due = time.time() >= data['deadline_at']
    if a.check or not due:
        print(json.dumps({'due': due, 'deadline_at': data['deadline_at'], 'groups': data['azure_groups'], 'gcp': bool(data.get('gcp'))}))
        return
    evidence = []
    for name in data['azure_groups']:
        base = [data['az'], '--subscription', data['subscription_id']]
        # Global az flags follow the command group, so construct argv explicitly.
        args = [data['az'], 'group', 'show', '--subscription', data['subscription_id'], '-n', name, '-o', 'json']
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        if r.returncode:
            evidence.append({'group': name, 'read_exit': r.returncode}); continue
        if not owned_group(json.loads(r.stdout), data):
            evidence.append({'group': name, 'refused': 'ownership_mismatch'}); continue
        r = subprocess.run([data['az'], 'group', 'delete', '--subscription', data['subscription_id'],
                            '-n', name, '--yes', '--no-wait'], capture_output=True, text=True, timeout=60)
        evidence.append({'group': name, 'cleanup_submit_exit': r.returncode})
    if data.get('gcp'):
        evidence += gcp_cleanup(data)
    out = path.parent / ('watchdog-%d.json' % time.time())
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump({'observed_at': time.time(), 'actions': evidence}, f)


if __name__ == '__main__':
    main()
