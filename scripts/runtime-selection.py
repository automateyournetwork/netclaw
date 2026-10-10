#!/usr/bin/env python3
"""Unix bootstrap selection. Golden fixtures also test runtime-selection.mjs."""
import json
import os
from pathlib import Path
import sys

def resolve_values(env, owner_home, descriptor=None):
    if descriptor is not None:
        if not isinstance(descriptor, dict) or descriptor.get('schemaVersion') != 1 or descriptor.get('kind') not in ('openclaw', 'hermes'):
            raise ValueError('selection_invalid: invalid runtime descriptor')
        if not isinstance(descriptor.get('home'), str) or not os.path.isabs(descriptor['home']):
            raise ValueError('selection_invalid: absolute runtime home required')
    kind = env.get('NETCLAW_RUNTIME', (descriptor or {}).get('kind', 'openclaw'))
    if kind not in ('openclaw', 'hermes'): raise ValueError('selection_invalid: expected openclaw or hermes')
    matching = descriptor if descriptor and descriptor['kind'] == kind else {}
    override = env.get('HERMES_HOME') if kind == 'hermes' else env.get('OPENCLAW_STATE_DIR') or env.get('OPENCLAW_HOME')
    home = override or matching.get('home') or os.path.join(owner_home, '.' + kind)
    if not os.path.isabs(home) or os.path.normpath(home) == os.path.sep: raise ValueError('selection_invalid: absolute non-root home required')
    home = os.path.normpath(home)
    inherited = matching.get('configPath') if home == matching.get('home') else None
    config = (env.get('OPENCLAW_CONFIG_PATH') or inherited) if kind == 'openclaw' else None
    config = config or os.path.join(home, 'openclaw.json' if kind == 'openclaw' else 'config.yaml')
    if not os.path.isabs(config): raise ValueError('selection_invalid: absolute config path required')
    return dict(kind=kind, home=home, configPath=os.path.normpath(config))

def resolve(env=None):
    env = os.environ if env is None else env
    owner = env.get('HOME') or str(Path.home())
    file = Path(env.get('XDG_CONFIG_HOME') or Path(owner)/'.config') / 'netclaw/runtime.json'
    descriptor = None
    if file.exists() or file.is_symlink():
        stat = file.lstat()
        if file.is_symlink() or not file.is_file() or stat.st_size > 8192 or stat.st_mode & 0o077 or stat.st_uid != os.getuid():
            raise ValueError('selection_invalid: private owner descriptor required')
        descriptor = json.loads(file.read_text())
    return resolve_values(env, owner, descriptor)

if __name__ == '__main__':
    try:
        value = resolve()
        if len(sys.argv) == 3 and sys.argv[1] == '--field': print(value[sys.argv[2]])
        else: print(json.dumps(value))
    except Exception:
        print('selection_invalid: repair the private runtime descriptor or explicit selection.', file=sys.stderr)
        sys.exit(1)
