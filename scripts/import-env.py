#!/usr/bin/env python3
"""Preview or import checkout dotenv settings into the runtime's durable dotenv.

No shell evaluation, interpolation, provider calls, or runtime config changes.
Existing destination assignments always win. Diagnostics contain names only.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT = re.compile(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')
QUOTED = re.compile(r'''^(["'`])((?:\\.|(?!\1).)*)\1\s*(?:\#.*)?$''')
PLACEHOLDER = re.compile(r'^(?:changeme|your[-_].*|.*\.\.\..*|/path/to/.*|x{8}-x{4}-x{4}-x{4}-x{12})$', re.I)


def records(text):
    """Keep original single-line assignments; parse only for blank/conflict checks."""
    result = {}
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        match = ASSIGNMENT.fullmatch(stripped)
        if not match or '\0' in line:
            raise ValueError(f'Invalid dotenv assignment on line {number}')
        key, raw = match.groups()
        if raw.startswith(('"', "'", '`')):
            quoted = QUOTED.fullmatch(raw)
            if not quoted:
                raise ValueError(f'Invalid or multiline dotenv value on line {number}')
            value = quoted[2]
        else:
            value = raw.split('#', 1)[0].strip()
        result[key] = (value, stripped)
    return result


def read_regular(path):
    if path.is_symlink() or (path.exists() and not stat.S_ISREG(path.stat().st_mode)):
        raise ValueError('Dotenv paths must be regular files, not symlinks')
    if not path.exists():
        return ''
    with path.open(encoding='utf-8', newline='') as stream:
        return stream.read()


def import_env(source, target, apply=False):
    # Validate both files completely before any mutation, even in preview mode.
    source_text = read_regular(source)
    original = read_regular(target)
    incoming, existing = records(source_text), records(original)
    declared = set()
    for line in (ROOT / '.env.example').read_text().splitlines():
        match = ASSIGNMENT.fullmatch(line.lstrip('# ').strip())
        if match:
            declared.add(match[1])
    groups = {name: [] for name in ('import', 'preserved', 'conflict', 'blank', 'placeholder', 'unsupported')}
    additions = []
    for key, (value, line) in incoming.items():
        if key not in declared:
            groups['unsupported'].append(key)
        elif key in existing:
            groups['preserved' if value == existing[key][0] else 'conflict'].append(key)
        elif not value.strip():
            groups['blank'].append(key)
        elif PLACEHOLDER.fullmatch(value):
            groups['placeholder'].append(key)
        else:
            groups['import'].append(key)
            additions.append(line)
    if apply and additions:
        spec = importlib.util.spec_from_file_location('netclaw_env_writer', ROOT / 'scripts/write-env.py')
        writer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(writer)
        separator = '\n' if original and not original.endswith('\n') else ''
        writer.write_private(target, original + separator + '\n'.join(additions) + '\n')
    print('Dotenv import: ' + ('applied' if apply else 'preview (use --apply to write)'))
    print('Runtime environment: ' + str(target))
    labels = {
        'import': 'Imported' if apply else 'Would import',
        'preserved': 'Already present', 'conflict': 'Kept runtime values (conflicts)',
        'blank': 'Skipped blank values', 'placeholder': 'Skipped template placeholders',
        'unsupported': 'Skipped undeclared names (configure these directly in the runtime)',
    }
    for group, keys in groups.items():
        if keys:
            print(f'{labels[group]}: ' + ', '.join(sorted(keys)))
    if not incoming:
        print('No checkout assignments to import.')
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.env')
    parser.add_argument('--target', type=Path, help='Override the runtime dotenv path')
    parser.add_argument('--runtime', choices=('openclaw', 'hermes'), default=os.environ.get('NETCLAW_RUNTIME', 'openclaw'))
    parser.add_argument('--apply', action='store_true', help='Write missing settings; default is preview only')
    args = parser.parse_args()
    if args.runtime == 'hermes':
        state = Path(os.environ.get('HERMES_HOME') or Path.home() / '.hermes')
    else:
        # Retain NetClaw's historical OPENCLAW_HOME state-dir fallback.
        state = Path(os.environ.get('OPENCLAW_STATE_DIR') or os.environ.get('OPENCLAW_HOME') or Path.home() / '.openclaw')
    try:
        import_env(args.source.absolute(), (args.target or state / '.env').absolute(), args.apply)
    except (OSError, UnicodeError, ValueError) as error:
        # OS exceptions can embed paths or file contents. Never echo them.
        detail = str(error) if type(error) is ValueError else type(error).__name__
        print('Dotenv import failed: ' + detail, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
