#!/usr/bin/env python3
"""R09A (spec 183) in-sandbox node runner. Runs as the `sandbox` user INSIDE an OpenShell sandbox; stdlib only.

Expects, uploaded to /sandbox/nc182 before it starts: the identity bundle (home/, identity/, transport/, etcd-client/,
contract.template.json, node.json), cluster.json, tls/{fullchain.pem,key.pem}, policy.sha256, and (optionally) a file
`ENABLE_WORKSPACE` later. The image provides /opt/nc182/{source,hud-source,venv,node,manifests}.

Steps: private manifest copies -> contract.json (python/env digests filled from the image) -> Border role (the production
launcher) -> wait for its operator descriptor -> HUD ingress prepare + serve -> posture file refreshed every few seconds.
Posture reports only what is observed; components outside the sandbox carry a disposition and are never "enforced".
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

STATE = Path('/sandbox/nc182')
OPT = Path('/opt/nc182')
HOME = STATE / 'home'
LOGS = STATE / 'logs'
POSTURE = STATE / 'posture.json'
EDGE_PORT, INGRESS_PORT = 8444, 8443
procs = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def private_tree():
    for directory, dirs, files in os.walk(STATE):
        os.chmod(directory, 0o700)
        for name in files:
            os.chmod(Path(directory) / name, 0o600)


def prepare():
    private_tree()
    manifests = STATE / 'manifests'
    manifests.mkdir(mode=0o700, exist_ok=True)
    for name in ('source-manifest.json', 'python-env-manifest.json', 'hud-source-manifest.json'):
        shutil.copy(OPT / 'manifests' / name, manifests / name)
        os.chmod(manifests / name, 0o600)
    contract = json.loads((STATE / 'contract.template.json').read_text())
    assert contract['source_manifest_sha256'] == sha(manifests / 'source-manifest.json'), 'source manifest changed'
    contract['python_sha256'] = sha(Path('/opt/nc182/venv/bin/python').resolve())
    contract['python_env_manifest_sha256'] = sha(manifests / 'python-env-manifest.json')
    path = STATE / 'contract.json'
    path.write_bytes(canonical(contract))
    os.chmod(path, 0o600)
    LOGS.mkdir(mode=0o700, exist_ok=True)


def spawn(name, argv, cwd, env):
    log = open(LOGS / f'{name}.log', 'ab', buffering=0)
    procs[name] = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    return procs[name]


def start_border():
    spawn('border-role', ['/opt/nc182/venv/bin/python', '-I', '-B', '/opt/nc182/source/scripts/protected-role.py',
                          '--contract', str(STATE / 'contract.json'), 'run'], HOME,
          {'PATH': '/usr/bin:/bin', 'HOME': str(HOME)})


def prepare_ingress():
    node = json.loads((STATE / 'node.json').read_text())
    cluster = json.loads((STATE / 'cluster.json').read_text())
    hud = STATE / 'hud'
    hud.mkdir(mode=0o700, exist_ok=True)
    data = {
        'origin': 'https://' + node['dns'], 'bind': '127.0.0.1', 'port': INGRESS_PORT,
        'installation_id': node['installation_id'], 'home': str(HOME),
        'source_root': str(OPT / 'hud-source'), 'source_manifest_file': str(STATE / 'manifests/hud-source-manifest.json'),
        'dist': str(OPT / 'hud-source/ui/netclaw-visual/dist'), 'edge_ws_port': EDGE_PORT,
        'manifest_file': str(STATE / 'identity/manifest.json'), 'anchor_certificate_file': str(STATE / 'identity/root.crt'),
        'anchor_key_id': node['anchor_key_id'],
        'cluster': {'cluster_id': cluster['cluster_id'], 'generation': cluster['generation'], 'anchor_key_id': node['anchor_key_id']},
        'tls': {'cert_file': str(STATE / 'tls/fullchain.pem'), 'chain_file': None, 'key_file': str(STATE / 'tls/key.pem')},
        'state_dir': str(hud), 'posture_file': str(POSTURE)}
    (hud / 'input.json').write_bytes(canonical(data))
    os.chmod(hud / 'input.json', 0o600)
    for stale in hud.iterdir():
        if stale.is_file() and stale.name != 'input.json':
            stale.unlink()
    result = subprocess.run(['/opt/nc182/node/bin/node', str(OPT / 'hud-source/labs/ha/hud_ingress_r09.mjs'), 'prepare', str(hud / 'input.json')],
                            capture_output=True, text=True, cwd=str(hud), env={'PATH': '/usr/bin:/bin', 'HOME': str(hud)})
    (LOGS / 'ingress-prepare.log').write_text(result.stdout + result.stderr)
    return result.returncode == 0


def start_ingress():
    hud = STATE / 'hud'
    spawn('hud-ingress', ['/opt/nc182/node/bin/node', str(OPT / 'hud-source/labs/ha/hud_ingress_r09.mjs'), 'serve', str(hud / 'ingress.json')],
          hud, {'PATH': '/usr/bin:/bin', 'HOME': str(hud)})


def write_posture(node):
    comps = []
    for name in ('border-role', 'hud-ingress', 'workspace-backend', 'chat-gateway', 'defenseclaw-sidecar'):
        p = procs.get(name)
        if p is None:
            continue
        comps.append({'name': name, 'inside_sandbox': True, 'state': 'running' if p.poll() is None else 'failed'})
    comps.append({'name': 'etcd-voter', 'inside_sandbox': False, 'disposition': 'host network; container policy', 'state': 'unknown'})
    guard = {'mode': 'none', 'state': 'stopped', 'fail_closed': True, 'last_block_ms': None}
    if (STATE / 'guard.json').exists():
        try:
            guard = json.loads((STATE / 'guard.json').read_text())
        except Exception:
            pass
    policy_sha = (STATE / 'policy.sha256').read_text().strip() if (STATE / 'policy.sha256').exists() else '0' * 64
    posture = {'schema_version': 1, 'node': node['code'], 'region': 'northamerica-northeast1',
               'sandbox': {'name': 'netclaw-node', 'phase': 'Ready', 'policy_version': 1, 'policy_sha256': policy_sha, 'landlock': 'hard_requirement'},
               'components': comps, 'guard': guard, 'observed_at_ms': int(time.time() * 1000)}
    tmp = STATE / 'posture.json.tmp'
    tmp.write_bytes(canonical(posture))
    os.chmod(tmp, 0o600)
    os.replace(tmp, POSTURE)


def main():
    prepare()
    node = json.loads((STATE / 'node.json').read_text())
    start_border()
    descriptor = HOME / 'netclaw-federation/protected-operator.json'
    deadline = time.time() + 180
    while not descriptor.exists() and time.time() < deadline:
        time.sleep(1)
    if descriptor.exists():
        write_posture(node)
        if prepare_ingress():
            start_ingress()
    stop = False

    def halt(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, halt)
    signal.signal(signal.SIGINT, halt)
    ctl = STATE / 'CTL'
    ctl.mkdir(mode=0o700, exist_ok=True)
    while not stop:
        if (ctl / 'stop-border').exists():
            (ctl / 'stop-border').unlink()
            try:
                descriptor.unlink()
            except FileNotFoundError:
                pass
            for name in ('hud-ingress', 'border-role'):
                p = procs.pop(name, None)
                if p is not None:
                    p.terminate()
                    try:
                        p.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        p.kill()
        if (ctl / 'start-border').exists():
            (ctl / 'start-border').unlink()
            if 'border-role' not in procs:
                start_border()
                deadline2 = time.time() + 120
                while not descriptor.exists() and time.time() < deadline2:
                    time.sleep(1)
                if prepare_ingress():
                    start_ingress()
        write_posture(node)
        time.sleep(3)
    for p in procs.values():
        p.terminate()


if __name__ == '__main__':
    sys.exit(main())
