#!/usr/bin/env python3
"""Read-only declared host checks; no package installs or network-device calls."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / 'config/installer-preflight.json'


def load_policy():
    policy = json.loads(POLICY_PATH.read_text())
    catalog = set(re.findall(r'^\s*"([a-z0-9-]+)\|', (ROOT / 'scripts/lib/catalog.sh').read_text(), re.M))
    if policy.get('schema_version') != 1 or not policy['components'].keys() <= catalog:
        raise ValueError('Preflight policy has an invalid schema or unknown catalog ids')
    for rule in [policy['defaults'], *policy['components'].values()]:
        for key in ('python_min', 'python_max_exclusive', 'go_min', 'linux_glibc_min'):
            if key in rule and (len(rule[key]) != 2 or any(type(n) is not int or n < 0 for n in rule[key])):
                raise ValueError('Invalid version bound in preflight policy')
    return policy, catalog


def normalize_arch(arch):
    return {'aarch64': 'arm64', 'amd64': 'x86_64'}.get(arch, arch)


def rule_for(policy, component):
    return {**policy['defaults'], **policy['components'].get(component, {})}


def platform_reason(rule, system, arch):
    if system not in rule['os']:
        return rule.get('reason', 'supported operating systems: ' + ', '.join(rule['os']))
    if 'platforms' in rule and [system, normalize_arch(arch)] not in rule['platforms']:
        return 'native SDK supports ' + ', '.join('/'.join(p) for p in rule['platforms'])
    return ''


def python_range(rule):
    result = '>=' + '.'.join(map(str, rule['python_min']))
    if 'python_max_exclusive' in rule:
        result += ',<' + '.'.join(map(str, rule['python_max_exclusive']))
    return result


class Host:
    def __init__(self):
        self.env = os.environ.copy()
        self.cache = {}

    def command(self, name):
        return shutil.which(name)

    def output(self, args):
        key = tuple(args)
        if key not in self.cache:
            # Even version/env probes must not trigger Go toolchain downloads.
            env = {**self.env, 'GOTOOLCHAIN': 'local'}
            try:
                result = subprocess.run(args, capture_output=True, text=True, timeout=5, env=env,
                                        stdin=subprocess.DEVNULL)
                self.cache[key] = result.stdout.strip() if result.returncode == 0 else None
            except (OSError, subprocess.TimeoutExpired):
                self.cache[key] = None
        return self.cache[key]

    def python(self, executable):
        output = self.output([executable, '-c', 'import sys,platform,json,importlib.util; '
            'print(json.dumps({"version":list(sys.version_info[:2]),"os":platform.system(),'
            '"arch":platform.machine(),"libc":list(platform.libc_ver()),'
            '"isolated":sys.prefix != sys.base_prefix,"venv":importlib.util.find_spec("venv") is not None,'
            '"ensurepip":importlib.util.find_spec("ensurepip") is not None}))'])
        try:
            return json.loads(output) if output else None
        except (ValueError, TypeError):
            return None


def launch_commands():
    spec = importlib.util.spec_from_file_location('preflight_config', ROOT / 'scripts/install-mcp-config.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    commands = {}
    config = json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']
    for name, entry in config.items():
        command = entry.get('command')
        # These launchers are external prerequisites, not artifacts we build.
        if command in ('uvx', 'docker', 'npx'):
            commands.setdefault(helper.component_for(name), set()).add(command)
    return commands


def vendor_source_ready(rule, env):
    target = urlparse(rule['vendor_index'])
    for key in ('PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL'):
        for value in shlex.split(env.get(key, '')):
            url = urlparse(value)
            if url.hostname == target.hostname and url.path.rstrip('/') == target.path.rstrip('/'):
                return True
    for value in shlex.split(env.get('PIP_FIND_LINKS', '')):
        path = Path(value)
        if path.is_dir() and any(path.glob(rule['vendor_wheel'])):
            return True
    return False


def evaluate(policy, selected, system, arch, executable, host, launchers=None, explicit_venv=''):
    core = []
    for command in policy['core_commands']:
        if not host.command(command):
            core.append(command + ' missing from PATH')
    node = host.output(['node', '--version']) if host.command('node') else None
    node_match = re.match(r'^v?(\d+)\.', node or '')
    if node is not None and (not node_match or int(node_match[1]) < 18):
        core.append('Node.js >=18 required; select a supported Node.js on PATH')
    elif host.command('node') and node is None:
        core.append('Could not read Node.js version')
    installer_python = host.python(host.command('python3')) if host.command('python3') else None
    if not installer_python or tuple(installer_python['version']) < (3, 10):
        core.append('Installer python3 on PATH requires Python 3.10+; select Python 3.12')
    actual_python = str(Path(explicit_venv) / 'bin/python') if explicit_venv else executable
    python = host.python(actual_python) if actual_python else None
    if not python:
        core.append('Cannot run selected component Python; set NETCLAW_PY to Python 3.12')
    elif not explicit_venv and not (python['venv'] and python['ensurepip']) and not any(
        host.command(c) for c in ('virtualenv', 'uv')
    ):
        core.append('Component environments need venv/ensurepip, virtualenv or uv')
    elif explicit_venv:
        if not python['isolated']:
            core.append('Explicit NETCLAW_VENV must be an isolated virtualenv; refusing system Python')
        if host.output([actual_python, '-m', 'pip', '--version']) is None:
            core.append('Explicit NETCLAW_VENV has no usable pip')
    if system not in policy['defaults']['os']:
        core.append('Unsupported operating system: ' + system + '; use macOS or Linux')
    results = []
    for component in selected:
        rule = rule_for(policy, component)
        errors, warnings = [], []
        reason = platform_reason(rule, system, arch)
        if reason:
            errors.append('Unsupported on this host: ' + reason)
        if python:
            version = tuple(python['version'])
            if version < tuple(rule['python_min']) or (
                'python_max_exclusive' in rule and version >= tuple(rule['python_max_exclusive'])
            ):
                errors.append('Requires Python ' + python_range(rule) + '; selected ' +
                              '.'.join(map(str, version)) + '. Select Python 3.12 via NETCLAW_PY')
            if 'platforms' in rule:
                reason = platform_reason(rule, python['os'], python['arch'])
                if reason:
                    errors.append('Selected Python architecture/platform: ' + reason)
            if 'linux_glibc_min' in rule and python['os'] == 'Linux':
                libc, value = python.get('libc', ['', ''])
                match = re.match(r'^(\d+)\.(\d+)', value)
                if libc != 'glibc' or not match or tuple(map(int, match.groups())) < tuple(rule['linux_glibc_min']):
                    errors.append('Native SDK Linux wheels require glibc >=2.34 (musl/Alpine unsupported)')
        commands = set(rule.get('commands', [])) | (launchers or {}).get(component, set())
        for command in sorted(commands):
            if not host.command(command):
                errors.append(command + ' missing; ' + policy['command_remedies'].get(command, 'put it on PATH'))
        for command in rule.get('optional_commands', []):
            if not host.command(command):
                warnings.append(command + ' missing; ' + policy['command_remedies'][command])
        if 'docker' in commands and host.command('docker') and host.output(['docker', 'info', '--format', '{{.ServerVersion}}']) is None:
            errors.append('Docker daemon unavailable; start Docker and check your Docker context')
        if 'go_min' in rule:
            go = host.output(['go', 'version']) if host.command('go') else None
            match = re.search(r'\bgo(\d+)\.(\d+)', go or '')
            if not match or tuple(map(int, match.groups())) < tuple(rule['go_min']):
                errors.append('Go 1.25+ required on PATH (macOS: brew install go)')
            if rule.get('cgo') and host.command('go'):
                if host.output(['go', 'env', 'CGO_ENABLED']) != '1':
                    errors.append('CGO must be enabled for Forward (CGO_ENABLED=1)')
                compiler = host.output(['go', 'env', 'CC'])
                if not compiler or not host.command(shlex.split(compiler)[0]):
                    errors.append('A C compiler is required for Forward SQLite/CGO')
                if system == 'Darwin' and host.output(['xcode-select', '-p']) is None:
                    errors.append('Install Apple Command Line Tools for Forward CGO (xcode-select --install)')
        if 'vendor_index' in rule and not vendor_source_ready(rule, host.env):
            errors.append('SDK is hosted at ' + rule['vendor_index'] +
                          '; configure PIP_EXTRA_INDEX_URL for Cisco or PIP_FIND_LINKS with verified SDK wheels')
        results.append({'component': component, 'errors': errors, 'warnings': warnings})
    return {'core_errors': core, 'components': results, 'python': actual_python,
            'ok': not core and not any(r['errors'] for r in results)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--os', default='')
    parser.add_argument('--arch', default='')
    parser.add_argument('--python', default=os.environ.get('NETCLAW_PY', sys.executable))
    parser.add_argument('--components', default='')
    parser.add_argument('--platform-only', action='store_true')
    parser.add_argument('--validate-policy', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        policy, catalog = load_policy()
        selected = list(dict.fromkeys(args.components.split()))
        unknown = set(selected) - catalog
        if unknown:
            raise ValueError('Unknown component(s): ' + ', '.join(sorted(unknown)))
        if args.validate_policy:
            print('Preflight policy: PASS (' + str(len(catalog)) + ' catalog entries)')
            return 0
        if args.platform_only:
            for component in sorted(catalog):
                reason = platform_reason(rule_for(policy, component), args.os, args.arch)
                if reason:
                    print(component + '|' + reason)
            return 0
        report = evaluate(policy, selected, args.os, args.arch, args.python, Host(), launch_commands(),
                          os.environ.get('NETCLAW_VENV', ''))
        if args.json:
            print(json.dumps(report))
        else:
            print('Component preflight — declared host prerequisites (Python: ' + report['python'] + ')')
            for message in report['core_errors']:
                print('[BLOCKED] core: ' + message)
            for row in report['components']:
                if not row['errors']:
                    print('[READY] ' + row['component'] + ': host prerequisites checked')
                for message in row['errors']:
                    print('[BLOCKED] ' + row['component'] + ': ' + message)
                for message in row['warnings']:
                    print('[WARN] ' + row['component'] + ': ' + message)
            print('Package resolution, endpoint credentials and service connectivity are not verified by preflight.')
        return 0 if report['ok'] else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Preflight error: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
