#!/usr/bin/env python3
"""Generate a Border Claw's scoped workspace + persona (feature 056).

Slimming a Border is NOT just trimming its MCP servers — its AGENT must also (a)
stop carrying the full ~190-skill catalog and (b) KNOW it is a Border that
DELEGATES domain work to member claws via n2n_route. Otherwise it answers like
the monolith ("I have 82 skills, here's all of CML/pyATS…") and never routes.

This builds `~/.openclaw-<risk>-border/workspace/` (or --out) containing ONLY the
broker skills (symlinked from the live workspace) + the n2n-federation skill, and
writes a Border SOUL.md / IDENTITY.md persona. Point the Border's
agents.defaults.workspace at it and restart the gateway. Support files (memory,
testbed, AGENTS.md, USER.md, TOOLS.md) are symlinked from the live workspace so
history/identity carry over; SOUL*/IDENTITY are overridden with the Border persona.

Usage:
  python3 scripts/in2n-border-workspace.py --risk johns-risk \
      --members cml,pyats,ipfabric,viz --on-demand containerlab,suzieq,... \
      [--live-workspace ~/.openclaw/workspace] [--out ~/.openclaw/workspace-border]
"""
import argparse, os, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Broker skill selection: comms + meta + light utilities stay on the Border;
# every domain skill lives in a member.
BROKER_PREFIXES = ("slack-", "webex-", "twilio-", "twitter-", "pagerduty-",
                   "servicenow-", "msgraph-")
BROKER_EXACT = {"protocol-participation", "gait-session-tracking", "memory",
                "mempalace", "humanrail-escalation", "subnet-calculator",
                "rfc-lookup", "wikipedia-research", "token-tracker", "markmap-viz",
                "n2n-federation"}
SUPPORT_FILES = ["AGENTS.md", "MEMORY.md", "USER.md", "HEARTBEAT.md", "TOOLS.md",
                 "TOOLS-REFERENCE.md", "SKILL-SCHEMA.md", "memory", "testbed"]


def _persona(risk, always_on, on_demand):
    ao = ", ".join(always_on) or "(none)"
    od = ", ".join(on_demand) or "(none)"
    return f"""# SOUL — Border Claw of the "{risk}" Risk

You are **NetClaw — the Border Claw** of the risk **{risk}**. You are NOT a
monolithic NetClaw and do NOT carry the full skill catalog. You are the
coordinator, single interface, and comms hub. Members do specialist work; you
route to them.

## You are NOT
You do NOT run CML, pyATS, IP Fabric, SuzieQ, Batfish, Forward, gTrace, packet
capture, Itential, AAP, NSO, ACI, Catalyst Center, F5, SD-WAN, ISE, Palo Alto,
FortiManager, nmap, NVD, firewall analysis, AWS/Azure/GCP, NetBox/Nautobot/
Infrahub, Infoblox, GitHub, or visualization yourself. **A member does.**

## Member claws (delegate via `n2n_route`)
- Always-on: {ao}
- On-demand (cold-start on first route): {od}

## How you handle a request (ALWAYS)
1. Comms / audit / memory / broker utility → handle yourself.
2. Otherwise DELEGATE: pick the owning member (call `n2n_member_list` if unsure),
   `n2n_route(request_text, target_hint=<capability>)`, poll `n2n_task_status` /
   `n2n_task_result`, return the member's answer. Never claim to run a domain
   skill directly, never list a flat 190-skill catalog — describe the members.

## Your own skills (broker set only)
Comms (Slack/Webex/Twilio/Twitter/PagerDuty/ServiceNow/MS Graph), memory +
MemPalace, GAIT audit, humanrail, N2N federation control (`n2n_*`), protocol/mesh,
and light utilities (subnet, RFC, Wikipedia, markmap, token-tracker).
See workspace/skills/n2n-federation/SKILL.md.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--risk", required=True)
    ap.add_argument("--members", default="", help="always-on member names, comma-sep")
    ap.add_argument("--on-demand", default="", help="on-demand member names, comma-sep")
    ap.add_argument("--live-workspace", default="~/.openclaw/workspace")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ws = os.path.expanduser(args.live_workspace)
    out = os.path.expanduser(args.out or f"~/.openclaw-{args.risk}-border/workspace")
    always_on = [x.strip() for x in args.members.split(",") if x.strip()]
    on_demand = [x.strip() for x in args.on_demand.split(",") if x.strip()]
    os.makedirs(os.path.join(out, "skills"), exist_ok=True)

    # broker skills (symlink from live) + n2n-federation (from repo if missing)
    n = 0
    skills_src = os.path.join(ws, "skills")
    for name in (os.listdir(skills_src) if os.path.isdir(skills_src) else []):
        if name.startswith(BROKER_PREFIXES) or name in BROKER_EXACT:
            src = os.path.join(skills_src, name)
            dst = os.path.join(out, "skills", name)
            if not os.path.lexists(dst):
                os.symlink(src, dst); n += 1
    nf = os.path.join(out, "skills", "n2n-federation")
    if not os.path.exists(nf):
        repo_nf = os.path.join(REPO, "workspace", "skills", "n2n-federation")
        if os.path.isdir(repo_nf):
            shutil.copytree(repo_nf, nf); n += 1

    # support/identity files symlinked; SOUL*/IDENTITY overridden with the persona
    for f in SUPPORT_FILES:
        src = os.path.join(ws, f)
        dst = os.path.join(out, f)
        if os.path.exists(src) and not os.path.lexists(dst):
            os.symlink(src, dst)
    with open(os.path.join(out, "SOUL.md"), "w") as fh:
        fh.write(_persona(args.risk, always_on, on_demand))
    with open(os.path.join(out, "IDENTITY.md"), "w") as fh:
        fh.write(f"# Border Claw · risk {args.risk}\n\nSingle interface + comms + "
                 f"router. Delegates all domain work to member claws via n2n_route. "
                 f"See SOUL.md.\n")

    print(f"Border workspace: {out}")
    print(f"  broker skills: {n}  (+ support files symlinked, SOUL/IDENTITY = Border persona)")
    print(f"  Point agents.defaults.workspace at it, then restart the gateway.")


if __name__ == "__main__":
    main()
