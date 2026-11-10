#!/usr/bin/env python3
"""R09A (spec 183) node image build-context generator. Generates files only; it never runs docker or the network.

Produces a build context for the `netclaw-node` OpenShell sandbox image: python:3.12-slim base, a `sandbox` user with a
fixed uid, Node 24 from nodejs.org (SHASUMS-checked), a Python 3.12 venv with the pinned Border dependencies, pinned
OpenClaw 2026.7.1-2 (--ignore-scripts), DefenseClaw 1.0.4 via the checksum-verified release installer, and the frozen
Border/HUD/workspace source trees made root-owned and read-only by `freeze_image.py` (the same immutability and
manifest rules as labs/ha/r09_vm_finalize.py / r09_vm_hud.py). No secret is baked in; state lives under /sandbox, owned
by the sandbox user, and identity/credential material arrives at deploy time.

  python -m labs.ha.r09a_image context --out DIR [--source-tar T --source-manifest M] [--hud-tar H] [--workspace-tar W]
                                       [--base-image REF] [--require-inputs]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

PY_BASE_IMAGE = 'python:3.12-slim'            # pass --base-image <repo>@sha256:<digest> to pin by digest
NODE_VERSION = '24.22.2'
OPENCLAW_VERSION = '2026.7.1-2'
DEFENSECLAW_VERSION = '1.0.4'
SANDBOX_UID = 20183
PYTHON_PACKAGES = ['cryptography==50.0.2', 'pyOpenSSL==26.4.0', 'service-identity==26.1.0', 'httpx>=0.27',
                   'websockets>=12.0,<17', 'qrcode>=7.4', 'PyYAML>=6.0', 'h2>=4.1']
INPUT_NAMES = ('source.tar', 'source-manifest.json', 'hud-source.tar', 'workspace-backend.tar')
SECRET_LIKE = re.compile(r'(sk-ant-[A-Za-z0-9_-]{8,}|nbt_[A-Za-z0-9._-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|'
                         r'ANTHROPIC_API_KEY\s*=\s*\S|NETBOX_TOKEN\s*=\s*\S|GODADDY_PAT\s*=\s*\S)')
DOCKERIGNORE = '*.env\n*.key\n*.pem\n**/guard.env\n**/provider*\n**/.env\n**/credentials*\n'

FREEZE_SCRIPT = r'''#!/usr/bin/env python3
"""Image build step (root): extract the frozen trees, write manifests, make everything root-owned and read-only.
Adapted from labs/ha/r09_vm_finalize.py (env manifest, freeze) and labs/ha/r09_vm_hud.py (npm ci, no symlinks)."""
import hashlib, json, os, shutil, stat, subprocess, tarfile
from pathlib import Path

OPT = Path('/opt/nc182')
MANIFESTS = OPT / 'manifests'
TREES = {'source.tar': OPT / 'source', 'hud-source.tar': OPT / 'hud-source', 'workspace-backend.tar': OPT / 'netclaw'}
NPM_DIRS = {'hud-source.tar': 'ui/netclaw-visual', 'workspace-backend.tar': 'ui/netclaw-visual'}
NODE_BIN = OPT / 'node/bin'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def freeze_tree(root):
    for directory, dirs, files in os.walk(root, followlinks=False):
        os.chown(directory, 0, 0)
        for name in files:
            p = Path(directory) / name
            if p.is_symlink():
                continue
            os.chown(p, 0, 0)
            os.chmod(p, 0o555 if stat.S_IMODE(p.lstat().st_mode) & 0o111 else 0o444)
    for directory, _, _ in os.walk(root, topdown=False, followlinks=False):
        os.chmod(directory, 0o555)


def tree_manifest(root):
    return {'schemaVersion': 1, 'files': {str(p.relative_to(root)): sha(p) for p in sorted(Path(root).rglob('*')) if p.is_file()}}


def env_manifest(venv):
    files, links = {}, {}
    for directory, dirs, names in os.walk(venv, followlinks=False):
        for name in dirs + names:
            p = Path(directory) / name
            rel = str(p.relative_to(venv))
            if p.is_symlink():
                links[rel] = os.readlink(p)
            elif p.is_file():
                files[rel] = sha(p)
    return {'schemaVersion': 1, 'files': files, 'symlinks': links}


def main():
    MANIFESTS.mkdir(mode=0o755, parents=True, exist_ok=True)
    present = [name for name in TREES if Path('/tmp/inputs', name).exists()]
    for name in present:
        target = TREES[name]
        target.mkdir(mode=0o755, parents=True, exist_ok=False)
        with tarfile.open(Path('/tmp/inputs', name)) as archive:
            archive.extractall(target, filter='data')
        if name in NPM_DIRS:
            env = {'PATH': f'{NODE_BIN}:/usr/bin:/bin', 'HOME': '/root'}
            subprocess.run([str(NODE_BIN / 'npm'), 'ci', '--omit=dev', '--ignore-scripts', '--no-audit', '--no-fund'],
                           cwd=target / NPM_DIRS[name], env=env, check=True, capture_output=True)
            for directory, dirs, files in os.walk(target, followlinks=False):  # the ingress refuses symlink aliases
                for entry in list(dirs) + list(files):
                    p = Path(directory) / entry
                    if p.is_symlink():
                        p.unlink()
                        if entry in dirs:
                            dirs.remove(entry)
    manifest_in = Path('/tmp/inputs/source-manifest.json')
    if manifest_in.exists():
        shutil.copy(manifest_in, MANIFESTS / 'source-manifest.json')
    for name in present:
        if name != 'source.tar':
            (MANIFESTS / (TREES[name].name + '-manifest.json')).write_text(
                json.dumps(tree_manifest(TREES[name]), sort_keys=True, separators=(',', ':')))
    (MANIFESTS / 'python-env-manifest.json').write_text(json.dumps(env_manifest('/opt/nc182/venv'), sort_keys=True, separators=(',', ':')))
    subprocess.run(['chmod', '-R', 'go-w,u-w', '/opt/nc182/venv'], check=True)
    for tree in list(TREES.values()) + [OPT / 'venv', OPT / 'node', OPT / 'openclaw', OPT / 'manifests']:
        if tree.exists():
            freeze_tree(tree)
    print(json.dumps({'trees': present, 'manifests': sorted(p.name for p in MANIFESTS.iterdir())}))


if __name__ == '__main__':
    main()
'''


def dockerfile(base_image=PY_BASE_IMAGE):
    packages = ' '.join("'%s'" % p for p in PYTHON_PACKAGES)
    return f'''# R09A node image (spec 183). Generated by labs/ha/r09a_image.py; no secrets are baked in.
FROM {base_image}
ARG NODE_VERSION={NODE_VERSION}
ARG OPENCLAW_VERSION={OPENCLAW_VERSION}
ARG DEFENSECLAW_VERSION={DEFENSECLAW_VERSION}
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates xz-utils git \\
    && rm -rf /var/lib/apt/lists/*

# The policy's run_as_user must exist in the image (OpenShell: IdentityResolutionFailed otherwise).
RUN groupadd -g {SANDBOX_UID} sandbox && useradd -u {SANDBOX_UID} -g {SANDBOX_UID} -m -s /bin/bash sandbox \\
    && install -d -m 0700 -o sandbox -g sandbox /sandbox

# Node from nodejs.org, verified against the published SHASUMS.
RUN set -e; f="node-v${{NODE_VERSION}}-linux-x64.tar.xz"; base="https://nodejs.org/dist/v${{NODE_VERSION}}"; \\
    curl -fsSL --proto '=https' --tlsv1.2 "$base/$f" -o "/tmp/$f"; \\
    curl -fsSL --proto '=https' --tlsv1.2 "$base/SHASUMS256.txt" -o /tmp/SHASUMS256.txt; \\
    (cd /tmp && grep " $f$" SHASUMS256.txt | sha256sum -c -); \\
    mkdir -p /opt/nc182/node && tar -xJf "/tmp/$f" -C /opt/nc182/node --strip-components=1; \\
    rm -f "/tmp/$f" /tmp/SHASUMS256.txt

# Python 3.12 environment with the pinned Border dependencies (venv manifest is written by freeze_image.py).
RUN python -m venv /opt/nc182/venv && /opt/nc182/venv/bin/pip install --no-cache-dir {packages}

# Pinned OpenClaw (qualified version), no install scripts.
RUN export PATH=/opt/nc182/node/bin:$PATH && npm install --prefix /opt/nc182/openclaw --ignore-scripts --no-audit --no-fund \\
    "openclaw@${{OPENCLAW_VERSION}}" && /opt/nc182/openclaw/node_modules/.bin/openclaw --version

# DefenseClaw from the pinned, checksum-verified release installer (binaries are then copied root-owned to /usr/local/bin;
# runtime data lives under /sandbox at deploy time via `defenseclaw init` with HOME=/sandbox).
RUN set -e; d="$(mktemp -d)"; base="https://github.com/cisco-ai-defense/defenseclaw/releases/download/${{DEFENSECLAW_VERSION}}"; \\
    curl -fsSL --proto '=https' --tlsv1.2 -o "$d/install.sh" "$base/install.sh"; \\
    curl -fsSL --proto '=https' --tlsv1.2 -o "$d/checksums.txt" "$base/checksums.txt"; \\
    (cd "$d" && grep -E '[[:space:]]\\*?install\\.sh$' checksums.txt | sha256sum -c -); \\
    mkdir -p /opt/nc182/dc-home; \\
    HOME=/opt/nc182/dc-home PATH=/opt/nc182/node/bin:/opt/nc182/openclaw/node_modules/.bin:$PATH bash "$d/install.sh" --yes --connector openclaw; \\
    install -m 0555 /opt/nc182/dc-home/.local/bin/defenseclaw /opt/nc182/dc-home/.local/bin/defenseclaw-gateway /usr/local/bin/; \\
    rm -rf "$d"

# Frozen trees (root-owned, read-only) and manifests.
COPY inputs/ /tmp/inputs/
COPY freeze_image.py /opt/freeze_image.py
RUN python /opt/freeze_image.py && rm -rf /tmp/inputs /opt/freeze_image.py

USER sandbox
WORKDIR /sandbox
ENV PATH=/opt/nc182/venv/bin:/opt/nc182/node/bin:/opt/nc182/openclaw/node_modules/.bin:/usr/local/bin:/usr/bin:/bin \\
    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
'''


def assert_no_secrets(text):
    if SECRET_LIKE.search(text):
        raise ValueError('secret_in_build_context_refused')


def build_context(out_dir, inputs=None, base_image=PY_BASE_IMAGE, require_inputs=False):
    """Write Dockerfile, freeze_image.py, .dockerignore and inputs/ under a fresh private directory."""
    inputs = dict(inputs or {})
    unknown = set(inputs) - set(INPUT_NAMES)
    if unknown:
        raise ValueError('unknown_input_refused')
    if not re.fullmatch(r'[a-z0-9./:_-]+(@sha256:[a-f0-9]{64})?', base_image):
        raise ValueError('base_image_invalid')
    if require_inputs and not {'source.tar', 'source-manifest.json'} <= set(inputs):
        raise ValueError('required_inputs_missing')
    out = Path(out_dir)
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    (out / 'inputs').mkdir(mode=0o700)
    files = {}
    for name, text in (('Dockerfile', dockerfile(base_image)), ('freeze_image.py', FREEZE_SCRIPT), ('.dockerignore', DOCKERIGNORE)):
        assert_no_secrets(text)
        fd = os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        files[name] = hashlib.sha256(text.encode()).hexdigest()
    for name, source in inputs.items():
        source = Path(source)
        if not source.is_file() or source.is_symlink():
            raise ValueError('input_not_a_file')
        shutil.copyfile(source, out / 'inputs' / name)
        os.chmod(out / 'inputs' / name, 0o600)
        files['inputs/' + name] = hashlib.sha256((out / 'inputs' / name).read_bytes()).hexdigest()
    if not inputs:  # an empty directory is still copyable; the freeze step then makes no trees
        (out / 'inputs' / '.keep').write_text('')
    report = {'schema_version': 1, 'base_image': base_image, 'sandbox_uid': SANDBOX_UID,
              'versions': {'node': NODE_VERSION, 'openclaw': OPENCLAW_VERSION, 'defenseclaw': DEFENSECLAW_VERSION},
              'python_packages': PYTHON_PACKAGES, 'files': files,
              'missing_inputs': sorted(set(INPUT_NAMES) - set(inputs))}
    (out / 'context.json').write_text(json.dumps(report, sort_keys=True, indent=2))
    os.chmod(out / 'context.json', 0o600)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    c = sub.add_parser('context')
    c.add_argument('--out', required=True)
    c.add_argument('--source-tar')
    c.add_argument('--source-manifest')
    c.add_argument('--hud-tar')
    c.add_argument('--workspace-tar')
    c.add_argument('--base-image', default=PY_BASE_IMAGE)
    c.add_argument('--require-inputs', action='store_true')
    args = parser.parse_args(argv)
    given = {'source.tar': args.source_tar, 'source-manifest.json': args.source_manifest,
             'hud-source.tar': args.hud_tar, 'workspace-backend.tar': args.workspace_tar}
    try:
        print(json.dumps(build_context(args.out, {k: v for k, v in given.items() if v}, args.base_image, args.require_inputs),
                         sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print('refused:' + str(error if isinstance(error, ValueError) else type(error).__name__), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
