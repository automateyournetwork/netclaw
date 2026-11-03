#!/usr/bin/env python3
"""Check/apply one exact saved R04 plan, with a durable no-replay claim.

The coordinator records the owner's delegation separately. This program does not
create plans or infer authority from access. Teardown additionally needs a verified
private export manifest; R01 and preexisting budgets must never enter this state.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from review_plan import private, need, validate_state, validate_plan


def digest(path):
    return hashlib.sha256(private(path, maximum=512 * 1024**2)).hexdigest()


def verify(review, export_manifest=None):
    need(review.get('applied') is False and review.get('delegation_required') is False, 'review_not_executable')
    if not review['teardown_plan']:
        now = dt.datetime.now(dt.timezone.utc)
        start = dt.datetime.strptime(review['window_started_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
        expires = dt.datetime.strptime(review['expires_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
        need(start <= now < expires <= start + dt.timedelta(hours=48), 'saved_plan_expired_or_window_invalid')
    source = Path(review['source_root'])
    need(source.is_absolute() and source.resolve() == source, 'source_path_invalid')
    for name, expected in review['source_files'].items():
        need(Path(name).name == name and name.endswith('.tf') and hashlib.sha256((source / name).read_bytes()).hexdigest() == expected, 'source_changed')
    need({p.name for p in source.glob('*.tf')} == set(review['source_files']), 'source_closure_changed')
    tool = Path(review['tofu'])
    need(tool.is_absolute() and tool.resolve() == tool and hashlib.sha256(tool.read_bytes()).hexdigest() == review['tofu_sha256'], 'tofu_changed')
    need(digest(review['saved_plan']) == review['plan_sha256'], 'plan_changed')
    state = Path(review['state_path'])
    if review['state_sha256'] is None:
        need(not state.exists() and not state.is_symlink(), 'fresh_state_required')
    else:
        need(digest(state) == review['state_sha256'], 'state_changed')
        validate_state(private(state), 'netclaw-r04-' + review['run_id'], review['project'])
    if review['teardown_plan']:
        need(export_manifest is not None, 'verified_export_required')
        manifest = json.loads(private(export_manifest))
        need(set(manifest) == {'schemaVersion', 'run_id', 'files'} and manifest['schemaVersion'] == 1
             and manifest['run_id'] == review['run_id'] and isinstance(manifest['files'], dict)
             and 1 <= len(manifest['files']) <= 20000, 'export_manifest_invalid')
        for name, expected in manifest['files'].items(): need(digest(name) == expected, 'export_changed')
    return review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', required=True); parser.add_argument('--export-manifest')
    parser.add_argument('action', choices=('check', 'apply')); args = parser.parse_args()
    review_path = Path(args.review); review = verify(json.loads(private(review_path)), args.export_manifest)
    if args.action == 'check':
        print(json.dumps({'checked': True, 'plan_sha256': review['plan_sha256'], 'applied': False})); return
    os.umask(0o077)
    attempt = review_path.with_suffix('.attempt.json')
    fd = os.open(attempt, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump({'plan_sha256': review['plan_sha256'], 'outcome': 'unknown', 'automatic_replay': False}, stream)
        stream.flush(); os.fsync(stream.fileno())
    fd = os.open(attempt.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
    # No automatic retry, even when the subprocess times out or the reply is lost.
    env = {k: v for k, v in os.environ.items() if not k.startswith('TF_')}
    env.update(TF_DATA_DIR=str(review_path.parent / 'tfdata'), TF_IN_AUTOMATION='1', TF_WORKSPACE='default')
    log = review_path.with_suffix('.apply.log')
    with log.open('xb') as output:
        result = subprocess.run([review['tofu'], '-chdir=' + review['source_root'], 'apply', '-input=false', '-no-color',
                                 '-lock-timeout=30s', review['saved_plan']], env=env, stdout=output, stderr=subprocess.STDOUT, timeout=900)
    receipt = review_path.with_suffix('.result.json')
    receipt.write_text(json.dumps({'plan_sha256': review['plan_sha256'], 'exit_code': result.returncode,
                                  'outcome': 'command_completed' if result.returncode == 0 else 'requires_reconciliation',
                                  'state_sha256': digest(review['state_path']) if Path(review['state_path']).exists() else None}, indent=2))
    print(json.dumps({'command_completed': result.returncode == 0, 'automatic_replay': False}))
    if result.returncode: sys.exit(1)


if __name__ == '__main__':
    main()
