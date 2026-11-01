#!/usr/bin/env python3
"""iN2N on-demand member launcher for the confined system cold-start template
(spec 166).

`netclaw-coldmember@.service` (installed by `in2n-services.py coldstart install`)
runs this as `in2n-coldstart.py %i`, as the operator, under the spec 165 system
hardening. The polkit rule lets the operator start any instance name matching the
template, so the instance name is treated as untrusted input: it only SELECTS a
member, and only a registered, local, on-demand member's own launch command (from
the Risk registry) is ever executed — no shell, nothing taken from the unit name.

Usage:
  in2n-coldstart.py probe        # reserved authorization probe: exit 0, touches nothing
  in2n-coldstart.py <slug>       # exec the on-demand member whose slug is <slug>
                                 # (slug = member_id with '/' replaced by '-')

Exit codes: 0 probe; 2 invalid instance name; 3 no such cold-startable member
(nothing was run). Otherwise the process becomes the member (os.execvp).
"""

import os
import re
import shlex
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "mcp-servers", "protocol-mcp"))

PROBE = "probe"
# Same character set as the polkit rule's unit pattern (systemd instance names).
_INSTANCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_BASE_ENV = "NETCLAW_COLDSTART_BASE_DIR"


def _slug(member_id: str) -> str:
    return member_id.replace("/", "-")


def _base_dir() -> str:
    """The Risk registry directory: pinned by the template, else as in2n-services."""
    base = os.environ.get(_BASE_ENV) or os.environ.get("N2N_BASE_DIR")
    if not base:
        from bgp.federation.runtime import selected
        base = str(selected().base)
    return os.path.expanduser(base)


def _resolve(instance: str):
    """(member_id, launch_cmd) of the cold-startable member with this slug, or
    (None, reason). Opens the Border's registry read-only: the confined launcher
    never migrates or writes it."""
    import sqlite3
    from bgp.federation.router import _ROUTABLE_STATES
    db = os.path.join(_base_dir(), "federation.db")
    if not os.path.isfile(db):
        return None, "no Risk registry"
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        members = [dict(r) for r in conn.execute(
            "SELECT member_id, on_demand, managed_by, launch_cmd, state FROM member")]
    finally:
        conn.close()
    matches = [m for m in members if _slug(m.get("member_id") or "") == instance]
    if not matches:
        return None, "no registered member"
    if len(matches) > 1:
        # '/' and '-' both map to '-': never guess between colliding members.
        return None, "ambiguous: " + ", ".join(sorted(m["member_id"] for m in matches))
    m = matches[0]
    if not m.get("on_demand"):
        return None, f"{m['member_id']} is not an on-demand member"
    if m.get("managed_by") == "service":
        # Single owner (feature 057): its durable unit runs it, never a cold start.
        return None, f"{m['member_id']} is owned by a durable service unit"
    if not m.get("launch_cmd"):
        return None, f"{m['member_id']} has no local launch command"
    if m.get("state") not in _ROUTABLE_STATES:
        return None, f"{m['member_id']} is not routable (state {m.get('state')})"
    return m["member_id"], m["launch_cmd"]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: in2n-coldstart.py <instance>", file=sys.stderr)
        return 2
    instance = argv[0]
    if instance == PROBE:
        return 0          # reserved: proves the polkit authorization, runs nothing
    if not _INSTANCE.fullmatch(instance):
        print("in2n-coldstart: invalid instance name", file=sys.stderr)
        return 2
    member_id, launch_cmd = _resolve(instance)
    if member_id is None:
        print(f"in2n-coldstart: refusing {instance!r}: {launch_cmd}", file=sys.stderr)
        return 3
    args = shlex.split(launch_cmd)
    if not args:
        print(f"in2n-coldstart: refusing {instance!r}: empty launch command", file=sys.stderr)
        return 3
    if args[0] == "bash":
        # As in2n-services' member units: launch_cmd is typically `bash <run.sh>`.
        args[0] = shutil.which("bash") or "/bin/bash"
    os.environ.pop(_BASE_ENV, None)   # the launcher's, not the member's
    print(f"in2n-coldstart: starting {member_id}", file=sys.stderr, flush=True)
    os.execvp(args[0], args)
    return 1   # not reached (execvp raises on failure)


if __name__ == "__main__":
    sys.exit(main())
