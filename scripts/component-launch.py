#!/usr/bin/env python3
"""Launch a declared integration in its installed environment (no shell, no installs).

Used by native registrations and mcp-call, so both use the same interpreter,
source path and transport. This passes MCP unchanged; it grants no permissions.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'config/installer-access.json').read_text())['components']


def runtime_root(env):
    home = env.get('OPENCLAW_STATE_DIR') or env.get('OPENCLAW_HOME') or str(Path.home() / '.openclaw')
    if env.get('NETCLAW_RUNTIME') == 'hermes':
        home = env.get('HERMES_HOME', str(Path.home() / '.hermes'))
    return Path(env.get('NETCLAW_RUNTIME_ROOT', str(Path(home) / 'python-runtimes')))


def environment(env):
    result = dict(env)
    path = Path(env.get('NETCLAW_RUNTIME_ENV', str(runtime_root(env).parent / '.env')))
    if path.is_file():
        spec = importlib.util.spec_from_file_location('launch_dotenv', ROOT / 'scripts/write-env.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Literal parsing only; explicit runtime/entry env wins over dotenv.
        for key, value in module.values(path.read_text()).items():
            result.setdefault(key, value)
    return result


def resolve(component, server=None, env=None, repo=ROOT):
    env = environment(os.environ if env is None else env)
    rule = CONTRACT[component]
    server = server or rule['servers'][0]
    if server not in rule['servers']:
        raise ValueError('Server does not belong to the selected component')
    cwd = repo / rule.get('cwd', '.')
    if not cwd.is_dir():
        raise ValueError(f'{component}: source directory missing; rerun install.sh --add {component}')
    if 'variants' in rule:
        parts = list(rule['variants'][server])
    else:
        script = env.get(rule.get('script_env', '')) or (str(repo / rule['script']) if 'script' in rule else None)
        if script and not Path(script).is_file():
            raise ValueError(f'{component}: server script missing; rerun install.sh --add {component}')
        command = rule.get('command')
        if not command:
            if rule.get('bridge'):
                command = sys.executable
                env.setdefault('PYATS_VENV', str(runtime_root(env).parent / 'pyats-venv'))
            else:
                record = runtime_root(env) / 'records' / component
                if not record.is_file():
                    raise ValueError(f'{component}: no installed interpreter record; rerun install.sh --add {component}')
                command = record.read_text().strip()
                if not Path(command).is_absolute() or not os.access(command, os.X_OK):
                    raise ValueError(f'{component}: recorded interpreter unavailable; rerun install.sh --add {component}')
                env['PATH'] = str(Path(command).parent) + os.pathsep + env.get('PATH', os.defpath)
        else:
            command = env.get(rule.get('command_env', '')) or command
        parts = [command]
        # A custom script path is an operator override; never replace it with
        # the default module. Standard source modules need their src on path.
        default_script = str(repo / rule['script']) if 'script' in rule else None
        if 'module' in rule and script == default_script:
            parts += ['-u', '-m', rule['module']]
        elif script:
            parts += (['-u'] if not rule.get('command') else []) + [script]
        parts += rule.get('args', [])
        if rule.get('pythonpath'):
            source = str(repo / rule['pythonpath'])
            env['PYTHONPATH'] = source + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    executable = shutil.which(parts[0], path=env.get('PATH', os.defpath))
    if not executable:
        raise ValueError(f'{component}: launcher unavailable; rerun install.sh --add {component}')
    parts[0] = executable
    return parts, env, str(cwd)


def legacy_component(parts, env, repo=ROOT):
    """Recognize only exact declared script/module/command invocations."""
    for component, rule in CONTRACT.items():
        if 'variants' in rule:
            for server, command in rule['variants'].items():
                if parts == command:
                    return component, server
        elif rule.get('command') == 'gtrace' and parts == ['gtrace', 'mcp']:
            return component, rule['servers'][0]
        elif rule.get('script'):
            paths = {str(repo / rule['script'])}
            if env.get(rule.get('script_env', '')):
                paths.add(env[rule['script_env']])
            tail = parts[1:]
            if tail[:1] == ['-u']:
                tail = tail[1:]
            if parts[0] in ('python', 'python3', 'node', env.get('PYATS_PYTHON')) and len(tail) == 1 and tail[0] in paths:
                return component, rule['servers'][0]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=sorted(CONTRACT))
    parser.add_argument('--server')
    args = parser.parse_args()
    try:
        command, env, cwd = resolve(args.component, args.server)
        os.chdir(cwd)
        os.execvpe(command[0], command, env)
    except (OSError, ValueError) as error:
        # Do not dump env/config, upstream diagnostics or credential values.
        print(str(error) if isinstance(error, ValueError) else 'Component launch failed; check installation paths.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
