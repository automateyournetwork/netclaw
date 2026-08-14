#!/usr/bin/env python3
"""Push a periodic NetClaw status heartbeat to every enrolled mobile edge node.

Why this is a separate job rather than part of the agent's own heartbeat:
OpenClaw's built-in heartbeat (`agents.defaults.heartbeat`) composes an
LLM-authored summary and delivers it to the configured chat channel — Slack,
here. Two problems make it the wrong vehicle for device delivery:

  1. It depends on the model *choosing* to call `n2n_notify_phone` during the
     turn. A heartbeat you only get when the model remembers is not a
     heartbeat.
  2. Its delivery path is the Slack Web API, which has silently 403'd for
     hours at a time (see ~/.openclaw/bin/defenseclaw-slack-guard.sh). When
     that happens the agent runs fine and nothing arrives anywhere.

So this job derives its status from the daemon's own HTTP surface, formats it
deterministically, and pushes it through `/n2n/edge/push` — which delivers
live if the phone is connected, falls back to a platform push, and otherwise
queues for replay on next connect (bgp/federation/edge_queue.py). It shares no
code path with Slack, so one channel failing cannot silence the other.

Run via the netclaw-edge-heartbeat systemd timer. Safe to run by hand.
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


def _get(path: str):
    with urllib.request.urlopen(f"{DAEMON}{path}", timeout=TIMEOUT) as r:
        return json.load(r)


def _post(path: str, payload: dict):
    req = urllib.request.Request(
        f"{DAEMON}{path}", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def slack_delivery_health(window: str = "-90min") -> str:
    """Whether the *other* heartbeat channel is actually delivering.

    The expensive failure this whole file exists around is outbound-only
    breakage: the agent runs, composes a correct heartbeat, and the Slack POST
    403s — while `openclaw channels status` still reports connected/healthy
    because inbound Socket Mode is fine. Nothing retries and nothing alerts, so
    it has gone unnoticed for 7+ hours at a time.

    Since this job delivers over a completely different transport, it is the
    natural place to notice. Returns a warning line, or "" when Slack is fine.
    """
    import subprocess
    try:
        out = subprocess.run(
            ["journalctl", "--user", "-u", "openclaw-gateway",
             "--since", window, "--no-pager"],
            capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    if out.returncode != 0:
        return ""
    failed = started = 0
    for line in out.stdout.splitlines():
        if "[heartbeat] failed" in line:
            failed += 1
        elif "[heartbeat] started" in line:
            started += 1
    if failed:
        return (f"⚠ SLACK HEARTBEAT FAILING — {failed} delivery failure(s) in the "
                f"last 90min. Check: journalctl --user -u openclaw-gateway "
                f"| grep slack-guard")
    return ""


def _age(ts: float) -> str:
    if not ts:
        return "never"
    mins = (time.time() - ts) / 60
    if mins < 60:
        return f"{mins:.0f}m"
    if mins < 60 * 48:
        return f"{mins / 60:.0f}h"
    return f"{mins / 1440:.0f}d"


def compose() -> tuple:
    """Returns (summary_text, edge_nodes). Reads only the daemon's own API, so
    it reports what the daemon actually believes — not a second opinion that
    could drift from it."""
    health = _get("/n2n/health")
    faults = _get("/n2n/faults")
    posture = _get("/n2n/posture")
    members_api = _get("/n2n/members")

    peers = health.get("peers", [])
    up = [p for p in peers if p.get("channel_state") == "up"]

    # /n2n/members, not /n2n/faults, because only it carries node_type — and a
    # phone must never be counted as a downed agent member. `state == 'active'`
    # is what marks a member as one that is *supposed* to be running right now;
    # 'provisioned' members are cold by design and their being down is normal.
    all_members = members_api.get("members", members_api) or []
    if isinstance(all_members, dict):
        all_members = list(all_members.values())
    agents = [m for m in all_members if m.get("node_type") != "edge"]
    expected = [m for m in agents if m.get("state") == "active"]
    hot = expected
    hot_down = [m["member_id"] for m in expected if not m.get("live")]

    lines = [f"NetClaw {health.get('identity', '?')} — {time.strftime('%H:%M %Z')}"]
    lines.append(f"posture: {posture.get('mode')}/{posture.get('state')}"
                 + (f" missing={','.join(posture.get('missing') or [])}"
                    if posture.get("missing") else ""))
    lines.append(f"daemon: {faults.get('daemon')}  "
                 f"peers: {len(up)}/{len(peers)} up  "
                 f"hot members: {len(hot) - len(hot_down)}/{len(hot)} up")

    if up:
        lines.append("peers up: " + ", ".join(
            f"{p.get('display_name') or p['identity']}({_age(p.get('last_seen'))})"
            for p in up))
    stale = [p for p in peers
             if p.get("channel_state") != "up" and p.get("state") == "federated"
             and p.get("endpoint", ":None") not in (":None", "None:None")]
    if stale:
        lines.append("peers down: " + ", ".join(
            (p.get("display_name") or p["identity"]) for p in stale))
    if hot_down:
        lines.append("MEMBERS DOWN: " + ", ".join(sorted(hot_down)))

    cs = posture.get("channel_security") or {}
    if cs.get("red") or cs.get("renewals_failing"):
        lines.append(f"certs: red={cs.get('red')} renewals_failing="
                     f"{cs.get('renewals_failing')}")

    # Edge targets come from /n2n/members (node_type + heartbeat_age_s) enriched
    # with the queue depth from /n2n/health.
    # /n2n/members carries node_type/live/heartbeat_age_s but not the push
    # transport; /n2n/health's edge_nodes carries push_platform and the queue
    # depth. Both are needed to decide whether a device is worth pushing to.
    health_edge = {e["member_id"]: e for e in health.get("edge_nodes", [])}
    edge = []
    for m in all_members:
        if m.get("node_type") != "edge":
            continue
        he = health_edge.get(m["member_id"], {})
        edge.append({
            "member_id": m["member_id"],
            "state": m.get("state"),
            "live": bool(m.get("live")) or bool(he.get("connected")),
            "heartbeat_age_s": m.get("heartbeat_age_s"),
            "push_platform": he.get("push_platform"),
            "queued": he.get("queued", 0),
        })

    slack_warning = slack_delivery_health()
    if slack_warning:
        lines.append(slack_warning)

    for e in edge:
        if e["queued"]:
            lines.append(f"(you missed {e['queued']} earlier message(s))")
            break

    return "\n".join(lines), edge


def deliverable(e: dict, stale_after_s: int) -> bool:
    """Whether pushing to this edge node is worth doing.

    A device that is connected, or has a working platform push transport, is
    always a target. A device that has neither and has not been seen in days is
    an abandoned enrollment — re-enrolling a phone mints a NEW member_id, so
    old rows accumulate — and queueing for it would grow the backlog forever
    for something that will never connect again.
    """
    if e["live"] or e.get("push_platform"):
        return True
    age = e.get("heartbeat_age_s")
    if age is None:
        return False
    return age <= stale_after_s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="print the heartbeat instead of pushing it")
    ap.add_argument("--member", help="push to only this member_id")
    ap.add_argument("--stale-after-days", type=float, default=3.0,
                    help="skip unreachable devices unseen for longer than this "
                         "(abandoned enrollments); ignored for --member")
    ap.add_argument("--all", action="store_true",
                    help="push to every enrolled device, including stale ones")
    args = ap.parse_args()

    try:
        text, edge = compose()
    except (urllib.error.URLError, OSError) as e:
        print(f"edge-heartbeat: daemon unreachable at {DAEMON}: {e}", file=sys.stderr)
        return 1

    stale_after = int(args.stale_after_days * 86400)
    if args.member:
        targets = [e for e in edge if e["member_id"] == args.member]
    else:
        targets = [e for e in edge if args.all or deliverable(e, stale_after)]
    skipped = [e["member_id"] for e in edge if e not in targets]

    if args.dry_run:
        print(text)
        print("---")
        print(f"would push to: {[e['member_id'] for e in targets] or 'none'}")
        if skipped:
            print(f"skipped (stale/unreachable): {skipped}")
        return 0

    if not targets:
        print("edge-heartbeat: no reachable edge nodes — nothing to push"
              + (f" (skipped stale: {skipped})" if skipped else ""))
        return 0

    rc = 0
    for e in targets:
        try:
            out = _post("/n2n/edge/push", {
                "member_id": e["member_id"],
                "content_type": "text",
                "content": text,
            })
            state = ("delivered" if out.get("delivered")
                     else ("queued" if out.get("queued") else "dropped"))
            print(f"edge-heartbeat: {e['member_id']} -> {state}"
                  + (f" (via {out['via']})" if out.get("via") else "")
                  + (f" depth={out['queue_depth']}" if out.get("queue_depth") else ""))
            if state == "dropped":
                rc = 1
        except (urllib.error.URLError, OSError) as ex:
            print(f"edge-heartbeat: {e['member_id']} push failed: {ex}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
