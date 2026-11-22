#!/usr/bin/env python3
"""Spec 198 live operation driver against a Border HUD owner API (open-lab). Stdlib only; no secrets printed.

  r10_ops.py catalog --gen GEN [--codes nne1,ew1,ase1]
  r10_ops.py op --gen GEN --code nne1 --members a1,b2 --out FILE [--warm-netbox] [--timeout 300]
        runs ONE prepare -> approve -> poll operation through that Border HUD with the first member suffix that
        completes. A failed attempt fences its member (design), so each suffix is tried at most once.
  r10_ops.py sweep --gen GEN --members a,b,c,d --out-dir DIR [--codes nne1,ew1,ase1] [--warm-netbox]
        one operation through every listed Border, rotating members; exits non-zero unless all complete.
GEN is a group generation directory holding summary.json (nodes, cluster id and generation) as written by r10_prepare.py.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

TERMINAL = ('completed', 'refused', 'failed', 'denied', 'revoked', 'unknown')


def load(gen):
    return json.loads((Path(gen) / 'summary.json').read_text())


def call(summary, code, route, method='GET', body=None, timeout=170):
    node = [n for n in summary['nodes'] if n['code'] == code][0]
    headers = {'Accept': 'application/json', 'X-NetClaw-Installation': node['installation_id'],
               'X-NetClaw-Cluster-ID': summary['cluster_id'], 'X-NetClaw-Cluster-Generation': summary['generation']}
    data = None
    if body is not None or method != 'GET':
        headers['Content-Type'] = 'application/json'; headers['Origin'] = 'https://' + node['dns']
        data = json.dumps(body if body is not None else {}).encode()
    request = urllib.request.Request('https://' + node['dns'] + route, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.load(exc)
        except Exception:
            return exc.code, {}


def retry_call(*args, tries=4, **kwargs):
    """Transport errors (bad Wi-Fi) are retried for READS only; callers never retry a write through this."""
    for attempt in range(tries):
        try:
            return call(*args, **kwargs)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(5 * (attempt + 1))
    raise SystemExit('border unreachable: ' + args[1])


def warm_netbox():
    """demo.netbox.dev stalls on the first request after idle; keep it warm for the length of the run."""
    here = Path(__file__).resolve().parents[2]
    def get(name):
        return subprocess.run(['python3', str(here / 'scripts/write-env.py'), '--get', str(Path.home() / '.openclaw/.env'), name],
                              capture_output=True, text=True).stdout.strip()
    url, token = get('NETBOX_URL'), get('NETBOX_TOKEN')
    if not url or not token:
        return None
    script = ('while true; do curl -s -m 20 -o /dev/null -H "Authorization: Bearer $T" "$U/api/dcim/devices/27/?fields=id"; sleep 3; done')
    proc = subprocess.Popen(['bash', '-c', script], env=dict(os.environ, U=url, T=token), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(20)
    return proc


def catalog(summary, code):
    status, cat = retry_call(summary, code, '/api/hud/operations/catalog')
    return status, cat


def run_op(summary, code, suffix, out, timeout=300):
    status, cat = catalog(summary, code)
    rows = [m for m in cat.get('members', []) if m['member']['member_id'].endswith(suffix)]
    if not rows:
        return None
    row = rows[0]; tool = row['tools'][0]; model = row['model_profiles'][0]
    body = {'client_nonce': str(uuid.uuid4()), 'catalog_revision': cat['revision'], 'member_id': row['member']['member_id'],
            'model_profile_id': model['profile_id'], 'tool': tool['tool'], 'arguments': tool['arguments']}
    _, op = call(summary, code, '/api/hud/operations', 'POST', body)
    if 'operation_id' not in op:
        return {'state': 'prepare_failed', 'detail': op}
    _, decision = call(summary, code, '/api/hud/operations/%s/decision' % op['operation_id'], 'POST',
                       {'revision': op['revision'], 'review_digest': op['review_digest'], 'decision': 'approve'})
    deadline, state, current = time.time() + timeout, None, op
    while time.time() < deadline:
        _, current = retry_call(summary, code, '/api/hud/operations/' + op['operation_id'])
        state = current.get('state')
        if state in ('member_admitted', 'dispatch_claimed'):
            call(summary, code, '/api/hud/operations/%s/reconcile' % op['operation_id'], 'POST')
        if state in TERMINAL:
            break
        time.sleep(3)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(current, f, indent=1)
    return current


def verdict(code, suffix, current):
    result = (current or {}).get('result') or {}
    evidence = result.get('evidence') or {}
    epoch = ((current or {}).get('authority') or {}).get('epoch')
    return '%s via %s: %s durable_ack=%s outcome=%s error=%s epoch=%s' % (
        code, suffix, (current or {}).get('state'), result.get('durable_ack'), evidence.get('outcome'), evidence.get('error_code'), epoch)


def op_until_complete(summary, code, members, out, timeout):
    for suffix in members:
        current = run_op(summary, code, suffix, out, timeout)
        print(verdict(code, suffix, current), flush=True)
        if current and current.get('state') == 'completed':
            return suffix
    return None


def pick(summary, code, remote, used, prefer=('subnet_calculator', 'netbox_get_object_by_id')):
    """Unused member suffixes visible at `code`, remote-tagged or local, preferred flavor first."""
    status, cat = catalog(summary, code)
    rows = [m for m in cat.get('members', []) if ('remote' in m) == remote and m['member']['member_id'][-6:] not in used]
    rows.sort(key=lambda m: prefer.index(m['tools'][0]['tool']) if m['tools'][0]['tool'] in prefer else 99)
    return [m['member']['member_id'][-6:] for m in rows]


def matrix(summaries, outdir, codes, scope, timeout):
    """One LOCAL and one CROSS-GROUP operation through every Border of every group. A failed attempt fences its member,
    so each member is tried at most once; the table records every attempt."""
    used, table = set(), []
    for label, summary in summaries:
        for code in codes:
            for remote in ([False, True] if scope == 'both' else [scope == 'cross']):
                kind = 'cross' if remote else 'local'
                outcome = None
                for suffix in pick(summary, code, remote, used)[:6]:
                    used.add(suffix)
                    current = run_op(summary, code, suffix, str(Path(outdir) / ('%s-%s-%s-%s.json' % (label, code, kind, suffix))), timeout)
                    print(label, kind, verdict(code, suffix, current), flush=True)
                    if current and current.get('state') == 'completed':
                        outcome = suffix; break
                table.append({'group': label, 'ingress': code, 'kind': kind, 'member': outcome, 'ok': outcome is not None})
    fd = os.open(str(Path(outdir) / 'matrix.json'), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(table, f, indent=1)
    bad = [t for t in table if not t['ok']]
    print('matrix: %d/%d completed%s' % (len(table) - len(bad), len(table), '' if not bad else '; FAILED ' + ', '.join('%s/%s/%s' % (t['group'], t['ingress'], t['kind']) for t in bad)))
    return 1 if bad else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('verb', choices=('catalog', 'op', 'sweep', 'matrix'))
    parser.add_argument('--gen', required=True); parser.add_argument('--codes', default='nne1,ew1,ase1')
    parser.add_argument('--code'); parser.add_argument('--members', default=''); parser.add_argument('--out'); parser.add_argument('--out-dir')
    parser.add_argument('--gen-peer', help='matrix: the OTHER group generation dir'); parser.add_argument('--scope', default='both', choices=('local', 'cross', 'both'))
    parser.add_argument('--timeout', type=int, default=300); parser.add_argument('--warm-netbox', action='store_true')
    args = parser.parse_args(argv)
    summary = load(args.gen)
    if args.verb == 'catalog':
        for code in args.codes.split(','):
            status, cat = catalog(summary, code)
            print(code, status, sorted(m['member']['member_id'][-6:] for m in cat.get('members', [])))
        return 0
    members = [m for m in args.members.split(',') if m]
    proc = warm_netbox() if args.warm_netbox else None
    try:
        if args.verb == 'matrix':
            outdir = Path(args.out_dir); outdir.mkdir(parents=True, exist_ok=True); os.chmod(outdir, 0o700)
            return matrix([('local-group', summary), ('peer-group', load(args.gen_peer))], outdir, args.codes.split(','), args.scope, args.timeout)
        if args.verb == 'op':
            return 0 if op_until_complete(summary, args.code, members, args.out, args.timeout) else 1
        outdir = Path(args.out_dir); outdir.mkdir(parents=True, exist_ok=True); os.chmod(outdir, 0o700)
        remaining, failed = list(members), []
        for code in args.codes.split(','):
            used = op_until_complete(summary, code, remaining, str(outdir / ('op-' + code + '.json')), args.timeout)
            if used is None:
                failed.append(code)
            else:
                remaining = remaining[remaining.index(used) + 1:]
        print('sweep:', 'ALL COMPLETE' if not failed else 'FAILED ' + ','.join(failed))
        return 1 if failed else 0
    finally:
        if proc:
            proc.terminate()


if __name__ == '__main__':
    sys.exit(main())
