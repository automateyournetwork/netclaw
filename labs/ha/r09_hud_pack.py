#!/usr/bin/env python3
"""Pack the HUD closure (built dist + HUD server source + R09 ingress) for a Border VM.

Writes hud-source.tar: labs/ha/hud_ingress_r09.mjs and ui/netclaw-visual/{package.json,
package-lock.json,dist/**,src/** (no tests)}. node_modules is installed on the VM
(`npm ci --omit=dev --ignore-scripts`) by r09_vm_hud.py and then frozen with the tree.
"""
import io
import os
from pathlib import Path
import sys
import tarfile

REPO = Path(__file__).resolve().parents[2]
UI = 'ui/netclaw-visual'


def files():
    out = {'labs/ha/hud_ingress_r09.mjs': REPO / 'labs/ha/hud_ingress_r09.mjs'}
    for name in ('package.json', 'package-lock.json'):
        out[f'{UI}/{name}'] = REPO / UI / name
    for sub in ('dist', 'src'):
        for p in sorted((REPO / UI / sub).rglob('*')):
            if not p.is_file() or p.is_symlink():
                continue
            rel = p.relative_to(REPO / UI)
            if sub == 'src' and (p.name.endswith(('.test.js', '.test.jsx', '.test.mjs')) or '__tests__' in rel.parts):
                continue
            out[f'{UI}/{rel}'] = p
    return out


def main(target):
    entries = files()
    with tarfile.open(target, 'w') as archive:
        for name, path in entries.items():
            raw = path.read_bytes()
            info = tarfile.TarInfo(name)
            info.size = len(raw); info.mode = 0o644; info.mtime = 0
            info.uid = info.gid = 0; info.uname = info.gname = 'root'
            archive.addfile(info, io.BytesIO(raw))
    print(f'{len(entries)} files -> {target}')


if __name__ == '__main__':
    main(sys.argv[1])
