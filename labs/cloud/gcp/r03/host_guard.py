#!/usr/bin/env python3
"""One-use host traffic allowance; Linux/root only. Never resets a spent quota.

This is an engineering boundary, not a GCP monetary cap. No command is run at
import. A configuration-free closed baseline precedes configuration/state reads.
Missing kernel/tools require the separately verified network-manager boot gate.
The VM is dedicated: this owns inet/netclaw_r03 and root qdisc handle 172: only.
"""
import argparse
from contextlib import contextmanager
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


class Refused(ValueError):
    pass


def need(test, code):
    if not test:
        raise Refused(code)


def pairs(rows):
    value = {}
    for key, item in rows:
        need(key not in value, 'duplicate_field')
        value[key] = item
    return value


def timestamp(value):
    need(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value), 'expiry_invalid')
    return dt.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)


def validate(config):
    need(isinstance(config, dict) and set(config) == {'schemaVersion', 'run_id', 'interface', 'quota_bytes', 'rate_bits', 'expires_at'}, 'guard_fields_invalid')
    need(type(config['schemaVersion']) is int and config['schemaVersion'] == 1, 'guard_schema_invalid')
    need(isinstance(config['run_id'], str) and re.fullmatch(r'\d{8}-[a-z0-9]{4,8}', config['run_id']), 'run_invalid')
    need(isinstance(config['interface'], str) and re.fullmatch(r'[a-z][a-z0-9]{1,14}', config['interface']) and config['interface'] != 'lo', 'interface_invalid')
    need(type(config['quota_bytes']) is int and 1 <= config['quota_bytes'] <= 10 * 1024**3, 'quota_invalid')
    need(type(config['rate_bits']) is int and 1 <= config['rate_bits'] <= 1000000, 'rate_invalid')
    timestamp(config['expires_at'])
    return config


def private(path, *, maximum=65536):
    path = Path(path)
    need(path.is_absolute() and path.resolve() == path, 'private_path_invalid')
    root_ancestors(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077 and info.st_size <= maximum, 'private_file_invalid')
        return stream.read(maximum + 1)


def root_ancestors(directory):
    """A service UID must not be able to rename a root-owned guard input."""
    directory = Path(directory)
    for parent in (directory, *directory.parents):
        info = parent.stat()
        need(parent.resolve() == parent and stat.S_ISDIR(info.st_mode) and info.st_uid == 0
             and not info.st_mode & 0o022, 'root_controlled_ancestors_required')


def create_private(path, value):
    """Exclusive durable claim: no overwrite, including after a failed attempt."""
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def run(command, *, input=None, check=True):
    result = subprocess.run(command, input=input, capture_output=True, timeout=10, check=False,
                            env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C'})
    need(len(result.stdout) + len(result.stderr) <= 1024 * 1024, 'guard_output_overflow')
    if check:
        need(result.returncode == 0, 'guard_command_failed')
    return result


@contextmanager
def serial_lock(path):
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as lock:
        info = os.fstat(lock.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077, 'private_lock_required')
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def rules(config, opened, exists, *, bootstrap=False):
    prefix = 'delete table inet netclaw_r03\n' if exists else ''
    quota = f'quota egress {{ over {config["quota_bytes"]} bytes; }}\n' if opened else ''
    effect = 'quota name egress drop' if opened else 'drop'
    dhcp = 'ip daddr { 169.254.169.254, 255.255.255.255 } udp sport 68 udp dport 67 accept\n' if bootstrap else ''
    return (prefix + 'table inet netclaw_r03 {\n' + quota +
            'chain output { type filter hook output priority -300; policy accept;\n' +
            f'oifname "lo" accept\n{dhcp}{effect}\n' + '}\n}\n').encode()


def replace_rules(config, opened, command=run, *, bootstrap=False):
    exists = command(['nft', 'list', 'table', 'inet', 'netclaw_r03'], check=False).returncode == 0
    command(['nft', '-f', '-'], input=rules(config, opened, exists, bootstrap=bootstrap))


def activate(config, state_dir, *, command=run, now=None):
    replace_rules({}, False, command)
    validate(config)
    supplied_now = now
    now = now or dt.datetime.now(dt.timezone.utc)
    need(now < timestamp(config['expires_at']) <= now + dt.timedelta(hours=48), 'expiry_outside_window')
    claim = Path(state_dir) / 'allocation.json'
    need(not claim.exists() and not claim.is_symlink(), 'allowance_already_spent')
    links = json.loads(command(['ip', '-j', 'link', 'show']).stdout)
    # Linux may instantiate dormant fallback tunnel devices. They have no UP
    # flag and cannot be enabled by the unprivileged application services.
    need(all(isinstance(row.get('flags'), list) for row in links)
         and {row['ifname'] for row in links if 'UP' in row['flags']} == {'lo', config['interface']}, 'single_active_interface_required')
    qdiscs = json.loads(command(['tc', '-j', 'qdisc', 'show', 'dev', config['interface']]).stdout)
    need(all(row.get('kind') in {'noqueue', 'mq', 'fq_codel'} for row in qdiscs), 'existing_qdisc_refused')
    create_private(claim, {'schemaVersion': 1, 'configuration': config, 'claimed_at': now.isoformat()})
    command(['tc', 'qdisc', 'replace', 'dev', config['interface'], 'root', 'handle', '172:', 'tbf',
             'rate', str(config['rate_bits']) + 'bit', 'burst', '16384', 'latency', '400ms'])
    # If installation fails, the earlier closed ruleset remains. A failed claim
    # cannot be reclaimed by retry, re-entry, process restart or machine reboot.
    try:
        need((supplied_now or dt.datetime.now(dt.timezone.utc)) < timestamp(config['expires_at']), 'expiry_reached_during_setup')
        replace_rules(config, True, command)
        create_private(Path(state_dir) / 'activated.json', {'schemaVersion': 1, 'run_id': config['run_id'], 'expires_at': config['expires_at']})
    except Exception:
        replace_rules(config, False, command)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--state-dir')
    parser.add_argument('action', choices=['baseline', 'activate', 'close', 'inspect'])
    args = parser.parse_args()
    need(sys.platform == 'linux' and os.getuid() == 0, 'linux_root_required')
    root_ancestors(Path('/run/netclaw-r03-guard'))
    # The lock is independent of mutable configuration and allocation paths.
    # Expiry/close waits for an in-flight activation, then wins permanently.
    with serial_lock('/run/netclaw-r03-guard/lock'):
        perform(args)


def perform(args):
    if args.action != 'inspect':
        replace_rules({}, False, bootstrap=args.action == 'baseline')
    if args.action in ('baseline', 'close'):
        return
    need(args.config and args.state_dir, 'configuration_paths_required')
    config = validate(json.loads(private(args.config), object_pairs_hook=pairs))
    directory = Path(args.state_dir)
    need(directory.is_absolute() and directory.resolve() == directory, 'state_path_invalid')
    root_ancestors(directory.parent)
    directory.mkdir(mode=0o700, parents=False, exist_ok=True)
    info = directory.stat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o077, 'state_owner_invalid')
    if args.action == 'activate':
        activate(config, directory)
    else:
        for command in (['nft', '-j', 'list', 'table', 'inet', 'netclaw_r03'],
                        ['tc', '-j', '-s', 'qdisc', 'show', 'dev', config['interface']]):
            print(run(command).stdout.decode())


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never emit credential-bearing command stderr or arbitrary configuration.
        print('R03 host guard refused; inspect owned private evidence.', file=sys.stderr)
        sys.exit(1)
