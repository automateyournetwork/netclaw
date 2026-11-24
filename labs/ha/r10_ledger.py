#!/usr/bin/env python3.10
"""Spec 198 spend ledger: $15 pause point, $25 hard ceiling. Stdlib only. The ledger holds estimates, never secrets.

usage: r10_ledger.py [--file F] start <phase> <resource> <usd_per_hour> | stop <phase> <resource> | status | approve-over-pause
Exit 3 when a start is refused (paused or over ceiling).
"""
import argparse, json, math, os, sys, time
from contextlib import contextmanager
import fcntl

CEILING = 25.0
PAUSE = 15.0
DEFAULT = os.path.expanduser('~/.local/share/netclaw/r10-ledger.json')


@contextmanager
def locked(path):
    """Serialize the complete read/check/write, including separate phase CLIs."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), mode=0o700, exist_ok=True)
    fd = os.open(path + '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def load(path):
    if not os.path.exists(path):
        return {'ceiling_usd': CEILING, 'pause_usd': PAUSE, 'approved_over_pause': False, 'entries': []}
    with open(path) as f:
        return json.load(f)


def save(path, data):
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    tmp = path + '.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def entry_cost(e, now):
    if 'fixed_usd' in e:
        return e['fixed_usd']
    end = e['stopped_at'] if e.get('stopped_at') is not None else now
    return e['rate_usd_per_h'] * max(0.0, end - e['started_at']) / 3600.0


def total(data, now=None):
    now = time.time() if now is None else now
    return sum(entry_cost(e, now) for e in data['entries'])


def hourly_burn(data):
    return sum(e['rate_usd_per_h'] for e in data['entries'] if 'fixed_usd' not in e and e.get('stopped_at') is None)


def check_start(data, rate, now=None, hours=1):
    """Reserve the intended duration for all running resources, including fixed allowances."""
    if not math.isfinite(rate) or rate <= 0 or not math.isfinite(hours) or not 0 < hours <= 24:
        return False, 'invalid positive finite rate/duration'
    projected = total(data, now) + (hourly_burn(data) + rate) * hours
    if projected >= min(CEILING, data['ceiling_usd']):
        return False, f'refused: projected ${projected:.2f} reaches the ${data["ceiling_usd"]:.0f} ceiling'
    if projected >= data['pause_usd'] and not data.get('approved_over_pause'):
        return False, f'paused: projected ${projected:.2f} reaches the ${data["pause_usd"]:.0f} pause point; owner approval required'
    return True, 'ok'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', default=DEFAULT)
    ap.add_argument('--now', type=float, default=None, help='test hook')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('start'); s.add_argument('phase'); s.add_argument('resource'); s.add_argument('rate', type=float)
    s.add_argument('--hours', type=float, default=1)
    t = sub.add_parser('stop'); t.add_argument('phase'); t.add_argument('resource')
    sub.add_parser('status'); sub.add_parser('approve-over-pause')
    c = sub.add_parser('charge'); c.add_argument('phase'); c.add_argument('resource'); c.add_argument('usd', type=float)
    a = ap.parse_args(argv)
    with locked(a.file):
        return execute(a)


def execute(a):
    now = time.time() if a.now is None else a.now
    d = load(a.file)
    if a.cmd == 'start':
        if any(e['phase'] == a.phase and e['resource'] == a.resource and e.get('stopped_at') is None for e in d['entries']):
            print('refused: resource already has an open entry; inspect its outcome', file=sys.stderr); return 3
        ok, why = check_start(d, a.rate, now, a.hours)
        if not ok:
            print(why, file=sys.stderr); return 3
        d['entries'].append({'phase': a.phase, 'resource': a.resource, 'rate_usd_per_h': a.rate, 'started_at': now, 'stopped_at': None,
                             'reviewed_duration_hours': a.hours, 'deadline_at': now + a.hours * 3600})
        save(a.file, d); print(f'started {a.resource}')
    elif a.cmd == 'charge':
        if not math.isfinite(a.usd) or a.usd < 0 or total(d, now) + a.usd >= min(CEILING, d['ceiling_usd']):
            print('refused: invalid charge or ceiling reached', file=sys.stderr); return 3
        if any(e['phase'] == a.phase and e['resource'] == a.resource for e in d['entries']):
            print('refused: charge identity already exists', file=sys.stderr); return 3
        d['entries'].append({'phase': a.phase, 'resource': a.resource, 'fixed_usd': a.usd, 'started_at': now, 'stopped_at': now})
        save(a.file, d); print('charge recorded')
    elif a.cmd == 'stop':
        n = 0
        for e in d['entries']:
            if e['phase'] == a.phase and e['resource'] == a.resource and e.get('stopped_at') is None:
                e['stopped_at'] = now; n += 1
        save(a.file, d); print(f'stopped {n}')
    elif a.cmd == 'approve-over-pause':
        d['approved_over_pause'] = True; save(a.file, d); print('approved over pause (ceiling still enforced)')
    else:
        print(json.dumps({'total_est_usd': round(total(d, now), 4), 'burn_usd_per_h': round(hourly_burn(d), 4),
                          'paused': total(d, now) + hourly_burn(d) >= d['pause_usd'] and not d.get('approved_over_pause'),
                          'open_entries': sum(1 for e in d['entries'] if e.get('stopped_at') is None)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
