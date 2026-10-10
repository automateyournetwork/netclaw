#!/usr/bin/env python3
"""Bind selected MCP registrations to installer runtimes, preserving custom entries."""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


catalog = load_helper('installer_catalog', 'verify-catalog-coverage.py')
writer = load_helper('installer_writer', 'write-env.py')


def component_for(server):
    if server in catalog.GROUPED_CONFIG_EXACT:
        return catalog.GROUPED_CONFIG_EXACT[server]
    for prefix, component in catalog.GROUPED_CONFIG_PREFIXES.items():
        if server.startswith(prefix):
            return component
    return catalog.strip_mcp_suffix(server)


def bind_entry(entry, repo, runtime):
    result = copy.deepcopy(entry)
    command = result.get('command')
    if not command:  # Remote transport.
        return result
    if runtime:
        python = Path(runtime)
        if not python.is_file() or not os.access(python, os.X_OK):
            raise ValueError('Recorded Python runtime is not executable')
        if command in ('python', 'python3') or (
            command.startswith('mcp-servers/') and command.endswith('/.venv/bin/python')
        ):
            result['command'] = str(python)
        elif '/' not in command and (python.parent / command).is_file():
            result['command'] = str(python.parent / command)
        # Canonical source-venv templates follow the successful runtime record
        # after recovery. Custom interpreters, uvx and Node retain their command.
    value = result.get('command', '')
    if value in ('python', 'python3') and not runtime:
        result['command'] = sys.executable
    if value.startswith(('mcp-servers/', 'scripts/')):
        result['command'] = str(repo / value)
    if 'args' in result:
        result['args'] = [str(repo / arg) if arg.startswith(('mcp-servers/', 'scripts/')) else arg
                          for arg in result['args']]
    result.setdefault('cwd', str(repo))
    return result


def launch(entry):
    return {key: entry.get(key) for key in ('command', 'args', 'cwd')}


def merge_config(path, generated, template):
    original = path.read_text() if path.exists() else '{}'
    config = json.loads(original)
    state_path = path.with_name(path.name + '.netclaw-managed.json')
    prior = json.loads(state_path.read_text()) if state_path.exists() else {}
    if 'mcpServers' in config:
        servers = config['mcpServers']
    else:
        servers = config.setdefault('mcp', {}).setdefault('servers', {})
    managed = dict(prior)
    conflicts = []
    for name, entry in generated.items():
        existing = servers.get(name)
        if existing is not None:
            normalized = bind_entry(template[name], Path(entry.get('cwd', '.')), None)
            with_cwd = {**template[name], 'cwd': entry.get('cwd')}
            if launch(existing) not in (launch(template[name]), launch(normalized), launch(with_cwd),
                                        launch(prior.get(name, {})), launch(entry)):
                conflicts.append(name)
                continue
            # Keep operator environment, timeouts, approvals and other fields.
            updated = copy.deepcopy(existing)
            for key in ('command', 'args', 'cwd'):
                if key in entry:
                    updated[key] = entry[key]
                else:
                    updated.pop(key, None)
            updated['env'] = {**entry.get('env', {}), **existing.get('env', {})}
            if not updated['env']:
                updated.pop('env')
            if 'transport' in entry:
                updated.setdefault('transport', entry['transport'])
            servers[name] = updated
        else:
            servers[name] = entry
        managed[name] = entry
    if conflicts:
        raise ValueError('Preserved custom launch commands; reconcile these registrations before retrying: '
                         + ', '.join(conflicts))
    data = json.dumps(config, indent=2) + '\n'
    if data != original:
        if path.exists():
            backup = path.with_name(path.name + f'.before-netclaw-{time.time_ns()}')
            writer.write_private(backup, original)
        writer.write_private(path, data)
    writer.write_private(state_path, json.dumps(managed, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--components', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    template = json.loads((repo / 'config/openclaw.json').read_text())['mcpServers']
    selected = set(args.components.split())
    generated = {}
    for name, entry in template.items():
        if name == "hermes-hud-mcp":
            continue  # Private HUD control plane.
        component = component_for(name)
        if component not in selected:
            continue
        record = args.runtime_root / 'records' / component
        runtime = record.read_text().strip() if record.exists() else None
        generated[name] = bind_entry(entry, repo, runtime)
        if 'scripts/component-launch.py' in entry.get('args', []):
            generated[name].setdefault('env', {}).update({
                'NETCLAW_RUNTIME_ROOT': str(args.runtime_root.resolve()),
                'NETCLAW_RUNTIME_ENV': str(args.runtime_root.resolve().parent / '.env'),
            })
    writer.write_private(args.output, json.dumps({'mcpServers': generated}, indent=2) + '\n')
    if args.config:
        merge_config(args.config, generated, template)
    print(f'Prepared {len(generated)} selected MCP registrations.')


if __name__ == '__main__':
    main()
