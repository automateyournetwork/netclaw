#!/usr/bin/env python3
"""One-use R06 retention controller; immutable private operations, never replan.

The deployment coordinator seals the exact private host/DNS/access operations.
Check is read-only. Execute first quiesces and exports all three organizations,
then applies the reviewed saved teardown and verifies actual owned residues.
An interrupted claim is intentionally not retried by launchd.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from review_plan import need, private
from run_plan import verify


def timestamp(value):
    return dt.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)


def write(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def validate(config):
    fields = {'schemaVersion', 'scope', 'run_id', 'quiesce_at', 'cleanup_at', 'expires_at',
              'python', 'ops', 'review', 'authorization', 'export_manifest', 'files'}
    need(set(config) == fields and config['schemaVersion'] == 1 and config['scope'] == 'r06', 'retirement_scope_invalid')
    need(re.fullmatch(r'\d{8}-[a-z0-9]{4,6}', config['run_id']), 'retirement_run_invalid')
    quiesce, cleanup, expiry = [timestamp(config[k]) for k in ('quiesce_at', 'cleanup_at', 'expires_at')]
    need(expiry - dt.timedelta(minutes=15) <= quiesce < cleanup <= expiry
         and dt.timedelta(minutes=4) <= cleanup-quiesce <= dt.timedelta(minutes=10), 'retirement_window_invalid')
    need(isinstance(config['files'], dict) and 4 <= len(config['files']) <= 100, 'retirement_closure_invalid')
    for name, expected in config['files'].items():
        need(hashlib.sha256(private(name, maximum=64*1024**2)).hexdigest() == expected, 'retirement_input_changed')
    for key in ('ops', 'review', 'authorization'):
        need(config[key] in config['files'], 'retirement_input_unsealed')
    python = Path(config['python'])
    need(python.is_absolute() and python.is_file(), 'retirement_python_invalid')
    export = Path(config['export_manifest'])
    need(export.is_absolute() and export.resolve() == export, 'retirement_export_path_invalid')
    review = json.loads(private(config['review']))
    need(review['teardown_plan'] and review['run_id'] == config['run_id']
         and review['expires_at'] == config['expires_at'], 'retirement_plan_scope_invalid')
    authorization = json.loads(private(config['authorization']))
    need(authorization['scope'] == 'r06' and authorization['plan_sha256'] == review['plan_sha256'], 'retirement_authorization_invalid')
    return review


def invoke(config, action, output, timeout):
    with output.open('xb') as stream:
        result = subprocess.run([config['python'], '-B', config['ops'], action],
                                stdin=subprocess.DEVNULL, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=timeout)
    need(result.returncode == 0, 'retirement_' + action + '_failed_see_private_receipt')


def execute(config, directory, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    review = validate(config)
    start, cleanup = timestamp(config['quiesce_at']), timestamp(config['cleanup_at'])
    need(start <= now < cleanup-dt.timedelta(minutes=3), 'outside_retirement_start_window')
    # Claim precedes every stop; no automatic replay after unknown outcome.
    write(directory/'workflow-claim.json', {'at': now.isoformat(), 'run_id': config['run_id'],
          'plan_sha256': review['plan_sha256'], 'outcome': 'unknown', 'automatic_replay': False})
    try:
        invoke(config, 'inspect', directory/'preflight.log', 90)
        invoke(config, 'quiesce-export', directory/'export.log', 240)
        validate(config)
        verify(review, config['export_manifest'])
        while dt.datetime.now(dt.timezone.utc) < cleanup:
            time.sleep(max(0, min(1, (cleanup-dt.datetime.now(dt.timezone.utc)).total_seconds())))
        invoke(config, 'apply-plan', directory/'apply.log', 930)
        invoke(config, 'retire-extras', directory/'extras.log', 150)
        invoke(config, 'verify-retired', directory/'residues.log', 120)
        write(directory/'settled.json', {'passed': True, 'at': dt.datetime.now(dt.timezone.utc).isoformat(),
                                        'automatic_replay': False, 'owned_billable_residues': 0})
    except BaseException as exc:
        write(directory/'failure.json', {'exception_type': type(exc).__name__, 'message': str(exc),
              'automatic_replay': False, 'fallback': 'Independent GCE STOP remains; inspect actual disk/IP and other residues.'})
        raise


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('action', choices=('check', 'execute'))
    args = parser.parse_args()
    path = Path(args.config)
    config = json.loads(private(path))
    review = validate(config)
    if args.action == 'check':
        # An already verified current export proves the saved plan is executable;
        # the scheduled operation requires a NEW quiescent export before apply.
        verify(review, config['export_manifest'])
        print(json.dumps({'checked': True, 'executed': False, 'plan_sha256': review['plan_sha256'],
                          'quiesce_at': config['quiesce_at'], 'cleanup_at': config['cleanup_at']}))
    else:
        execute(config, path.parent)


if __name__ == '__main__':
    main()
