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
import argparse, copy, importlib.util, json, os, sys, re, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp-servers/protocol-mcp'))
from bgp.federation.runtime import selected, private_dir

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


def provision_hermes(runtime, risk, member, destination=None, model=None):
    if not all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', x) for x in (risk,member)):
        raise ValueError('risk/member must be safe local names')
    if member != 'subnet':raise ValueError('Hermes currently qualifies only the subnet member profile')
    import yaml
    home=Path(destination or runtime.home/'members'/risk/member/'home').resolve()
    private_dir(home)
    if (home/'config.yaml').exists():raise ValueError('member already provisioned; existing config is preserved')
    source=yaml.safe_load(runtime.config.read_text()) if runtime.kind=='hermes' else json.loads(runtime.config.read_text())
    servers=source.get('mcp_servers',{}) if runtime.kind=='hermes' else (source.get('mcp') or {}).get('servers',{})
    if 'subnet-calc-mcp' not in servers:raise ValueError('qualified subnet registration is required')
    config={'model':copy.deepcopy(source.get('model') or {}),'mcp_servers':{'subnet-calc-mcp':copy.deepcopy(servers['subnet-calc-mcp'])}}
    if runtime.kind!='hermes':
        if not model:raise ValueError('mixed OpenClaw Border provisioning requires an explicit Hermes model')
        config['model']={'default':model}
    elif model:config['model']['default']=model
    registration=config['mcp_servers']['subnet-calc-mcp']
    registration['env']={'NETCLAW_RUNTIME_ROOT':str(home/'python-runtimes'),'NETCLAW_RUNTIME_ENV':str(home/'.env')}
    records=private_dir(home/'python-runtimes/records')
    for name in ('hermes-hud','n2n','subnet-calc'):
        source_record=runtime.home/'python-runtimes/records'/name
        if not source_record.exists():raise ValueError('install '+name+' in the selected Border before provisioning')
        target=records/name;target.write_text(source_record.read_text());target.chmod(0o600)
    # Share immutable reviewed executables, never the Border's config/history.
    agent_base=runtime.home/'python-runtimes/hermes-hud-agent'
    for name,value in [('hermes-hud-agent-python',agent_base/'venv/bin/python'),('hermes-hud-agent-source',agent_base/'source')]:
        file=records/name;file.write_text(str(value)+'\n');file.chmod(0o600)
    skills=private_dir(home/'skills/subnet-calculator')
    shutil.copyfile(Path(REPO)/'workspace/skills/subnet-calculator/SKILL.md',skills/'SKILL.md')
    file=home/'config.yaml';file.write_text(json.dumps(config,indent=2)+'\n');file.chmod(0o600)
    spec=importlib.util.spec_from_file_location('literal_env',Path(REPO)/'scripts/write-env.py')
    writer=importlib.util.module_from_spec(spec);spec.loader.exec_module(writer)
    values=writer.values(runtime.env_file.read_text()) if runtime.env_file.exists() else {}
    provider_keys={'OPENAI_API_KEY','OPENAI_BASE_URL','ANTHROPIC_API_KEY','ANTHROPIC_BASE_URL','OPENROUTER_API_KEY'}
    values={k:v for k,v in values.items() if k in provider_keys}
    values.update(NETCLAW_RUNTIME='hermes',HERMES_HOME=str(home),N2N_ROLE='member',N2N_RISK_NAME=risk,
        N2N_MEMBER_ID=risk+'/'+member,N2N_MEMBER_SCOPE='["subnet-calculator"]',N2N_MEMBER_BASE=str(home/'n2n'))
    envfile=home/'.env';envfile.write_text(''.join(k+'='+json.dumps(v)+'\n' for k,v in values.items()));envfile.chmod(0o600)
    return home


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--risk", required=True)
    ap.add_argument("--member", required=True, help="profile/member name, e.g. ipfabric")
    ap.add_argument("--runtime", choices=["hermes","openclaw"], default=None)
    ap.add_argument("--home", default=None)
    ap.add_argument("--model", default=None, help="override model (default: profile tier)")
    ap.add_argument("--anthropic-key-from", default=None)
    ap.add_argument("--border-config", default=None)
    args = ap.parse_args()

    runtime=selected()
    if (args.runtime or runtime.kind)=='hermes':
        home=provision_hermes(runtime,args.risk,args.member,args.home,args.model)
        print('Scoped Hermes member home:',home)
        print('Set N2N_BORDER_ENDPOINT and the one-use enrollment token in its private .env; launch with N2N_MEMBER_ENV_FILE.')
        return
    if not all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', value) for value in (args.risk,args.member)):
        raise ValueError('risk/member must be safe local names')
    if runtime.kind=='hermes' and not args.border_config:
        raise ValueError('an OpenClaw member requires --border-config pointing at its reviewed OpenClaw template')
    args.border_config=args.border_config or str(runtime.config)
    args.anthropic_key_from=args.anthropic_key_from or str(runtime.env_file)
    prof = _profiles()
    name = args.member
    model = args.model or prof.model_tier(name)
    keep = set(prof.MCP_SERVERS.get(name, [])) | {"memory-mcp"}
    border = json.load(open(args.border_config))
    m = copy.deepcopy(border)

    # 1. scope MCP servers
    all_servers = border.get("mcp", {}).get("servers", {})
    m.setdefault("mcp", {})["servers"] = {k: v for k, v in all_servers.items() if k in keep}

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

    # 3. register a DIRECT Anthropic provider at the member's tier model, AND
    #    whitelist that model for agent "main" (agents.defaults.models) — the
    #    agent rejects a --model override that isn't in its allow-list.
    key = _anthropic_key(args.anthropic_key_from)
    m.setdefault("models", {}).setdefault("providers", {})["anthropic"] = {
        "baseUrl": "https://api.anthropic.com", "apiKey": key, "api": "anthropic-messages",
        "models": [{"id": model, "name": model, "reasoning": False,
                    "input": ["text", "image"], "contextWindow": 200000, "maxTokens": 64000}],
    }
    allow = m.setdefault("agents", {}).setdefault("defaults", {}).setdefault("models", {})
    allow.setdefault(f"anthropic/{model}", {"alias": "member"})

    # 4. write the scoped home + share the workspace (identity/skills) via symlink
    mh = str(Path(args.home or f"{HOME}/.openclaw-{args.risk}-{name}").expanduser().absolute())
    private_dir(mh)
    if (Path(mh)/'openclaw.json').exists():raise ValueError('member already provisioned; existing config is preserved')
    json.dump(m, open(f"{mh}/openclaw.json", "w"), indent=2)
    os.chmod(f"{mh}/openclaw.json", 0o600)
    ws = f"{mh}/workspace"
    if not os.path.exists(ws):
        os.symlink(str(Path(args.border_config).expanduser().resolve().parent/"workspace"), ws)

    print(f"scoped home: {mh}")
    print(f"  mcp.servers: {list(m['mcp']['servers'].keys())}")
    print(f"  model: {model}  (anthropic key: {'present' if key else 'MISSING'})")
    print(f"  OPENCLAW_STATE_DIR={mh}")
    print(f"  OPENCLAW_CONFIG_PATH={mh}/openclaw.json")
    print(f"  N2N_MEMBER_MODEL={model}")


if __name__ == "__main__":
    main()
