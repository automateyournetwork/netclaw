"""Refuse standalone setup of a home that requires private cluster authority.

Presence is deliberately sufficient: a damaged marker is never permission to
fall back. This module reads metadata only and does not migrate or remove it.
"""
import argparse
import os
from pathlib import Path
import sys

from setup_state import Conflict, directory, guarded_read
from setup_schema import loads


def require_standalone_home(home):
    home = Path(home).expanduser().absolute()
    state = home / 'netclaw-federation'
    marker = state / 'ha-required.json'
    if os.path.lexists(marker):
        raise Conflict('ha_home_requires_cluster_workflow')
    if not os.path.lexists(state):
        # Preserve legacy path handling when there is no protected state at all.
        # Existing installation writers retain their own path/ownership checks.
        return
    try:
        # Existing protected state must be a real, owner-safe directory.
        with directory(state): pass
    except FileNotFoundError:
        return
    profile = state / 'protected-profile.json'
    try:
        value = loads(guarded_read(profile, 1024 * 1024, private=True))
    except FileNotFoundError:
        return
    except (ValueError, OSError):
        raise Conflict('protected_home_state_invalid') from None
    if not isinstance(value, dict):
        raise Conflict('protected_home_state_invalid')
    if value.get('schemaVersion') == 2 or 'ha' in value:
        raise Conflict('ha_home_requires_cluster_workflow')
    if type(value.get('schemaVersion')) is not int or value['schemaVersion'] != 1:
        raise Conflict('protected_home_state_invalid')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True)
    args = parser.parse_args(argv)
    try:
        require_standalone_home(args.home)
        return 0
    except (ValueError, OSError):
        print('Setup refused: protected HA home requires its private cluster workflow; existing state preserved.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
