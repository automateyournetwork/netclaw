#!/usr/bin/env python3
"""iN2N migration scaffold generator — GENERATE-ONLY, never touches the live claw.

Decomposes a monolithic NetClaw into a "risk": a Border + one scoped member per
configured integration. It ONLY *generates* into a staging directory and prints a
cutover runbook — it does NOT stop, start, remove, or reconfigure anything. You
read the output, then run the runbook by hand (parallel cutover).

For each offered member profile (env-gated, from in2n-profiles.py) it writes:
  <staging>/members/<name>/.env      — the member's LEAST-PRIVILEGE env slice
                                        (its integration keys + memory/gait/humanrail
                                        + iN2N member vars + a model line to fill in)
  <staging>/members/<name>/run.sh    — the launch command (in2n-member.py)
And a top-level:
  <staging>/border.env.additions     — the N2N_ROLE=border lines to add to ~/.openclaw/.env
  <staging>/RUNBOOK.md               — the step-by-step parallel-cutover runbook

NOTE: this is ALSO the shape a FRESH install produces per member — migration just
pre-fills the .env slice from an existing monolith; a fresh member fills it in via
the installer. Same runtime (scripts/in2n-member.py), same enrollment.

Usage:
  python3 scripts/in2n-migrate.py --risk johns-risk --border-endpoint 127.0.0.1:11790 \
      [--staging ./migration-staging] [--hot cml,pyats,ipfabric,viz] [--live-env ~/.openclaw/.env]
"""

import argparse
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_profiles():
    path = os.path.join(REPO, "scripts", "in2n-profiles.py")
    spec = importlib.util.spec_from_file_location("in2n_profiles", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_env(path):
    """Return {KEY: raw_line} for a .env file (values kept verbatim, never printed)."""
    out = {}
    try:
        with open(os.path.expanduser(path)) as fh:
            for line in fh:
                s = line.rstrip("\n")
                if s.strip() and not s.strip().startswith("#") and "=" in s:
                    out[s.split("=", 1)[0].strip()] = s
    except OSError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser(description="iN2N migration scaffold (generate-only)")
    ap.add_argument("--risk", default="johns-risk")
    ap.add_argument("--border-endpoint", default="127.0.0.1:11790")
    ap.add_argument("--staging", default=os.path.join(REPO, "migration-staging"))
    ap.add_argument("--hot", default="cml,pyats,ipfabric,viz",
                    help="comma-separated always-on members; the rest are cold/on-demand")
    ap.add_argument("--idle-exit", type=int, default=900,
                    help="idle seconds before a cold/on-demand member exits")
    ap.add_argument("--live-env", default="~/.openclaw/.env")
    args = ap.parse_args()

    prof = _load_profiles()
    offered = prof.profiles()                      # env-gated: only configured members
    live_env = _read_env(args.live_env)
    hot = {h.strip() for h in args.hot.split(",") if h.strip()}
    staging = os.path.abspath(args.staging)
    members_dir = os.path.join(staging, "members")
    os.makedirs(members_dir, exist_ok=True)

    summary = []
    for name, info in offered.items():
        mdir = os.path.join(members_dir, name)
        os.makedirs(mdir, exist_ok=True)
        member_id = f"{args.risk}/{name}"
        always_on = name in hot
        # least-privilege env slice (KEYS only listed here; VALUES copied verbatim)
        slice_keys = prof.env_slice_keys(name, set(live_env.keys()))
        env_lines = [live_env[k] for k in slice_keys]
        # iN2N member config
        member_cfg = [
            "# ── iN2N member config (feature 056) ──",
            "N2N_ROLE=member",
            f"N2N_RISK_NAME={args.risk}",
            f"N2N_MEMBER_ID={member_id}",
            f"N2N_BORDER_ENDPOINT={args.border_endpoint}",
            f"N2N_MEMBER_BASE={os.path.join(mdir, 'n2n')}",
            # Point the member's OpenClaw runtime at the scoped home that
            # scripts/in2n-member-home.py builds (~/.openclaw-<risk>-<member>/openclaw.json).
            # openclaw agent --local honors OPENCLAW_CONFIG_PATH / OPENCLAW_STATE_DIR from
            # the env (verified: OPENCLAW_PROFILE as an env var is ignored — only the
            # --profile flag takes it). in2n-member.py loads this .env into os.environ and
            # gateway.py spawns `openclaw agent --local` inheriting that env, so without
            # these two vars the member silently loads the default ~/.openclaw home
            # (scope not enforced). Path is absolute (expanduser) because the .env loader
            # uses os.environ.setdefault with the raw string (no shell ~ expansion).
            f"OPENCLAW_CONFIG_PATH={os.path.expanduser('~/.openclaw-' + args.risk + '-' + name)}/openclaw.json",
            f"OPENCLAW_STATE_DIR={os.path.expanduser('~/.openclaw-' + args.risk + '-' + name)}",
            f"N2N_MEMBER_SCOPE={_scope_json(info['skills'])}",
            "# Pick THIS member's provider/model (any provider incl local/Ollama):",
            "N2N_MEMBER_MODEL=anthropic/claude-sonnet-5   # <-- edit per member",
            "# ANTHROPIC_API_KEY / OPENAI_API_KEY / OLLAMA_HOST as needed for the model above",
            "# N2N_ENROLLMENT_TOKEN=<paste from: netclaw risk add …>   # first run only",
        ]
        with open(os.path.join(mdir, ".env"), "w") as fh:
            fh.write("# Least-privilege .env slice for member %s (generated).\n" % member_id)
            fh.write("# Integration + base-floor (memory/gait/humanrail) keys only.\n\n")
            fh.write("\n".join(env_lines) + ("\n\n" if env_lines else "\n"))
            fh.write("\n".join(member_cfg) + "\n")
        idle = 0 if always_on else args.idle_exit
        with open(os.path.join(mdir, "run.sh"), "w") as fh:
            fh.write("#!/usr/bin/env bash\n")
            fh.write("# Robust: the launcher parses the .env itself (values may contain\n")
            fh.write("# spaces/colons/JSON) — no fragile shell sourcing.\n")
            fh.write('export N2N_MEMBER_ENV_FILE="$(dirname "$0")/.env"\n')
            fh.write(f"exec python3 {REPO}/scripts/in2n-member.py --idle-exit {idle}\n")
        os.chmod(os.path.join(mdir, "run.sh"), 0o755)
        summary.append((name, member_id, "always-on" if always_on else "on-demand",
                        len(info["skills"]), len(slice_keys)))

    # Border additions (role only — comms secrets stay in ~/.openclaw/.env)
    with open(os.path.join(staging, "border.env.additions"), "w") as fh:
        fh.write("\n".join([
            "# Append to ~/.openclaw/.env to promote this claw to Border (additive).",
            "# (values must be clean — no inline comments; .env loaders keep them literally)",
            "N2N_ROLE=border", f"N2N_RISK_NAME={args.risk}",
            "N2N_ENABLED_STACKS=both", "N2N_IN2N_PORT=11790",
            "# N2N_RISK_MODE=production -> DefenseClaw + OpenShell enforced",
            "N2N_RISK_MODE=production",
        ]) + "\n")

    _write_runbook(staging, args, summary)
    _print_summary(staging, summary)


def _scope_json(skills):
    import json
    from_base = [
        {"name": "n2n-member-runtime", "type": "skill", "tier": "base"},
        {"name": "self-status", "type": "skill", "tier": "base"},
        {"name": "memory", "type": "skill", "tier": "base"},
        {"name": "gait-session-tracking", "type": "skill", "tier": "base"},
        {"name": "humanrail-escalation", "type": "skill", "tier": "base"},
    ]
    spec = [{"name": s, "type": "skill", "tier": "specialty"} for s in skills]
    # N2N_MEMBER_SCOPE is a flat list of capability names the member will run
    return json.dumps([e["name"] for e in from_base + spec])


def _write_runbook(staging, args, summary):
    hot = [s for s in summary if s[2] == "always-on"]
    cold = [s for s in summary if s[2] == "on-demand"]
    lines = [
        f"# iN2N migration runbook — {args.risk} (parallel cutover)",
        "",
        "**GENERATED — read before running. Nothing here has touched your live claw.**",
        "",
        "## 0. Backup (do first, always)",
        "```bash",
        "tar czf ~/netclaw-backup-$(date +%Y%m%d-%H%M).tgz ~/.openclaw",
        "cd " + REPO + " && git status   # confirm branch 056, work committed",
        "```",
        "",
        "## 1. Tell Slack (affects Nick/Byrn's mesh during the daemon restart)",
        "Post the heads-up (draft separately) BEFORE step 3.",
        "",
        "## 2. Promote this claw to Border (additive — keeps running)",
        "Append `border.env.additions` to `~/.openclaw/.env`, then restart the mesh daemon.",
        "eN2N mesh (AS65001/4.4.4.4) reconnects to Nick/Byrn automatically (053 supervisor).",
        "```bash",
        "cat " + os.path.join(staging, "border.env.additions") + " >> ~/.openclaw/.env",
        "# restart the mesh daemon (however you run it) — role=border starts the iN2N listener",
        "netclaw risk status   # expect role=border, risk=" + args.risk,
        "```",
        "",
        "## 3. Bring up the HOT SET (always-on) — one at a time, verify each",
        "For each hot member: issue its token, drop it into the member's .env, launch, route a real task.",
        "```bash",
    ]
    api = "127.0.0.1:8179"
    for name, mid, _mode, _sk, _ek in hot:
        run = os.path.join(staging, 'members', name, 'run.sh')
        env = os.path.join(staging, 'members', name, '.env')
        lines += [
            f"# --- {mid}  (always-on) ---",
            f"curl -s -XPOST {api}/n2n/members/add -H 'Content-Type: application/json' \\",
            f"  -d '{{\"name\":\"{name}\",\"profile\":\"{name}\",\"launch_cmd\":\"bash {run}\",\"on_demand\":false}}'",
            f"#   -> paste enrollment_token into {env} (N2N_ENROLLMENT_TOKEN=) + set N2N_MEMBER_MODEL",
            f"bash {run} &                             # persistent (idle-exit 0); dials + enrolls",
            f"netclaw risk members                     # expect {mid} live",
            f"netclaw risk route \"<a real {name} task>\" <capability>",
        ]
    lines += ["```", "",
              "## 4. Register the COLD / on-demand members (the rest) — do NOT launch them",
              "Register each with on_demand=true + its launch_cmd. The Border cold-starts it",
              "automatically on the first route and it idle-exits after "
              + str(args.idle_exit) + "s of quiet. Verify by routing a real task and watching it spin up.",
              "```bash"]
    for name, mid, _mode, _sk, _ek in cold:
        run = os.path.join(staging, 'members', name, 'run.sh')
        env = os.path.join(staging, 'members', name, '.env')
        lines += [
            f"curl -s -XPOST {api}/n2n/members/add -H 'Content-Type: application/json' \\",
            f"  -d '{{\"name\":\"{name}\",\"profile\":\"{name}\",\"launch_cmd\":\"bash {run}\",\"on_demand\":true}}'",
            f"#   -> paste token + model into {env}   ({mid}: Border cold-starts on route)",
        ]
    lines += ["# test a cold member end-to-end (Border spawns it, waits, delegates):",
              "#   netclaw risk route \"<task for a cold member>\" <capability>",
              "```", "",
              "## 4b. Slim the Border INCREMENTALLY (no capability gap)",
              "The Border stays fat through promotion so nothing breaks. Shed each domain",
              "ONLY AFTER its member is proven in step 3/4 — never a moment where a capability",
              "is unavailable. After a member handles its tasks, remove that domain's skills +",
              "MCP servers from the Border's ~/.openclaw (workspace/skills + openclaw.json),",
              "then `openclaw mcp reload`. End state — the Border keeps ONLY the broker set:",
              "```",
              "comms:      slack* webex* twilio* twitter* pagerduty* servicenow* discord*",
              "broker/meta: n2n-federation protocol-participation gait-session-tracking",
              "             memory mempalace humanrail-escalation",
              "utilities:  subnet-calculator rfc-lookup wikipedia-research token-tracker",
              "```",
              "Everything else (all member domains) is REMOVED from the Border — it now routes",
              "to the member instead. Target: ~25 skills on the Border, down from ~190.", "",
              "## 5. Move comms to the Border / decommission the monolith LAST",
              "Once members are proven, the Border is your single door. Keep the backup.",
              "The monolith is retired last — never a gap where Slack/mesh is dark.",
              "",
              "## Rollback",
              "Remove the border.env.additions lines, restart the daemon (back to standalone),",
              "stop the member run.sh processes. Your backup restores everything.",
              ""]
    with open(os.path.join(staging, "RUNBOOK.md"), "w") as fh:
        fh.write("\n".join(lines))


def _print_summary(staging, summary):
    print(f"Generated iN2N migration scaffold → {staging}  (GENERATE-ONLY, nothing deployed)")
    print(f"  {len(summary)} member scaffolds + border.env.additions + RUNBOOK.md\n")
    print(f"  {'member':16s} {'mode':10s} {'skills':>6s} {'env-keys':>8s}")
    for name, mid, mode, sk, ek in summary:
        print(f"  {name:16s} {mode:10s} {sk:6d} {ek:8d}")
    print(f"\n  Read the runbook:  {os.path.join(staging, 'RUNBOOK.md')}")
    print("  NOTHING has touched your live claw. Review, then run the runbook by hand.")


if __name__ == "__main__":
    main()
