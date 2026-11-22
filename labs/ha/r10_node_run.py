#!/usr/bin/env python3
"""Full R10 lab Border runner, frozen into its OpenShell image.

Starts the protected role, guarded OpenClaw gateway, workspace backend and HTTPS
ingress. There is no uploaded-script execution hook. Provider credentials remain
OpenShell placeholders; an existing local token is required for the gateway.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import r09a_node_run as base


def workspace_env():
    env = dict(os.environ)
    env.update(HOME='/sandbox', OPENCLAW_HOME='/sandbox',
               OPENCLAW_STATE_DIR='/sandbox/.openclaw',
               OPENCLAW_CONFIG_PATH='/sandbox/.openclaw/openclaw.json',
               OPENCLAW_GATEWAY_TOKEN=Path('/sandbox/nc182/gateway-token').read_text().strip(),
               NETCLAW_OPEN_LAB_WORKSPACE_CONFIG='/sandbox/nc182/workspace.json',
               HUD_PORT='3001', HUD_UI_PORT='3000',
               PATH='/opt/nc182/venv/bin:/opt/nc182/node/bin:/opt/nc182/openclaw/node_modules/.bin:/usr/local/bin:/usr/bin:/bin')
    assert env.get('ANTHROPIC_API_KEY', '').startswith('openshell:'), 'provider_placeholder_required'
    return env


def start_workspace():
    env = workspace_env()
    shutil.copyfile(base.STATE / 'guard-config.yaml', '/sandbox/guard-config.yaml'); os.chmod('/sandbox/guard-config.yaml', 0o600)
    with open(base.LOGS / 'guard-setup.log', 'ab', buffering=0) as out:
        subprocess.run(['bash', str(base.STATE / 'bin/r09a_guard_up.sh')], env=env,
                       stdout=out, stderr=out, stdin=subprocess.DEVNULL, check=True, timeout=180)
    # The OpenClaw gateway's DefenseClaw plugin authenticates to the guard with this token (X-DC-Auth) and the guard
    # holds the provider placeholder; guard_up.sh exports both only inside its own shell, so mirror them here.
    env['DEFENSECLAW_GATEWAY_TOKEN'] = Path('/sandbox/.gwtoken').read_text().strip()
    env['DEFENSECLAW_LLM_KEY'] = env['ANTHROPIC_API_KEY']
    cfgpath = Path(env['OPENCLAW_CONFIG_PATH'])
    cfg = json.loads(cfgpath.read_text())
    cfg.setdefault('gateway', {}).update(mode='local', port=18789, bind='loopback',
        auth={'mode': 'token', 'token': '${OPENCLAW_GATEWAY_TOKEN}'},
        http={'endpoints': {'chatCompletions': {'enabled': True}}})
    cfg.setdefault('agents', {}).setdefault('defaults', {})['workspace'] = '/sandbox/.openclaw/workspace'
    # OpenClaw's Anthropic transport refuses a model entry without a positive maxTokens (spec 198 live finding).
    for provider in cfg.get('models', {}).get('providers', {}).values():
        for model in provider.get('models', []):
            model.setdefault('maxTokens', 8192); model.setdefault('contextWindow', 200000)
    cfgpath.write_bytes(base.canonical(cfg)); os.chmod(cfgpath, 0o600)
    base.spawn('chat-gateway', ['/opt/nc182/openclaw/node_modules/.bin/openclaw', 'gateway', '--port', '18789'],
               '/sandbox', env)
    base.spawn('workspace-backend', ['/opt/nc182/node/bin/node', 'server.js'],
               '/opt/nc182/netclaw/ui/netclaw-visual', env)


def prepare_ingress():
    node = json.loads((base.STATE / 'node.json').read_text())
    cluster = json.loads((base.STATE / 'cluster.json').read_text())
    hud = base.STATE / 'hud'; hud.mkdir(mode=0o700, exist_ok=True)
    data = {
        'origin': 'https://' + node['dns'], 'bind': '127.0.0.1', 'port': 8443,
        'installation_id': node['installation_id'], 'home': str(base.HOME),
        'source_root': str(base.OPT / 'hud-source'),
        'source_manifest_file': str(base.STATE / 'manifests/hud-source-manifest.json'),
        'dist': str(base.OPT / 'hud-source/ui/netclaw-visual/dist'), 'edge_ws_port': 8444,
        'manifest_file': str(base.STATE / 'identity/manifest.json'),
        'anchor_certificate_file': str(base.STATE / 'identity/root.crt'), 'anchor_key_id': node['anchor_key_id'],
        'cluster': {'cluster_id': cluster['cluster_id'], 'generation': cluster['generation'], 'anchor_key_id': node['anchor_key_id']},
        'tls': {'cert_file': str(base.STATE / 'tls/fullchain.pem'), 'chain_file': None, 'key_file': str(base.STATE / 'tls/key.pem')},
        'state_dir': str(hud), 'posture_file': str(base.POSTURE),
        'workspace': {'path': str(base.STATE / 'workspace.json')}}
    for p in hud.iterdir():
        if p.is_file():
            p.unlink()
    (hud / 'input.json').write_bytes(base.canonical(data)); os.chmod(hud / 'input.json', 0o600)
    with open(base.LOGS / 'ingress-prepare.log', 'ab', buffering=0) as out:
        subprocess.run(['/opt/nc182/node/bin/node', str(base.OPT / 'hud-source/labs/ha/hud_ingress_r09.mjs'),
                        'prepare', str(hud / 'input.json')], stdout=out, stderr=out, check=True,
                       cwd=hud, env={'PATH': '/usr/bin:/bin', 'HOME': str(hud)}, timeout=60)


def main():
    base.prepare()
    node = json.loads((base.STATE / 'node.json').read_text())
    start_workspace()
    base.start_border()
    descriptor = base.HOME / 'netclaw-federation/protected-operator.json'
    deadline = time.monotonic() + 180
    while not descriptor.exists() and time.monotonic() < deadline:
        if base.procs['border-role'].poll() is not None:
            raise RuntimeError('border_start_failed')
        time.sleep(1)
    if not descriptor.exists():
        raise RuntimeError('border_descriptor_timeout')
    base.write_posture(node)
    prepare_ingress(); base.start_ingress()
    stopped = False
    def halt(*_):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, halt); signal.signal(signal.SIGINT, halt)
    try:
        while not stopped:
            base.write_posture(node)
            # A failed required component ends the node; no silent partial success.
            if any(p.poll() is not None for p in base.procs.values()):
                raise RuntimeError('required_component_failed')
            time.sleep(3)
    finally:
        for p in base.procs.values():
            p.terminate()


if __name__ == '__main__':
    main()
