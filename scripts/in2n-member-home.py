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
import ipaddress
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp-servers/protocol-mcp'))
from bgp.federation.runtime import selected, private_dir
sys.path.insert(0, str(Path(__file__).resolve().parent/'lib'))
from convergence_member_policy import native_tool_policy
from ha_setup_guard import require_standalone_home

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
COMMS_PLUGINS = {"slack", "webex", "discord", "twilio", "twitter", "msteams"}


def _profiles():
    spec = importlib.util.spec_from_file_location(
        "in2n_profiles", os.path.join(REPO, "scripts", "in2n-profiles.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


RUNTIME_PATH_KEYS = ("NETCLAW_RUNTIME_ROOT", "NETCLAW_RUNTIME_ENV")


def _launched_component(entry):
    """The component a scripts/component-launch.py entry starts, else None."""
    args = [str(a) for a in (entry.get("args") or [])] if isinstance(entry, dict) else []
    for i, arg in enumerate(args[:-1]):
        if Path(arg).name == "component-launch.py":
            return args[i + 1]
    return None


def scoped_mcp_servers(servers, member, prof=None, home=None, member_env=None, border_root=None):
    """The Border's mcp.servers entries a member of profile `member` keeps: its
    MCP_SERVERS list plus memory-mcp. Servers the Border lacks are skipped.

    With `home`, an entry that selects a runtime (NETCLAW_RUNTIME_ROOT/ENV, which
    install-mcp-config.py writes for scripts/component-launch.py entries) is
    rewritten to the member's own: component-launch.py loads every key of
    NETCLAW_RUNTIME_ENV, so the Border's would hand the member the whole Border .env.
    pyATS keeps the Border's pyats-venv (an executable, like GAIT_VENV), from the
    entry's own NETCLAW_RUNTIME_ROOT or else `border_root`. Its change root follows
    the member's runtime root (<home>/netclaw-changes); see spec 182 research.md."""
    kept = copy.deepcopy((prof or _profiles()).member_servers(member, servers))
    if home is None:
        return kept
    home = Path(home)
    for entry in kept.values():
        if not isinstance(entry, dict):
            continue
        env = entry.get("env") if isinstance(entry.get("env"), dict) else None
        component = _launched_component(entry)
        if component is None and not (env and any(k in env for k in RUNTIME_PATH_KEYS)):
            continue
        env = entry.setdefault("env", {}) if env is None else env
        root = env.get("NETCLAW_RUNTIME_ROOT") or border_root
        if component == "pyats" and root and "PYATS_VENV" not in env:
            env["PYATS_VENV"] = str(Path(root).parent / "pyats-venv")
        env["NETCLAW_RUNTIME_ROOT"] = str(home / "python-runtimes")
        env["NETCLAW_RUNTIME_ENV"] = str(_member_path(member_env) if member_env else home / ".env")
    return kept


def copy_runtime_records(servers, home, border_root):
    """Give the member the interpreter records its component-launch entries need
    (paths to the Border's installed interpreters; shared executables, no config)."""
    copied = []
    for entry in servers.values():
        component = _launched_component(entry)
        if not component or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", component):
            continue
        source = Path(border_root) / "records" / component
        if source.is_file() and not source.is_symlink():
            records = private_dir(private_dir(Path(home) / "python-runtimes") / "records")
            target = records / component
            if target.is_symlink():
                raise ValueError("member runtime record must not be a symlink: " + str(target))
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(source.read_text())
            copied.append(component)
    return copied


def member_home_command(risk, member, member_env):
    """The exact provisioning command for a staged member (printed by in2n-migrate.py)."""
    import shlex
    return " ".join(shlex.quote(x) for x in (
        "python3", str(Path(REPO) / "scripts/in2n-member-home.py"), "--runtime", "openclaw",
        "--risk", risk, "--member", member, "--member-env", str(member_env)))


def _member_path(value):
    """Absolute, with `..` collapsed lexically; symlinks are NOT followed, so a
    symlinked member env file is still seen (and refused) as one."""
    return Path(os.path.abspath(os.path.expanduser(str(value))))


def _same_path(a, b):
    """True when a and b name the same file or directory (samefile, else resolved paths)."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return Path(a).expanduser().resolve() == Path(b).expanduser().resolve()


def _refuse_border_home(home, border_homes):
    """A member home must never be the Border's own home."""
    for border in border_homes:
        if _same_path(home, border):
            raise SystemExit(f"error: member home {home} is the Border's home ({border}); "
                             "choose a separate --home for the member.")


def _require_member_env(servers, home, member_env, member, border_envs=()):
    """Fail closed: a server that loads NETCLAW_RUNTIME_ENV must have the member's own
    file: present, a regular file, not a symlink, and never the Border's .env."""
    loaders = sorted(k for k, e in servers.items()
                     if isinstance(e, dict) and isinstance(e.get("env"), dict) and e["env"].get("NETCLAW_RUNTIME_ENV"))
    target = _member_path(member_env) if member_env else Path(home) / ".env"
    if not loaders:
        return
    hint = (f"Pass --member-env with this member's private .env, e.g. the slice in2n-migrate.py "
            f"staged as <staging>/members/{member}/.env; in2n-migrate.py prints the exact command.")
    if target.is_symlink() or not target.is_file():
        raise SystemExit(f"error: {', '.join(loaders)} load their settings from {target}, which does "
                         f"not exist (or is not a regular file). {hint}")
    for border_env in border_envs:
        if _same_path(target, border_env):
            raise SystemExit(f"error: {', '.join(loaders)} would load {target}, the Border's .env "
                             f"({border_env}); component-launch.py loads every key of it. {hint}")


def _anthropic_key(env_path):
    try:
        for line in open(os.path.expanduser(env_path)):
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def provision_hermes(runtime, risk, member, destination=None, model=None):
    require_standalone_home(runtime.home)
    if not all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', x) for x in (risk,member)):
        raise ValueError('risk/member must be safe local names')
    if member != 'subnet':raise ValueError('Hermes currently qualifies only the subnet member profile')
    import yaml
    home=Path(destination or runtime.home/'members'/risk/member/'home').resolve()
    require_standalone_home(home)
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


def _convergence_provider(source, values, model=None):
    """Copy one declared provider/model; never inspect an auth vault or OAuth state."""
    defaults = (source.get('agents') or {}).get('defaults') or {}
    binding = model or defaults.get('model')
    if isinstance(binding, dict):
        binding = binding.get('primary')
    if not isinstance(binding, str):
        raise ValueError('select an explicit provider/model for the Convergence member')
    if '/' not in binding:
        binding = 'anthropic/'+binding
    provider, model_id = binding.split('/', 1)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', provider) or not model_id or len(model_id)>200:
        raise ValueError('invalid member provider/model binding')
    declared = (source.get('models') or {}).get('providers', {}).get(provider)
    if declared is None and provider == 'anthropic':
        declared = {'api': 'anthropic-messages', 'apiKey': '${ANTHROPIC_API_KEY}'}
    if not isinstance(declared, dict) or declared.get('headers'):
        raise ValueError('declare a supported member provider explicitly; vault/OAuth or custom headers require separate setup')
    models = None
    if 'models' in declared:
        if not isinstance(declared['models'], list):
            raise ValueError('provider models must be a list')
        models = [item for item in declared['models'] if isinstance(item, dict) and item.get('id') == model_id]
        if len(models) != 1:
            raise ValueError('selected member model must have one explicit provider model declaration')
    elif provider not in ('anthropic', 'openai', 'openrouter'):
        raise ValueError('custom member providers require an explicit selected model declaration')
    config = {}
    env = {}
    for field in ('api', 'baseUrl', 'authHeader'):
        if field not in declared:
            continue
        value = declared[field]
        if field == 'authHeader':
            if not isinstance(value, bool):raise ValueError('invalid provider authHeader')
        elif not isinstance(value, str):
            raise ValueError('provider api/baseUrl must be explicit text')
        if isinstance(value, str) and '${' in value:
            match = re.fullmatch(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', value)
            if not match or not values.get(match[1]):
                raise ValueError('unresolved member provider environment reference')
            env[match[1]] = values[match[1]]
        config[field] = value
    local_without_auth = False
    if 'apiKey' not in declared and not declared.get('authHeader', False):
        try:
            address = urlsplit(declared.get('baseUrl', ''))
            local_without_auth = (address.scheme in ('http', 'https') and bool(address.hostname)
                and ipaddress.ip_address(address.hostname).is_loopback and address.username is None
                and address.password is None and not address.query and not address.fragment
                and (address.port is None or 1 <= address.port <= 65535))
        except (ValueError, TypeError):
            pass
    key = None
    credential = declared.get('apiKey')
    if isinstance(credential, dict):
        if (set(credential) != {'source', 'provider', 'id'} or credential.get('source') != 'env'
                or credential.get('provider') != 'default' or not isinstance(credential.get('id'), str)
                or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', credential['id'])):
            raise ValueError('only default env provider SecretRef is supported; vault/file/exec lookup is not performed')
        key = credential['id']
        secret = values.get(key)
        config['apiKey'] = dict(credential)
    elif isinstance(credential, str) and credential:
        match = re.fullmatch(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', credential)
        key = match[1] if match else {'anthropic':'ANTHROPIC_API_KEY','ollama':'OLLAMA_API_KEY'}.get(provider,'OPENAI_API_KEY')
        secret = values.get(key) if match else credential
        if not match and '${' in credential:
            raise ValueError('unresolved member provider credential; configure its private environment first')
        config['apiKey'] = '${'+key+'}'
    elif not local_without_auth:
        raise ValueError('member provider needs an explicit API-key setting; vault/OAuth lookup is not performed')
    if key is not None:
        if not secret:
            raise ValueError('unresolved member provider credential; configure its private environment first')
        env[key] = secret
    # Keep only the chosen model's declared inference metadata.
    allowed = ('id', 'name', 'api', 'reasoning', 'input', 'cost', 'contextWindow', 'maxTokens', 'compat')
    if models is not None:
        config['models'] = [{key:value for key,value in models[0].items() if key in allowed}]
    return binding, provider, config, env


def _mirror_security_mode(border_home, member_home):
    """A production member checks security.mode in ITS OWN home
    (<home>/config/openclaw.json, see controls._security_config_path). Mirror only
    the Border's mode there; never copy the rest of the Border's security config.
    Absent or unreadable on the Border: write nothing (the member stays 'hobby')."""
    try:
        mode = (json.loads((Path(border_home)/'config/openclaw.json').read_text())
                .get('security') or {}).get('mode')
    except (OSError, ValueError, AttributeError):
        return
    if not isinstance(mode, str) or not mode:
        return
    cfg = private_dir(Path(member_home)/'config')
    file = cfg/'openclaw.json'
    file.write_text(json.dumps({'security': {'mode': mode}}, indent=2)+'\n'); file.chmod(0o600)


def provision_convergence(runtime, risk, destination=None, model=None, key_file=None, env_file=None):
    """Prepare an isolated OpenClaw evidence member, without enrollment or launch.

    Source/interpreter executables are shared; mutable env, records and workspace
    belong to the member. This is configuration isolation, not OS confinement.
    """
    require_standalone_home(runtime.home)
    if runtime.kind != 'openclaw':
        raise ValueError('Convergence member execution requires OpenClaw; Hermes is not qualified')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', risk):
        raise ValueError('risk/member must be safe local names')
    prof = _profiles()
    values = prof.configured_values(env_file or runtime.env_file, include_process=False)
    try:
        prof.convergence_settings(values)
    except Exception:
        raise ValueError('enabled and complete Convergence configuration is required') from None
    source = json.loads(runtime.config.read_text())
    if 'convergence-read-mcp' not in (source.get('mcp') or {}).get('servers', {}):
        raise ValueError('install the native Convergence reader in the selected Border first')
    records = {}
    for component in ('convergence-read', 'n2n'):
        record = runtime.home/'python-runtimes/records'/component
        command = record.read_text().strip() if record.is_file() else ''
        if not Path(command).is_absolute() or not os.access(command, os.X_OK):
            raise ValueError('install '+component+' in the selected Border before provisioning')
        records[component] = command
    provider_values = values
    if key_file:
        provider_values = prof.configured_values(key_file, include_process=False)
    binding, provider, provider_config, provider_env = _convergence_provider(source, provider_values, model)
    risk_mode = values.get('N2N_RISK_MODE', 'production').strip().lower()
    if risk_mode not in ('production', 'testing'):
        raise ValueError('select production or explicitly opted-in testing risk mode')
    home = Path(destination or Path(HOME)/('.openclaw-'+risk+'-convergence')).expanduser().absolute()
    require_standalone_home(home)
    if home == runtime.home or (home.exists() and any(home.iterdir())):
        raise ValueError('member already provisioned; existing home is preserved')
    if home.is_symlink():
        raise ValueError('member home must not be a symlink')
    # Do not copy registrations whose absolute paths or embedded env values may
    # select the Border. Build the existing canonical component-launch entry.
    registration = {
        'command': sys.executable,
        'args': ['-u', str(Path(REPO)/'scripts/component-launch.py'), 'convergence-read',
                 '--server', 'convergence-read-mcp'],
        'transport': 'stdio',
        'env': {'NETCLAW_RUNTIME': 'openclaw', 'OPENCLAW_HOME': str(home),
                'OPENCLAW_STATE_DIR': str(home), 'OPENCLAW_CONFIG_PATH': str(home/'openclaw.json'),
                'NETCLAW_RUNTIME_ROOT': str(home/'python-runtimes'),
                'NETCLAW_RUNTIME_ENV': str(home/'.env')},
    }
    config = {
        'mcp': {'servers': {'convergence-read-mcp': registration}},
        'channels': {},
        'tools': native_tool_policy(),
        'models': {'providers': {provider: provider_config}},
        'agents': {'defaults': {'workspace': str(home/'workspace'),
            'model': {'primary': binding}, 'models': {binding: {'alias': 'member'}}}},
    }
    # Spec 167 F5: keep the Border's DefenseClaw OpenClaw plugin (model guard) and
    # nothing else from its plugin configuration; no other plugin is copied.
    from bgp.federation.controls import defenseclaw_plugin_config
    guard_plugin = defenseclaw_plugin_config(source)
    if guard_plugin is not None:
        config['plugins'] = guard_plugin
    # Exact connector settings only; no wildcard copying of unrelated future keys.
    keys = ('CONVERGENCE_ENABLED', 'CONVERGENCE_API_URL', 'CONVERGENCE_API_TOKEN',
            'CONVERGENCE_SITE', 'CONVERGENCE_EXPORTERS', 'CONVERGENCE_ALLOW_LOOPBACK_HTTP')
    member_values = {k: values[k] for k in keys if k in values}
    member_values.update(provider_env)
    member_values.update(NETCLAW_RUNTIME='openclaw',
        OPENCLAW_HOME=str(home), OPENCLAW_STATE_DIR=str(home), OPENCLAW_CONFIG_PATH=str(home/'openclaw.json'),
        NETCLAW_RUNTIME_ROOT=str(home/'python-runtimes'), NETCLAW_RUNTIME_ENV=str(home/'.env'),
        N2N_ROLE='member', N2N_RISK_MODE=risk_mode, N2N_RISK_NAME=risk, N2N_MEMBER_ID=risk+'/convergence',
        N2N_MEMBER_BASE=str(home/'n2n'), N2N_MEMBER_MODEL=binding,
        N2N_MEMBER_SCOPE=json.dumps([item['name'] for item in prof.BASE_FLOOR]+['convergence-observations']))
    private_dir(home)
    record_dir = private_dir(home/'python-runtimes/records')
    for component, command in records.items():
        file = record_dir/component; file.write_text(command+'\n'); file.chmod(0o600)
    skill = private_dir(home/'workspace/skills/convergence-observations')
    shutil.copyfile(Path(REPO)/'workspace/skills/convergence-observations/SKILL.md', skill/'SKILL.md')
    file = home/'openclaw.json'; file.write_text(json.dumps(config, indent=2)+'\n'); file.chmod(0o600)
    file = home/'.env'; file.write_text(''.join(k+'='+json.dumps(v)+'\n' for k,v in member_values.items())); file.chmod(0o600)
    _mirror_security_mode(runtime.home, home)
    return home


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--risk", required=True)
    ap.add_argument("--member", required=True, help="profile/member name, e.g. ipfabric")
    ap.add_argument("--runtime", choices=["hermes","openclaw"], default=None)
    ap.add_argument("--home", default=None)
    ap.add_argument("--model", default=None, help="override provider/model (Convergence defaults to selected primary; other profiles use tier)")
    ap.add_argument("--anthropic-key-from", "--provider-env", dest="anthropic_key_from", default=None,
                    help="provider credential env file (Convergence: explicit selected-provider references only)")
    ap.add_argument("--border-config", default=None)
    ap.add_argument("--member-env", default=None,
                    help="the member's private .env that component-launched servers load "
                         "(default: <home>/.env; never the Border's)")
    args = ap.parse_args()

    runtime=selected()
    require_standalone_home(runtime.home)
    if (args.runtime or runtime.kind)=='hermes':
        home=provision_hermes(runtime,args.risk,args.member,args.home,args.model)
        print('Scoped Hermes member home:',home)
        print('Set N2N_BORDER_ENDPOINT and the one-use enrollment token in its private .env; launch with N2N_MEMBER_ENV_FILE.')
        return
    if args.member == 'convergence':
        if args.border_config and Path(args.border_config).resolve() != runtime.config.resolve():
            raise ValueError('select the Convergence Border runtime explicitly; alternate templates are not supported')
        home = provision_convergence(runtime, args.risk, args.home, args.model, args.anthropic_key_from)
        print('Scoped OpenClaw Convergence member home:', home)
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
    border = json.load(open(args.border_config))
    m = copy.deepcopy(border)

    # 1. scope MCP servers; runtime paths point at the member's home, never the Border's
    mh = str(_member_path(args.home or f"{HOME}/.openclaw-{args.risk}-{name}"))
    require_standalone_home(mh)
    border_home = Path(args.border_config).expanduser().resolve().parent
    _refuse_border_home(mh, {runtime.home, border_home})
    border_servers = m["mcp"].get("servers", {})
    border_roots = {e["env"]["NETCLAW_RUNTIME_ROOT"] for e in prof.member_servers(name, border_servers).values()
                    if isinstance(e, dict) and isinstance(e.get("env"), dict) and e["env"].get("NETCLAW_RUNTIME_ROOT")}
    border_root = (border_roots.pop() if len(border_roots) == 1 else
                   str(Path(args.border_config).expanduser().resolve().parent/'python-runtimes'))
    m.setdefault("mcp", {})["servers"] = scoped_mcp_servers(
        border_servers, name, prof, home=mh, member_env=args.member_env, border_root=border_root)
    _require_member_env(m["mcp"]["servers"], mh, args.member_env, name,
                        border_envs=(runtime.env_file, border_home / ".env"))

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
    private_dir(mh)
    if (Path(mh)/'openclaw.json').exists():raise ValueError('member already provisioned; existing config is preserved')
    copy_runtime_records(m["mcp"]["servers"], mh, border_root)
    json.dump(m, open(f"{mh}/openclaw.json", "w"), indent=2)
    os.chmod(f"{mh}/openclaw.json", 0o600)
    _mirror_security_mode(Path(args.border_config).expanduser().resolve().parent, Path(mh))
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
