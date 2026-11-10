#!/usr/bin/env python3
"""R09A (spec 183) DefenseClaw node sidecar tooling: config renderer, sidecar spec and audit-export plan.

The node guard configuration is the previously qualified R04A Anthropic Sonnet 4.6 file, returned BYTE FOR BYTE (its
sha256 is pinned; any change refuses). That file already carries the required posture: `mode: action`,
`hook_fail_mode: closed`, `scanner_mode: local`, `detection_strategy: regex_only`, connector `openclaw`, the loopback
provider fence as `base_url`, and no inline key. No key or token value is ever written here.

  python -m labs.ha.r09a_defenseclaw render --out DIR
  python -m labs.ha.r09a_defenseclaw spec --node nne1
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

HOME = Path(os.path.expanduser('~'))
QUALIFIED_GUARD_CONFIG = HOME / '.local/share/netclaw/roadmap-r04a-20261103/cloud-plan/member-inputs/guard-config.yaml'
QUALIFIED_GUARD_CONFIG_SHA256 = '1fdc7ab50a660051a1f5283eec65ff3d947f05b6518602157d8e455a8f7fa26b'  # same pin as r09_member
DEFENSECLAW_VERSION = '1.0.4'
GUARD_PORT = 4000        # guardrail proxy (loopback in the node sandbox)
API_PORT = 4001          # gateway management API probed by the qualified health probe
SANDBOX_HOME = '/sandbox'
AUDIT_DIR = SANDBOX_HOME + '/defenseclaw'
REQUIRED_LINES = ('  mode: action\n', '  hook_fail_mode: closed\n', '  scanner_mode: local\n',
                  '  detection_strategy: regex_only\n', '  connector: openclaw\n', 'data_dir: /guard\n',
                  '  llm_role: judge_and_agent\n', '  base_url: http://127.0.0.1:18888\n', '  fleet_mode: disabled\n',
                  '  token_env: DEFENSECLAW_GATEWAY_TOKEN\n', '  api_port: %d\n' % API_PORT, '  port: %d\n' % GUARD_PORT)
SECRET_LIKE = re.compile(rb'(sk-ant-[A-Za-z0-9_-]{8,}|nbt_[A-Za-z0-9._-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|api_key:\s*\S)')
NODE_CODE = re.compile(r'^[a-z][a-z0-9]{1,15}$')


class DefenseClawRefused(ValueError):
    """Fixed codes only."""


def need(condition, code):
    if not condition:
        raise DefenseClawRefused(code)


def render_config(path=None):
    """The qualified guard configuration, byte for byte, after verifying the pin and the required posture."""
    path = Path(path or QUALIFIED_GUARD_CONFIG)
    need(path.is_file(), 'qualified_guard_config_missing')
    raw = path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == QUALIFIED_GUARD_CONFIG_SHA256, 'qualified_guard_config_changed')
    need(SECRET_LIKE.search(raw) is None, 'guard_config_inline_secret_refused')
    text = raw.decode('utf-8', 'strict')
    for line in REQUIRED_LINES:
        need(line in text, 'guard_config_posture_missing')
    return raw


def sidecar_spec(node):
    """Sidecar placement and paths for one node (no secrets). Consumed by the deploy driver and posture."""
    need(isinstance(node, str) and NODE_CODE.match(node), 'invalid_node')
    return {
        'schema_version': 1, 'node': node, 'defenseclaw_version': DEFENSECLAW_VERSION, 'mode': 'action',
        'fail_closed': True, 'inside_sandbox': True,
        'listen': {'guardrail_proxy': f'127.0.0.1:{GUARD_PORT}', 'management_api': f'127.0.0.1:{API_PORT}'},
        'config_sha256': QUALIFIED_GUARD_CONFIG_SHA256,
        'start': ['defenseclaw-gateway', 'start'],  # `start`, not the foreground command: only start writes the PID record
        'home': SANDBOX_HOME, 'audit_dir': AUDIT_DIR, 'audit_db': AUDIT_DIR + '/audit.db',
        'key_handling': 'provider key is attached by OpenShell (sandbox create --provider) at the egress proxy; '
                        'no key file or environment variable exists inside the sandbox',
        'env_names': ['DEFENSECLAW_GATEWAY_TOKEN'],
    }


def export_plan(node, destination):
    """What an audit export collects (a plan, not an action): DefenseClaw audit SQLite, alerts listing, OCSF events."""
    spec = sidecar_spec(node)
    need(isinstance(destination, str) and destination.startswith('/') and '..' not in destination.split('/'), 'invalid_destination')
    return {'node': node, 'destination': destination, 'steps': [
        {'kind': 'copy', 'source': spec['audit_db'], 'target': destination + '/defenseclaw-audit.db', 'mode': 0o600},
        {'kind': 'command', 'argv': ['defenseclaw', 'alerts'], 'target': destination + '/defenseclaw-alerts.txt'},
        {'kind': 'command', 'argv': ['openshell', 'logs', 'netclaw-node'], 'target': destination + '/openshell-ocsf.log'}],
        'retention': 'exported before teardown; contains blocked activity, policy changes and guard state changes'}


def render(out_dir):
    out = Path(out_dir)
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    raw = render_config()
    fd = os.open(out / 'guard-config.yaml', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
    return {'config_sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'out': str(out)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    r = sub.add_parser('render')
    r.add_argument('--out', required=True)
    s = sub.add_parser('spec')
    s.add_argument('--node', required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(render(args.out) if args.action == 'render' else sidecar_spec(args.node), sort_keys=True, indent=2))
        return 0
    except (DefenseClawRefused, OSError) as error:
        print('refused:' + (str(error) if isinstance(error, DefenseClawRefused) else type(error).__name__), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
