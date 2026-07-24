#!/usr/bin/env python3
"""Provision a member's scoped OpenClaw home (feature 056).

Generalizes the recipe proven live for the ipfabric member: from the Border's
~/.openclaw/openclaw.json, build ~/.openclaw-<risk>-<member>/openclaw.json that
is SCOPED to one member:
  - mcp.servers  → filtered to the member's servers (+ memory-mcp)
  - plugins/channels → comms plugins stripped (they crash `openclaw agent --local`)
  - models.providers.anthropic → a DIRECT Anthropic provider registered at the
    member's tier model (so the member runs Claude without the DefenseClaw proxy)
  - workspace → symlinked to the Border's (identity/skills); scope is enforced by
    the member's declared N2N_MEMBER_SCOPE + the trimmed MCP set
Sets nothing live — just writes the member home. The member launcher points at it
via OPENCLAW_STATE_DIR / OPENCLAW_CONFIG_PATH.

Usage: python3 scripts/in2n-member-home.py --risk johns-risk --member ipfabric \
         [--model claude-sonnet-5] [--anthropic-key-from ~/.openclaw/.env]
"""
import argparse, copy, importlib.util, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
COMMS_PLUGINS = {"slack", "webex", "discord", "twilio", "twitter", "msteams"}


def _profiles():
    spec = importlib.util.spec_from_file_location(
        "in2n_profiles", os.path.join(REPO, "scripts", "in2n-profiles.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _anthropic_key(env_path):
    try:
        for line in open(os.path.expanduser(env_path)):
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--risk", required=True)
    ap.add_argument("--member", required=True, help="profile/member name, e.g. ipfabric")
    ap.add_argument("--model", default=None, help="override model (default: profile tier)")
    ap.add_argument("--anthropic-key-from", default="~/.openclaw/.env")
    ap.add_argument("--border-config", default=f"{HOME}/.openclaw/openclaw.json")
    args = ap.parse_args()

    prof = _profiles()
    name = args.member
    model = args.model or prof.model_tier(name)
    keep = set(prof.MCP_SERVERS.get(name, [])) | {"memory-mcp"}
    border = json.load(open(args.border_config))
    m = copy.deepcopy(border)

    # 1. scope MCP servers and expand ${NETCLAW_DIR} (member .env may not export it;
    #    unexpanded paths make every MCP fail with EPIPE / not found).
    netclaw_dir = os.environ.get("NETCLAW_DIR") or REPO
    all_servers = border.get("mcp", {}).get("servers", {})

    def _expand(obj):
        if isinstance(obj, str):
            return obj.replace("${NETCLAW_DIR}", netclaw_dir).replace(
                "${HOME}", HOME
            )
        if isinstance(obj, list):
            return [_expand(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _expand(v) for k, v in obj.items()}
        return obj

    m.setdefault("mcp", {})["servers"] = {
        k: _expand(v) for k, v in all_servers.items() if k in keep
    }

    # 2. strip comms plugins/channels that break --local; keep defenseclaw (guardrails)
    pl = m.get("plugins", {})
    if isinstance(pl, dict):
        for sub in ("entries", "load"):
            if isinstance(pl.get(sub), dict):
                pl[sub] = {k: v for k, v in pl[sub].items() if k not in COMMS_PLUGINS}
        if isinstance(pl.get("allow"), list):
            pl["allow"] = [x for x in pl["allow"]
                           if not any(c in str(x).lower() for c in COMMS_PLUGINS)]
    m["channels"] = {}

    # 3. Register the member's model provider + whitelist it for agent "main".
    #    Supports anthropic/* (default tier) and ollama/* (N2N_MEMBER_MODEL).
    #    Agent rejects a --model override that isn't in agents.defaults.models.
    allow = m.setdefault("agents", {}).setdefault("defaults", {}).setdefault("models", {})
    if model.startswith("ollama/") or "/" not in model and "claude" not in model:
        # Prefer Border's existing ollama provider block (baseUrl + apiKey).
        ollama_model = model if model.startswith("ollama/") else f"ollama/{model}"
        border_ollama = (
            border.get("models", {}).get("providers", {}).get("ollama")
            or {}
        )
        m.setdefault("models", {}).setdefault("providers", {})["ollama"] = border_ollama or {
            "baseUrl": os.environ.get("OLLAMA_BASE_URL", "https://ollama.com"),
            "apiKey": os.environ.get("OLLAMA_API_KEY", ""),
            "api": "ollama",
        }
        allow.setdefault(ollama_model, {"alias": "member"})
        model = ollama_model
    else:
        key = _anthropic_key(args.anthropic_key_from)
        anthropic_id = model.split("/", 1)[-1] if model.startswith("anthropic/") else model
        m.setdefault("models", {}).setdefault("providers", {})["anthropic"] = {
            "baseUrl": "https://api.anthropic.com", "apiKey": key, "api": "anthropic-messages",
            "models": [{"id": anthropic_id, "name": anthropic_id, "reasoning": False,
                        "input": ["text", "image"], "contextWindow": 200000, "maxTokens": 64000}],
        }
        allow.setdefault(f"anthropic/{anthropic_id}", {"alias": "member"})
        model = f"anthropic/{anthropic_id}" if not model.startswith("anthropic/") else model

    # 4. write the scoped home + share the workspace (identity/skills) via symlink
    mh = f"{HOME}/.openclaw-{args.risk}-{name}"
    os.makedirs(mh, exist_ok=True)
    json.dump(m, open(f"{mh}/openclaw.json", "w"), indent=2)
    os.chmod(f"{mh}/openclaw.json", 0o600)
    ws = f"{mh}/workspace"
    if not os.path.exists(ws):
        os.symlink(f"{HOME}/.openclaw/workspace", ws)

    print(f"scoped home: {mh}")
    print(f"  mcp.servers: {list(m['mcp']['servers'].keys())}")
    print(f"  model: {model}")
    print(f"  OPENCLAW_STATE_DIR={mh}")
    print(f"  OPENCLAW_CONFIG_PATH={mh}/openclaw.json")
    print(f"  N2N_MEMBER_MODEL={model}")


if __name__ == "__main__":
    main()
