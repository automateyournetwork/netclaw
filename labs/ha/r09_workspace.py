#!/usr/bin/env python3
"""R09 full-workspace support for the HA Borders: private-file generation only (no cloud, no deploy, no secrets).

An HA Border's protected HUD (labs/ha/hud_ingress_r09.mjs -> ui/netclaw-visual protected-server.js) is control-only
until its HUD config carries `workspace {path, sha256}`. That entry names a *workspace config* (schema 1) that points
at a separate, normal NetClaw HUD backend (ui/netclaw-visual/server.js) running as another UID with its own
conversation home (OpenClaw config, gateway). See specs/182-multi-region-ha-borders/workspace-plan.md.

Subcommands
  render   write the two byte-identical workspace configs (edge copy + backend copy) and the conversation-home files
  pack     git-archive the pinned backend source tree (+ built dist) into one tar for the VMs
  features print the accepted feature names

Secrets are never written here. The gateway token is referenced as ${OPENCLAW_GATEWAY_TOKEN} (systemd EnvironmentFile on
the VM); the provider key lives only in the gateway unit's EnvironmentFile.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[2]

# Exact mirror of ui/netclaw-visual/src/hud-server/remote-hud.js REMOTE_HUD_FEATURES.
FEATURES = ('overview', 'chat', 'canvas', 'rag', 'members', 'peers', 'skills', 'runtime', 'tokenomics',
            'documentation', 'reference', 'logs', 'operations')
# Features that work on a VM without extra services. `rag` needs rag-mcp (torch/chroma) and is left out by default.
DEFAULT_FEATURES = ('overview', 'chat', 'canvas', 'members', 'peers', 'skills', 'runtime', 'tokenomics',
                    'documentation', 'reference', 'logs', 'operations')
SOURCE_PATHS = ('ui/netclaw-visual', 'docs', 'workspace', 'config', 'SOUL.md', 'IDENTITY.md', 'scripts/mcp-call.py')
SOURCE_SKIP = ('ui/netclaw-visual/test', 'ui/netclaw-visual/node_modules', 'ui/netclaw-visual/deploy',
               'ui/netclaw-visual/integration')
UUID = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
MODEL_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/:-]{0,100}$')


class WorkspaceRefused(ValueError):
    pass


def need(value, code):
    if not value:
        raise WorkspaceRefused(code)


def canonical(value):
    """Same bytes the Border roles hash: sorted keys, compact separators, UTF-8."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_features(features):
    """Mirror remoteHudFeatures(): non-empty, unique, known names, canvas needs chat."""
    features = list(features)
    need(features and len(set(features)) == len(features), 'invalid_workspace_features')
    need(all(f in FEATURES for f in features), 'invalid_workspace_features')
    need('canvas' not in features or 'chat' in features, 'invalid_workspace_features')
    return features


def workspace_config(*, installation_id, conversation_home, upstream_port, features=DEFAULT_FEATURES,
                     border_home, ingress_port):
    """The exact schema-1 object readRemoteHudConfig() accepts (edge and backend read the same bytes)."""
    need(isinstance(installation_id, str) and UUID.match(installation_id), 'invalid_installation_id')
    for name, value in (('conversation_home', conversation_home), ('border_home', border_home)):
        need(isinstance(value, str) and os.path.isabs(value) and os.path.normpath(value) == value and '\x00' not in value,
             'invalid_' + name)
    need(conversation_home != border_home and not conversation_home.startswith(border_home.rstrip('/') + '/')
         and not border_home.startswith(conversation_home.rstrip('/') + '/'), 'invalid_conversation_root')
    need(isinstance(upstream_port, int) and 1024 <= upstream_port <= 65535 and upstream_port != ingress_port,
         'workspace_loop')
    return {'schemaVersion': 1, 'installationId': installation_id,
            'upstream': f'http://127.0.0.1:{upstream_port}', 'conversationHome': conversation_home,
            'conversationConfig': conversation_home + '/openclaw.json', 'features': validate_features(features)}


def openclaw_config(*, model, gateway_port=18789):
    """Conversation-home OpenClaw config: loopback gateway, token by env reference, one model, no tools declared.

    Secrets are never inlined. The exact schema is the pinned OpenClaw's; the install script runs `openclaw doctor`
    style validation against it before the service starts.
    """
    need(isinstance(model, str) and MODEL_ID.match(model), 'invalid_model')
    need(isinstance(gateway_port, int) and 1024 <= gateway_port <= 65535, 'invalid_gateway_port')
    return {'gateway': {'mode': 'local', 'port': gateway_port, 'bind': 'loopback',
                        'auth': {'mode': 'token', 'token': '${OPENCLAW_GATEWAY_TOKEN}'}},
            'agents': {'defaults': {'workspace': '__CONVERSATION_HOME__/workspace',
                                    'model': {'primary': model}}}}


def write_private(path, raw):
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def render(args):
    out = Path(args.out_dir).absolute()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    config = workspace_config(installation_id=args.installation_id, conversation_home=args.conversation_home,
                              upstream_port=args.upstream_port, features=args.features or DEFAULT_FEATURES,
                              border_home=args.border_home, ingress_port=args.ingress_port)
    raw = canonical(config)
    write_private(out / 'workspace.edge.json', raw)       # installed 0600 owned by the Border (edge) UID
    write_private(out / 'workspace.backend.json', raw)    # installed 0600 owned by the conversation UID
    home_files = out / 'conversation-home'
    home_files.mkdir(mode=0o700)
    oc = openclaw_config(model=args.model, gateway_port=args.gateway_port)
    oc['agents']['defaults']['workspace'] = args.conversation_home + '/workspace'
    write_private(home_files / 'openclaw.json', canonical(oc))
    summary = {'workspace_sha256': sha256(raw), 'upstream': config['upstream'], 'features': config['features'],
               'conversation_home': args.conversation_home, 'model': args.model,
               'edge_file': str(out / 'workspace.edge.json'), 'backend_file': str(out / 'workspace.backend.json')}
    write_private(out / 'summary.json', canonical(summary))
    return summary


def pack(args):
    """git-archive the pinned tree (HEAD or --ref), add the built dist, write one tar. Tracked files only."""
    ref = args.ref
    commit = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--verify', ref + '^{commit}'], capture_output=True,
                            text=True, check=True).stdout.strip()
    dist = REPO / 'ui/netclaw-visual/dist'
    need(dist.is_dir() and (dist / 'index.html').is_file(), 'built_dist_required')
    archive = subprocess.run(['git', '-C', str(REPO), 'archive', '--format=tar', commit, '--', *SOURCE_PATHS],
                             capture_output=True, check=True).stdout
    target = Path(args.out).absolute()
    need(not target.exists(), 'output_exists')
    count = 0
    with tarfile.open(fileobj=io.BytesIO(archive)) as src, tarfile.open(target, 'w') as dst:
        for member in src:
            if any(member.name == p or member.name.startswith(p + '/') for p in SOURCE_SKIP):
                continue
            member.uid = member.gid = 0
            member.uname = member.gname = 'root'
            dst.addfile(member, src.extractfile(member) if member.isfile() else None)
            count += 1
        for p in sorted(dist.rglob('*')):
            if p.is_file() and not p.is_symlink():
                info = tarfile.TarInfo('ui/netclaw-visual/dist/' + str(p.relative_to(dist)))
                raw = p.read_bytes()
                info.size, info.mode, info.mtime = len(raw), 0o644, 0
                info.uid = info.gid = 0
                info.uname = info.gname = 'root'
                dst.addfile(info, io.BytesIO(raw))
                count += 1
    return {'commit': commit, 'files': count, 'tar': str(target), 'tar_sha256': sha256(target.read_bytes())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    r = sub.add_parser('render')
    r.add_argument('--installation-id', required=True)
    r.add_argument('--border-home', default='/var/lib/nc182/home')
    r.add_argument('--conversation-home', default='/var/lib/nc182ws/home')
    r.add_argument('--upstream-port', type=int, default=3001)
    r.add_argument('--ingress-port', type=int, default=443)
    r.add_argument('--gateway-port', type=int, default=18789)
    r.add_argument('--model', default='anthropic/claude-sonnet-4-6')
    r.add_argument('--features', nargs='+')
    r.add_argument('--out-dir', required=True)
    k = sub.add_parser('pack')
    k.add_argument('--ref', default='HEAD')
    k.add_argument('--out', required=True)
    sub.add_parser('features')
    args = parser.parse_args(argv)
    try:
        if args.action == 'features':
            result = {'accepted': list(FEATURES), 'default': list(DEFAULT_FEATURES)}
        else:
            result = render(args) if args.action == 'render' else pack(args)
    except (WorkspaceRefused, subprocess.CalledProcessError, FileExistsError) as error:
        print(json.dumps({'refused': str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
