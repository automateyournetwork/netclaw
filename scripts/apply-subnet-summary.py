#!/usr/bin/env python3
"""Apply the reviewed bounded summary patch only to exact native subnet bytes."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile

BEFORE = 'bfb8bb548aa7096c0b2324a3798c581ce917a26388aa6193ae66eb0708e7dd45'
AFTER = '582f3203269612fcf949c5875e41ac557bb096d6476c846e1ac921ba559a6364'


def patch_bytes(raw, patch):
    source, lines = raw.splitlines(keepends=True), patch.splitlines(keepends=True)
    if lines[:2] != [b'--- a/servers/subnetcalculator_mcp.py\n', b'+++ b/servers/subnetcalculator_mcp.py\n']:
        raise ValueError('patch_path_changed')
    result, cursor, i = [], 0, 2
    while i < len(lines):
        match = re.fullmatch(rb'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', lines[i])
        if not match: raise ValueError('patch_shape_changed')
        start = int(match[1])-1
        if start < cursor or start > len(source): raise ValueError('patch_range_changed')
        result.extend(source[cursor:start]); cursor=start; i+=1
        old, new = 0, 0
        while i < len(lines) and not lines[i].startswith(b'@@'):
            kind, value = lines[i][:1], lines[i][1:]
            if kind in (b' ', b'-'):
                if cursor >= len(source) or source[cursor] != value: raise ValueError('patch_context_changed')
                cursor += 1; old += 1
            if kind in (b' ', b'+'): result.append(value); new += 1
            if kind not in (b' ', b'+', b'-'): raise ValueError('patch_line_changed')
            i += 1
        if old != int(match[2] or b'1') or new != int(match[4] or b'1'): raise ValueError('patch_count_changed')
    result.extend(source[cursor:])
    return b''.join(result)


def apply(root):
    root=Path(root).absolute();target=root/'servers/subnetcalculator_mcp.py'
    if root.resolve()!=root or target.resolve()!=target: raise ValueError('source_symlink_refused')
    info=target.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022: raise ValueError('source_mode_refused')
    raw=target.read_bytes();before=hashlib.sha256(raw).hexdigest()
    if before==AFTER:return {'changed':False,'source_sha256':AFTER}
    if before!=BEFORE:raise ValueError('native_source_revision_unqualified')
    patched=patch_bytes(raw,Path(__file__).with_name('patches').joinpath('subnet-calculator-bounded.patch').read_bytes())
    if hashlib.sha256(patched).hexdigest()!=AFTER:raise ValueError('patch_digest_changed')
    fd,name=tempfile.mkstemp(prefix='.subnet-summary-',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(patched);stream.flush();os.fsync(stream.fileno())
        os.chmod(name,stat.S_IMODE(info.st_mode));os.replace(name,target)
        directory=os.open(target.parent,os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(name):os.unlink(name)
    return {'changed':True,'source_sha256':AFTER}


if __name__=='__main__':
    import json
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root')
    args=parser.parse_args()
    try:print(json.dumps(apply(args.root)))
    except (OSError,ValueError) as exc:parser.exit(1,'Subnet summary patch refused: '+(str(exc) if isinstance(exc,ValueError) else 'source_unavailable')+'\n')
