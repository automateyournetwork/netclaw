#!/usr/bin/env python3
"""QUALIFICATION-ONLY launcher: scripts/protected-role.py plus one instrumented scenario.

Used by the REAL runner INSTEAD of ``scripts/protected-role.py`` only when the
coordinator passes an explicit private instrument configuration. It performs the
identical production ``validate`` (plus the REAL-qualification checks in
``real_instrument.check_qualification``), then reproduces the production chain
``federation-control.py run`` -> ``bgp-daemon-v2.py`` inside ONE process: the final
``os.execve`` of that chain is intercepted, verified byte-for-byte against the
expected exact call, and replaced by an in-process ``runpy`` of the same daemon
file so the class-attribute wrappers survive. Production source is imported
unmodified. The daemon path is also passed as a trailing argument so the
production ``stop`` ownership check (ps command contains the daemon path) holds.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
DAEMON = ROOT / 'mcp-servers/protocol-mcp/bgp-daemon-v2.py'
CONTROL = ROOT / 'scripts/federation-control.py'


def instrument_module():
    spec = importlib.util.spec_from_file_location('real_instrument', HERE.with_name('real_instrument.py'))
    module = importlib.util.module_from_spec(spec); sys.modules['real_instrument'] = module
    spec.loader.exec_module(module)
    return module


def guarded_execve(real, instrument, original):
    expected = [sys.executable, '-I', '-B', str(DAEMON)]
    def execve(path, argv, env):
        real.need(path == sys.executable and list(argv) == expected and dict(env) == dict(os.environ), 'unexpected_exec_chain')
        real.need(sys.flags.isolated and sys.flags.dont_write_bytecode, 'isolated_interpreter_required')
        instrument.install(**real.load_production())
        sys.argv = [str(DAEMON)]
        runpy.run_path(str(DAEMON), run_name='__main__')
        raise SystemExit(0)
    return execve


def main(argv=None, *, validator=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--instrument-config', required=True)
    parser.add_argument('action', choices=('validate', 'run', 'stage2'))
    parser.add_argument('daemon_marker', nargs='?')  # trailing daemon path, stage2 only
    args = parser.parse_args(argv)
    real = instrument_module()
    try:
        config, cfg, environment = real.check_qualification(
            args.contract, args.instrument_config, source_root=ROOT, validator=validator,
            environ=os.environ if args.action == 'stage2' else None)
        if args.action == 'validate':
            print(json.dumps({'valid': True, 'scenario': config['scenario'], 'role': cfg['role']})); return 0
        if args.action == 'run':
            os.chdir(cfg['home']); os.umask(0o077)
            python = cfg['python']
            os.execve(python, [python, '-I', '-B', str(HERE), '--contract', args.contract,
                               '--instrument-config', args.instrument_config, 'stage2', str(DAEMON)], environment)
        real.need(args.action == 'stage2' and args.daemon_marker == str(DAEMON), 'daemon_marker_invalid')
        instrument = real.Instrument(config)
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps({'error': 'real_instrument_refused'}), file=sys.stderr)
        return 1
    # Past this point only the production chain runs; its own failures are not relabelled.
    sys.argv = [str(CONTROL), 'run']
    os.execve = guarded_execve(real, instrument, os.execve)
    runpy.run_path(str(CONTROL), run_name='__main__')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
