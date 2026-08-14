#!/usr/bin/env python3
"""List and retire NetClaw Mobile edge enrollments (spec 103, FR-017).

Why this exists: re-scanning the enrollment QR mints a **new** `member_id`, so
every re-enrollment leaves the previous row behind forever. Nine such rows had
accumulated by the end of spec 103's own testing. Retiring one used to mean
either hand-writing a `curl` POST with a JSON body, or — as actually happened
on 2026-08-10 — reaching for `sqlite3` to clear the leftovers, which is exactly
what FR-017 exists to prevent.

Nothing here touches the database directly. Every mutation goes through the
daemon's `/n2n/members/remove` route, so channel teardown, key unpinning, queue
purging, and the audit trail all happen the same way they would for any other
member removal. This script only *finds* the candidates and calls that route.

  edge-enrollments.py                      # list every enrollment
  edge-enrollments.py --retire <member_id> # retire one
  edge-enrollments.py --retire-stale       # retire all unseen > 14 days
  edge-enrollments.py --retire-stale --older-than 30 --dry-run
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DAEMON = os.environ.get("N2N_DAEMON_URL", "http://127.0.0.1:8179")
TIMEOUT = 15
DEFAULT_STALE_DAYS = 14


def _get(path: str):
    with urllib.request.urlopen(f"{DAEMON}{path}", timeout=TIMEOUT) as r:
        return json.load(r)


def _post(path: str, payload: dict):
    req = urllib.request.Request(
        f"{DAEMON}{path}", method="POST", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def _age_str(seconds) -> str:
    if seconds is None:
        return "never"
    if seconds < 3600:
        return f"{seconds/60:.0f}m"
    if seconds < 86400 * 2:
        return f"{seconds/3600:.0f}h"
    return f"{seconds/86400:.0f}d"


def enrollments() -> list:
    """Every edge enrollment the daemon still knows about, newest-seen first.

    Merges the two endpoints because neither is sufficient alone: /n2n/members
    carries node_type and heartbeat_age_s but not the push transport, while
    /n2n/health's edge_nodes carries push_platform and queue depth.
    """
    members = _get("/n2n/members")
    members = members.get("members", members) or []
    if isinstance(members, dict):
        members = list(members.values())
    health = {e["member_id"]: e for e in _get("/n2n/health").get("edge_nodes", [])}

    out = []
    for m in members:
        if m.get("node_type") != "edge":
            continue
        he = health.get(m["member_id"], {})
        age = m.get("heartbeat_age_s")
        out.append({
            "member_id": m["member_id"],
            "state": m.get("state"),
            "connected": bool(m.get("live")) or bool(he.get("connected")),
            "age_s": age,
            "push_platform": he.get("push_platform"),
            "queued": he.get("queued", 0),
        })
    # Never-seen rows sort last; otherwise most-recently-seen first.
    out.sort(key=lambda e: (e["age_s"] is None, e["age_s"] or 0))
    return out


def is_stale(e: dict, stale_s: float) -> bool:
    """Abandoned = not connected now, and either never seen or not seen within
    the window. Deliberately ignores push_platform: a device can hold a valid
    push token and still be an abandoned enrollment (a re-enrolled phone leaves
    exactly that behind)."""
    if e["connected"]:
        return False
    if e["age_s"] is None:
        return True
    return e["age_s"] > stale_s


def print_table(rows: list, stale_s: float):
    if not rows:
        print("no edge enrollments")
        return
    print(f"{'MEMBER_ID':<38} {'STATE':<12} {'CONN':<5} {'LAST SEEN':<10} "
          f"{'PUSH':<6} {'QUEUED':<7} STALE")
    for e in rows:
        print(f"{e['member_id']:<38} {e['state'] or '-':<12} "
              f"{'yes' if e['connected'] else 'no':<5} {_age_str(e['age_s']):<10} "
              f"{e['push_platform'] or '-':<6} {e['queued']:<7} "
              f"{'YES' if is_stale(e, stale_s) else ''}")


def retire(member_id: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"  would retire {member_id}")
        return True
    try:
        out = _post("/n2n/members/remove", {"member_id": member_id})
    except urllib.error.HTTPError as e:
        print(f"  {member_id}: FAILED ({e.code} {e.reason})", file=sys.stderr)
        return False
    except (urllib.error.URLError, OSError) as e:
        print(f"  {member_id}: FAILED ({e})", file=sys.stderr)
        return False
    if not out.get("removed"):
        print(f"  {member_id}: not removed ({out.get('error', 'unknown')})",
              file=sys.stderr)
        return False
    purged = out.get("queued_purged", 0)
    print(f"  retired {member_id}"
          + (f" (+{purged} queued message(s) purged)" if purged else ""))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description="List and retire NetClaw Mobile edge enrollments (FR-017).")
    ap.add_argument("--retire", metavar="MEMBER_ID",
                    help="retire this enrollment")
    ap.add_argument("--retire-stale", action="store_true",
                    help="retire every enrollment unseen beyond --older-than")
    ap.add_argument("--older-than", type=float, default=DEFAULT_STALE_DAYS,
                    metavar="DAYS",
                    help=f"staleness threshold in days (default {DEFAULT_STALE_DAYS})")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be retired without doing it")
    ap.add_argument("--force", action="store_true",
                    help="retire a non-stale enrollment anyway (NOT reversible: "
                         "the pinned key is deleted and the device must re-enroll)")
    args = ap.parse_args()

    stale_s = args.older_than * 86400
    try:
        rows = enrollments()
    except (urllib.error.URLError, OSError) as e:
        print(f"edge-enrollments: daemon unreachable at {DAEMON}: {e}",
              file=sys.stderr)
        return 1

    if args.retire:
        match = [e for e in rows if e["member_id"] == args.retire]
        if not match:
            print(f"edge-enrollments: no edge enrollment {args.retire!r}",
                  file=sys.stderr)
            print_table(rows, stale_s)
            return 1
        # Retiring a live enrollment is almost never intended and is NOT
        # reversible — removal NULLs the pinned key and deletes its key file, so
        # the device must re-enroll and gets a new member_id.
        #
        # An earlier version of this guard checked only `connected`, which is
        # useless: a phone flaps constantly and reads `connected=no` most of the
        # time while being entirely live. On 2026-08-11 that let the *current*
        # phone be retired by a command expected to be refused. `--force` is now
        # required for anything that isn't demonstrably abandoned.
        if not args.dry_run and not args.force and not is_stale(match[0], stale_s):
            why = ("connected right now" if match[0]["connected"]
                   else f"last seen {_age_str(match[0]['age_s'])} ago, "
                        f"inside the {args.older_than:g}-day staleness window")
            newest = rows[0]["member_id"] if rows else None
            print(f"edge-enrollments: refusing to retire {args.retire} — "
                  f"{why}.", file=sys.stderr)
            if match[0]["member_id"] == newest:
                print(f"  This is also the MOST RECENTLY SEEN enrollment, so it "
                      f"is very likely the device you are actually using.",
                      file=sys.stderr)
            print(f"  Removal is NOT reversible: the pinned key is deleted and "
                  f"the device must re-enroll with a new member_id.\n"
                  f"  Preview with --dry-run, or pass --force if you are certain.",
                  file=sys.stderr)
            return 2
        return 0 if retire(args.retire, args.dry_run) else 1

    if args.retire_stale:
        targets = [e for e in rows if is_stale(e, stale_s)]
        if not targets:
            print(f"no enrollments unseen beyond {args.older_than:g} days — "
                  f"nothing to retire")
            return 0
        print(f"retiring {len(targets)} enrollment(s) unseen beyond "
              f"{args.older_than:g} days"
              + (" (dry run)" if args.dry_run else "") + ":")
        failures = sum(0 if retire(e["member_id"], args.dry_run) else 1
                       for e in targets)
        return 1 if failures else 0

    print_table(rows, stale_s)
    stale = [e for e in rows if is_stale(e, stale_s)]
    if stale:
        print(f"\n{len(stale)} enrollment(s) unseen beyond {args.older_than:g} "
              f"days. Retire with:  {os.path.basename(sys.argv[0])} --retire-stale")
    return 0


if __name__ == "__main__":
    sys.exit(main())
