#!/usr/bin/env python3
"""Prepare a private saved plan only. No apply/import/destroy execution exists here."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess


FIELDS = {'project_id', 'run_id', 'image_self_link', 'window_started_at', 'expires_at', 'member_cidrs', 'network_activated'}


def need(value, code):
    if not value:
        raise ValueError(code)


def private(path):
    path = Path(path)
    need(path.is_absolute() and path.resolve() == path, 'canonical_private_path_required')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077 and info.st_size <= 16 * 1024**2, 'private_file_required')
        return stream.read(16 * 1024**2 + 1)


def validate_state(raw, name, project):
    state = json.loads(raw)
    resources = state.get('resources')
    need(state.get('version') == 4 and isinstance(resources, list), 'state_schema_invalid')
    allowed = {'google_compute_network', 'google_compute_subnetwork', 'google_service_account',
               'google_secret_manager_secret', 'google_secret_manager_secret_iam_member',
               'google_compute_address', 'google_compute_firewall', 'google_compute_instance'}
    for resource in resources:
        need(resource.get('mode') == 'managed' and resource.get('type') in allowed, 'foreign_state_resource')
        for instance in resource.get('instances', []):
            attrs = instance['attributes']
            need(attrs.get('project') == project, 'foreign_project_state')
            values = [str(attrs.get(key, '')) for key in ('name', 'id', 'secret_id', 'account_id')]
            need(any(re.search(r'(?:^|/)' + re.escape(name) + r'(?:$|[-/])', value) for value in values), 'foreign_run_state')


def validate_plan(plan):
    allowed = {'google_compute_network', 'google_compute_subnetwork', 'google_service_account',
               'google_secret_manager_secret', 'google_secret_manager_secret_iam_member',
               'google_compute_address', 'google_compute_firewall', 'google_compute_instance'}
    changes = plan.get('resource_changes', [])
    need(all(item.get('type') in allowed and item.get('mode') == 'managed' for item in changes), 'foreign_plan_resource')
    expected = {'google_compute_network.r03', 'google_compute_subnetwork.r03',
                'google_service_account.border', 'google_secret_manager_secret.operator',
                'google_secret_manager_secret_iam_member.operator', 'google_compute_address.r03',
                'google_compute_firewall.iap', 'google_compute_firewall.https[0]',
                'google_compute_firewall.in2n[0]', 'google_compute_firewall.private_egress',
                'google_compute_firewall.web_egress[0]', 'google_compute_firewall.deny_egress',
                'google_compute_instance.border'}
    need(all(item.get('address') in expected and not item['change'].get('importing') for item in changes), 'foreign_plan_address')
    need(not plan.get('errored'), 'plan_errored')
    return [{'address': item['address'], 'actions': item['change']['actions']} for item in changes]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tofu', required=True)
    parser.add_argument('--variables', required=True)
    parser.add_argument('--private-root', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--teardown-plan', action='store_true')
    args = parser.parse_args()
    need(re.fullmatch('[a-z][a-z0-9-]{0,40}', args.name), 'plan_name_invalid')
    variables = json.loads(private(args.variables))
    need(isinstance(variables, dict) and set(variables) == FIELDS, 'variable_fields_invalid')
    need(re.fullmatch(r'\d{8}-[a-z0-9]{4,8}', variables['run_id']), 'run_invalid')
    directory = Path(args.private_root)
    need(directory.is_absolute() and directory.resolve() == directory, 'private_directory_required')
    info = directory.stat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077, 'private_directory_required')
    state = directory / 'r03.tfstate'
    if state.exists() or state.is_symlink():
        validate_state(private(state), 'netclaw-r03-' + variables['run_id'], variables['project_id'])
    else:
        need(not args.teardown_plan and not variables['network_activated'], 'fresh_foundation_required')
    tool = Path(args.tofu)
    need(tool.is_absolute() and tool.resolve() == tool and tool.is_file(), 'explicit_tofu_required')
    output = directory / (args.name + '.tfplan')
    need(not output.exists() and not output.is_symlink(), 'plan_already_exists')
    data = directory / 'tfdata'
    data.mkdir(mode=0o700, exist_ok=True)
    need(data.resolve() == data and data.stat().st_uid == os.getuid() and not data.stat().st_mode & 0o077, 'private_tfdata_required')
    env = {key: value for key, value in os.environ.items() if not key.startswith('TF_')}
    env.update(TF_DATA_DIR=str(data), TF_IN_AUTOMATION='1', TF_WORKSPACE='default')
    os.umask(0o077)
    source = Path(__file__).resolve().parent
    base = [str(tool), '-chdir=' + str(source)]
    def invoke(arguments, output_file):
        with output_file.open('xb') as stream:
            result = subprocess.run(base + arguments, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=300)
        need(result.returncode == 0, 'tofu_command_failed_see_private_log')
    invoke(['init', '-input=false', '-no-color', '-reconfigure', '-backend-config=path=' + str(state)], directory / (args.name + '-init.log'))
    command = ['plan', '-input=false', '-no-color', '-lock-timeout=30s', '-var-file=' + str(Path(args.variables)), '-out=' + str(output)]
    if args.teardown_plan:
        command.append('-destroy')
    invoke(command, directory / (args.name + '-plan.log'))
    json_path = directory / (args.name + '-plan.json')
    invoke(['show', '-json', str(output)], json_path)
    plan = json.loads(private(json_path))
    receipt = {'schemaVersion': 1, 'project': variables['project_id'], 'run_id': variables['run_id'],
               'plan_sha256': hashlib.sha256(private(output)).hexdigest(), 'teardown_plan': args.teardown_plan,
               'source_files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.tf')},
               'tofu_sha256': hashlib.sha256(tool.read_bytes()).hexdigest(), 'changes': validate_plan(plan),
               'applied': False, 'delegation_required': True, 'cost_gate_resolved': False}
    with (directory / (args.name + '-review.json')).open('x') as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
    print(json.dumps({'saved_plan': str(output), 'sha256': receipt['plan_sha256'], 'applied': False}))


if __name__ == '__main__':
    main()
