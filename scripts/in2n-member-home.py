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
       python3 scripts/in2n-member-home.py --risk johns-risk --spec member.json \
         --member-env <the member's .env>
A member spec (spec 184) sets the kept servers, skills and the top-level `tools`
policy; see docs/N2N-RISK.md "Member spec".
"""
import argparse, copy, importlib.util, json, os, shlex, stat, sys, re, shutil
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


_PROFILES = None


def _launched_component(entry):
    """The component a scripts/component-launch.py entry starts, else None."""
    global _PROFILES
    _PROFILES = _PROFILES or _profiles()
    return _PROFILES.launched_component(entry)


def scoped_mcp_servers(servers, member, prof=None, home=None, member_env=None, border_root=None,
                       spec=None):
    """The Border's mcp.servers entries a member of profile `member` keeps: its
    MCP_SERVERS list plus memory-mcp, or for a member spec (spec 184) spec.servers
    plus memory-mcp. Servers the Border lacks are skipped.

    With `home`, an entry that selects a runtime (NETCLAW_RUNTIME_ROOT/ENV, which
    install-mcp-config.py writes for scripts/component-launch.py entries) is
    rewritten to the member's own: component-launch.py loads every key of
    NETCLAW_RUNTIME_ENV, so the Border's would hand the member the whole Border .env.
    pyATS keeps the Border's pyats-venv (an executable, like GAIT_VENV), from the
    entry's own NETCLAW_RUNTIME_ROOT or else `border_root`. Its change root follows
    the member's runtime root (<home>/netclaw-changes); see spec 183 research.md."""
    prof = prof or _profiles()
    kept = copy.deepcopy(prof.spec_member_servers(spec, servers) if spec is not None
                         else prof.member_servers(member, servers))
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


def spec_skill_allowlist(config, skills, workspace=None):
    """Limit the member's agents to its skills (OpenClaw's per-agent `skills` allowlist;
    [] loads none) and, with `workspace`, point every agent at the member's own workspace.

    OpenClaw (resolveEffectiveAgentSkillFilter) uses an agent entry's own `skills` when
    it has the key, else agents.defaults.skills. The member's turn runs the default
    agent, `main` when several are configured, or N2N_MEMBER_AGENT (gateway.py), so
    every agent entry copied from the Border gets the list, and so do the defaults.
    Without a roster, agents.entries.main is created to carry it. Copied entries lose
    `tools` (the member's policy is the top-level section) and `agentDir` (the Border's
    agent state: sessions, auth profiles)."""
    agents = config.setdefault("agents", {})
    if not isinstance(agents.get("defaults"), dict):
        agents["defaults"] = {}
    agents["defaults"].pop("tools", None)
    agents["defaults"].pop("agentDir", None)
    agents["defaults"]["skills"] = list(skills)
    if workspace is not None:
        agents["defaults"]["workspace"] = str(workspace)
    entries, roster = agents.get("entries"), agents.get("list")
    found = []
    if isinstance(entries, dict):
        found += [entry for entry in entries.values() if isinstance(entry, dict)]
    if isinstance(roster, list):
        found += [entry for entry in roster if isinstance(entry, dict)]
    if not found:
        agents["entries"] = {"main": {}}
        found = [agents["entries"]["main"]]
    for entry in found:
        entry.pop("tools", None)
        entry.pop("agentDir", None)
        entry["skills"] = list(skills)
        if workspace is not None:
            entry["workspace"] = str(workspace)
    return config


def spec_tools_section(border_tools, policy):
    """The member's top-level `tools`: the spec policy plus tools.sandbox.tools = exactly
    the policy's allowlist. A hardened Border sets tools.sandbox.tools.alsoAllow
    bundle-mcp; a sandboxed session is filtered by both layers (OpenClaw
    resolveSandboxToolPolicyForAgent), and without an explicit sandbox list OpenClaw's
    default (exec, write, ... and no MCP tool) would apply. `border_tools` is not read:
    nothing of the Border's tools section is kept (tools.sandbox has only `tools`)."""
    tools = copy.deepcopy(policy)
    tools["sandbox"] = {"tools": {"allow": list(policy["allow"])}}
    return tools


def spec_skills_section(border_skills, skills):
    """The member's `skills` section, built, not copied: Workshop autonomous learning off
    (OpenClaw defaults it to auto, which writes learned skills that bypass the per-agent
    filter) and, for the member's own skills only, the Border's `enabled` flag. Skill
    entries' apiKey/env/config, extra skill directories and every other key are dropped:
    a skill's settings come from the member's own .env."""
    section = {"workshop": {"autonomous": {"mode": "off"}}}
    entries = (border_skills or {}).get("entries") if isinstance(border_skills, dict) else None
    if isinstance(entries, dict):
        kept = {k: {"enabled": v["enabled"]} for k, v in entries.items()
                if k in skills and isinstance(v, dict) and isinstance(v.get("enabled"), bool)}
        if kept:
            section["entries"] = kept
    return section


# agents.defaults.sandbox keys a spec member keeps (OpenClaw 2026.10.9 AgentSandboxSchema):
# how and where the sandbox isolates, never what it mounts or injects. Dropped:
# workspaceRoot (a Border path), ssh (identity/known-hosts data), browser (its binds; the
# browser tool is not a safe built-in), and docker binds/env/setupCommand/extraHosts and
# the dangerouslyAllow* switches.
SPEC_SANDBOX_KEYS = ("mode", "backend", "workspaceAccess", "sessionToolsVisibility", "scope", "prune")
SPEC_SANDBOX_DOCKER_KEYS = ("image", "containerPrefix", "workdir", "readOnlyRoot", "tmpfs", "network",
                            "user", "capDrop", "pidsLimit", "memory", "memorySwap", "cpus", "gpus",
                            "ulimits", "seccompProfile", "apparmorProfile", "dns")


def spec_sandbox(border_agents):
    """The member's agents.defaults.sandbox: the Border's (agents.defaults.sandbox, with
    agents.entries.main.sandbox over it), reduced to SPEC_SANDBOX_KEYS and
    SPEC_SANDBOX_DOCKER_KEYS; None when the Border configures none. A non-docker backend
    is refused: its settings (ssh identity) are not shared with a member."""
    agents = border_agents if isinstance(border_agents, dict) else {}
    merged = {}
    for source in ((agents.get("defaults") or {}).get("sandbox"),
                   ((agents.get("entries") or {}).get("main") or {}).get("sandbox")
                   if isinstance(agents.get("entries"), dict) else None):
        if isinstance(source, dict):
            for key, value in source.items():
                if key == "docker" and isinstance(value, dict) and isinstance(merged.get("docker"), dict):
                    merged["docker"] = {**merged["docker"], **value}
                else:
                    merged[key] = value
    if not merged:
        return None
    if merged.get("backend") not in (None, "docker"):
        raise ValueError("the Border's agent sandbox uses the %r backend; a spec member keeps only a "
                         "docker sandbox (its ssh settings are not shared)" % merged["backend"])
    sandbox = {k: copy.deepcopy(merged[k]) for k in SPEC_SANDBOX_KEYS if k in merged}
    if isinstance(merged.get("docker"), dict):
        docker = {k: copy.deepcopy(merged["docker"][k]) for k in SPEC_SANDBOX_DOCKER_KEYS
                  if k in merged["docker"]}
        if docker:
            sandbox["docker"] = docker
    return sandbox


def spec_store_overrides(servers, home, border_home):
    """Point a spec member's memory-mcp and gait-mcp at stores in its own home.

    memory-mcp keeps its data in MEMORY_DATA_DIR (default ~/.openclaw/memory: the
    Border's); it becomes <home>/memory. gait-mcp finds its repository from an explicit
    path, else ~/.gait_mcp_root (GAIT_MCP_STICKY_FILE), else its cwd, else HOME (the
    Border's .gait); it gets cwd, HOME and the sticky file under <home>/gait. GAIT_VENV
    (an executable venv, like pyATS's) keeps the Border's, made explicit because HOME
    changes. Returns the store directories to create."""
    home = Path(home)
    stores = []

    def env_of(entry, name):
        if "env" not in entry:
            entry["env"] = {}
        if not isinstance(entry["env"], dict):
            raise ValueError(f"{name} env must be a mapping")
        return entry["env"]

    memory = servers.get("memory-mcp")
    if isinstance(memory, dict):
        env_of(memory, "memory-mcp")["MEMORY_DATA_DIR"] = str(home / "memory")
        stores.append(home / "memory")
    gait = servers.get("gait-mcp")
    if isinstance(gait, dict):
        env = env_of(gait, "gait-mcp")
        venv = env.get("GAIT_VENV") or str(Path(border_home) / "gait-venv")
        env["GAIT_VENV"] = os.path.expanduser(str(venv))
        for key in ("GAIT_DIR", "GAIT_ROOT"):
            env.pop(key, None)
        env.update(HOME=str(home / "gait"), GAIT_MCP_STICKY_FILE=str(home / "gait/.gait_mcp_root"))
        gait["cwd"] = str(home / "gait")
        stores.append(home / "gait")
    return stores


# Top-level openclaw.json keys of a spec member (review round 2), built from scratch like
# the Convergence member's (provision_convergence), never copied from the Border:
#   mcp.servers  the kept servers, runtime and store paths rewritten to the member's;
#   channels {}  a member is reached only through its daemon (gateway.py runs
#                `openclaw agent --local`), never a chat channel;
#   tools        spec_tool_policy + the narrowed sandbox layer;
#   skills       spec_skills_section (Workshop off);
#   models       one provider (spec 185): NetClaw's Anthropic provider with apiKey
#                "${ANTHROPIC_API_KEY}" (from the member's .env slice, never a literal key);
#                or a copy of the Border's entry for the spec's provider with only its
#                model (key references only); or, with "auth": "subscription", no entry:
#                the built-in provider signs in with the member's own login;
#   agents       defaults: own workspace, the member model as primary + allowed,
#                the skill filter, the reduced sandbox; entries: main only (one agent,
#                so gateway._member_agent_args passes no --agent and OpenClaw runs it);
#   memory       search disabled (OpenClaw 2026.10.9 memory.search; the legacy
#                agents.defaults.memorySearch is not accepted): it would index the
#                Border's extraPaths and call a remote embedding API with its key. The
#                member's memory is memory-mcp, in its own store;
#   hooks/cron   disabled: a member runs no webhook mappings and no schedules;
#   plugins      only the DefenseClaw guard plugin (controls.defenseclaw_plugin_config),
#                when the Border has it: the production model guard. No other plugin.
# Not present: gateway (a --local turn starts none; without gateway.mode OpenClaw refuses
# to start one), env (no top-level env.vars), auth, secrets, browser, session, messages,
# and every other Border section.
SPEC_MEMBER_TOP_KEYS = ("mcp", "channels", "tools", "skills", "models", "agents", "memory", "hooks", "cron",
                        "plugins")


def spec_member_providers(border, spec, prof, model):
    """The member's models.providers (spec 185): see SPEC_MEMBER_TOP_KEYS."""
    if spec.get("auth") == "subscription":
        return {}
    if spec.get("provider"):
        providers = (border.get("models") or {}).get("providers") or {}
        return {spec["provider"]: prof.spec_provider_entry(spec, providers)}
    return {"anthropic": {
        "baseUrl": "https://api.anthropic.com", "apiKey": "${ANTHROPIC_API_KEY}",
        "api": "anthropic-messages",
        "models": [{"id": model, "name": model, "reasoning": False, "input": ["text", "image"],
                    "contextWindow": 200000, "maxTokens": 64000}]}}


def spec_member_config(border, servers, spec, prof, home, model):
    """A spec member's openclaw.json, from SPEC_MEMBER_TOP_KEYS only."""
    from bgp.federation.controls import defenseclaw_plugin_config
    skills = prof.spec_skills(spec)
    binding = f"{spec.get('provider') or 'anthropic'}/{model}"
    defaults = {"workspace": str(Path(home) / "workspace"), "model": {"primary": binding},
                "models": {binding: {"alias": "member"}}}
    sandbox = spec_sandbox(border.get("agents"))
    if sandbox is not None:
        defaults["sandbox"] = sandbox
    config = {
        "mcp": {"servers": servers},
        "channels": {},
        "tools": spec_tools_section(None, prof.spec_tool_policy(spec)),
        "skills": spec_skills_section(border.get("skills"), skills),
        "models": {"providers": spec_member_providers(border, spec, prof, model)},
        "agents": {"defaults": defaults, "entries": {"main": {}}},
        "memory": {"search": {"enabled": False}},
        "hooks": {"enabled": False},
        "cron": {"enabled": False},
    }
    spec_skill_allowlist(config, skills, workspace=Path(home) / "workspace")
    guard = defenseclaw_plugin_config(border)
    if guard is not None:
        config["plugins"] = guard
    assert set(config) <= set(SPEC_MEMBER_TOP_KEYS)
    return config


def skill_sources(skills, roots):
    """{skill: source directory} from the first root holding <skill>/SKILL.md as a regular
    file (no symlinked skill directory or SKILL.md)."""
    found = {}
    for skill in skills:
        for root in roots:
            folder = Path(root) / skill
            if (not folder.is_symlink() and folder.is_dir() and (folder / "SKILL.md").is_file()
                    and not (folder / "SKILL.md").is_symlink()):
                found[skill] = folder
                break
    return found


def copy_skill(source, target):
    """Copy one skill's regular files into the member's workspace (0700 dirs, 0600 files).
    The tree is walked with os.fwalk(follow_symlinks=False): every directory, the skill's
    own included, is opened and checked against what was listed, so a directory swapped
    for a symlink during the copy is not entered. Each file is opened O_NOFOLLOW relative
    to its directory and must be a regular file with one link (fstat). Nothing outside
    the skill is copied."""
    private_dir(target)
    source = str(source)
    for dirpath, _dirs, files, dirfd in os.fwalk(source, follow_symlinks=False):
        relative = Path(os.path.relpath(dirpath, source))
        private_dir(target / relative)
        for name in sorted(files):
            try:
                src = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=dirfd)
            except OSError:
                print(f"warning: skill file not copied (not a regular file): {Path(dirpath) / name}",
                      file=sys.stderr)
                continue
            with os.fdopen(src, "rb") as source_stream:
                info = os.fstat(source_stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    print(f"warning: skill file not copied (not a single-link regular file): "
                          f"{Path(dirpath) / name}", file=sys.stderr)
                    continue
                fd = os.open(target / relative / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600)
                with os.fdopen(fd, "wb") as stream:
                    shutil.copyfileobj(source_stream, stream)


def member_home_command(risk, member, member_env, spec=None, allow_dangerous=False):
    """The exact provisioning command for a staged member (printed by in2n-migrate.py);
    a spec member's names its spec file (spec 184), plus --allow-dangerous-tools when
    the operator opted in for a spec that needs it."""
    import shlex
    selector = ("--spec", str(_member_path(spec))) if spec else ("--member", member)
    optin = ("--allow-dangerous-tools",) if spec and allow_dangerous else ()
    return " ".join(shlex.quote(x) for x in (
        "python3", str(Path(REPO) / "scripts/in2n-member-home.py"), "--runtime", "openclaw",
        "--risk", risk, *selector, *optin, "--member-env", str(member_env)))


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


def _env_names(env_path):
    """Variable names assigned in an env file (names only; values are never read out)."""
    names = set()
    try:
        for line in open(os.path.expanduser(env_path)):
            # The same assignment forms write-env.py loads (an optional `export`).
            match = re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line.strip())
            if match:
                names.add(match[1])
    except OSError:
        pass
    return names


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
    ap.add_argument("--member", default=None, help="profile/member name, e.g. ipfabric "
                    "(with --spec: defaults to, and must equal, the spec's name)")
    ap.add_argument("--spec", default=None, help="member spec JSON file (spec 184)")
    ap.add_argument("--allow-dangerous-tools", action="store_true",
                    help="with --spec: permit dangerous built-in tools (exec, write, ...) the spec "
                         "allows; recorded in the member home")
    ap.add_argument("--runtime", choices=["hermes","openclaw"], default=None)
    ap.add_argument("--home", default=None)
    ap.add_argument("--model", default=None, help="override provider/model (Convergence defaults to selected primary; other profiles use tier)")
    ap.add_argument("--anthropic-key-from", "--provider-env", dest="anthropic_key_from", default=None,
                    help="provider credential env file (Convergence: explicit selected-provider references "
                         "only; a --spec member never gets a literal key: its openclaw.json references "
                         "${ANTHROPIC_API_KEY}, resolved from its --member-env)")
    ap.add_argument("--border-config", default=None)
    ap.add_argument("--member-env", default=None,
                    help="the member's private .env that component-launched servers load "
                         "(default: <home>/.env; never the Border's)")
    args = ap.parse_args()

    if not args.member and not args.spec:
        ap.error("--member or --spec is required")
    if args.allow_dangerous_tools and not args.spec:
        ap.error("--allow-dangerous-tools applies only with --spec")
    runtime=selected()
    require_standalone_home(runtime.home)
    if args.spec and (args.runtime or runtime.kind)=='hermes':
        raise SystemExit('error: member specs provision OpenClaw members; Hermes qualifies only the subnet member')
    if args.spec:
        return provision_spec(args, runtime)
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
    _provision_openclaw(args, runtime, args.member)


def provision_spec(args, runtime):
    """A member from a member spec (spec 184): the generic OpenClaw path with the
    spec's servers, model and tool policy. Every spec-183 protection applies."""
    if runtime.kind=='hermes' and not args.border_config:
        raise ValueError('an OpenClaw member requires --border-config pointing at its reviewed OpenClaw template')
    prof = _profiles()
    config = args.border_config or str(runtime.config)
    try:
        spec, warnings = prof.load_member_spec(args.spec, prof.border_template_servers(config),
                                               allow_dangerous=args.allow_dangerous_tools,
                                               providers=prof.border_template_providers(config))
    except prof.MemberSpecError as error:
        raise SystemExit(f"error: {error}")
    for warning in warnings:
        print(f"warning: {args.spec}: {warning}", file=sys.stderr)
    spec["spec_file"] = str(_member_path(args.spec))
    if args.member and args.member != spec["name"]:
        raise SystemExit(f"error: --member {args.member} does not match the spec's name {spec['name']!r}")
    _provision_openclaw(args, runtime, spec["name"], spec)


def _provision_openclaw(args, runtime, name, spec=None):
    if not all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', value) for value in (args.risk,name)):
        raise ValueError('risk/member must be safe local names')
    if runtime.kind=='hermes' and not args.border_config:
        raise ValueError('an OpenClaw member requires --border-config pointing at its reviewed OpenClaw template')
    args.border_config=args.border_config or str(runtime.config)
    args.anthropic_key_from=args.anthropic_key_from or str(runtime.env_file)
    prof = _profiles()
    if spec and args.model:
        # The staged N2N_MEMBER_MODEL (the member's --model) comes from the spec; a different
        # configured model would make the agent reject every task (spec 185 review).
        raise SystemExit("error: --model cannot override a member spec's model; change the spec's "
                         "model and stage it again")
    model = args.model or (spec or {}).get("model") or prof.model_tier(name)
    border = json.load(open(args.border_config))
    m = copy.deepcopy(border)

    # 1. scope MCP servers; runtime paths point at the member's home, never the Border's
    mh = str(_member_path(args.home or f"{HOME}/.openclaw-{args.risk}-{name}"))
    require_standalone_home(mh)
    border_home = Path(args.border_config).expanduser().resolve().parent
    _refuse_border_home(mh, {runtime.home, border_home})
    border_servers = m["mcp"].get("servers", {})
    kept = prof.spec_member_servers(spec, border_servers) if spec else prof.member_servers(name, border_servers)
    if spec:
        from bgp.federation.controls import defenseclaw_plugin_config
        literal = [f"{server}: {path}" for server, entry in sorted(kept.items())
                   for path in prof.literal_secrets(entry)]
        literal += [f"DefenseClaw plugin: {path}"
                    for path in prof.literal_secrets(defenseclaw_plugin_config(border) or {})]
        if literal:
            raise SystemExit("error: the Border template holds literal secrets that a spec member would copy "
                             "(move each into the .env and reference it as ${NAME}): " + "; ".join(literal))
    border_roots = {e["env"]["NETCLAW_RUNTIME_ROOT"] for e in kept.values()
                    if isinstance(e, dict) and isinstance(e.get("env"), dict) and e["env"].get("NETCLAW_RUNTIME_ROOT")}
    border_root = (border_roots.pop() if len(border_roots) == 1 else
                   str(Path(args.border_config).expanduser().resolve().parent/'python-runtimes'))
    m.setdefault("mcp", {})["servers"] = scoped_mcp_servers(
        border_servers, name, prof, home=mh, member_env=args.member_env, border_root=border_root,
        spec=spec)
    _require_member_env(m["mcp"]["servers"], mh, args.member_env, name,
                        border_envs=(runtime.env_file, border_home / ".env"))

    if spec:
        # A spec member's config is built from SPEC_MEMBER_TOP_KEYS, never copied from the
        # Border (review round 2); its memory/GAIT stores live in its own home.
        stores = spec_store_overrides(m["mcp"]["servers"], mh, border_home)
        skills = prof.spec_skills(spec)
        m = spec_member_config(border, m["mcp"]["servers"], spec, prof, mh, model)
        roots = [Path(w) / "skills" for w in (((border.get("agents") or {}).get("defaults") or {}).get("workspace"),)
                 if isinstance(w, str)] + [border_home / "workspace/skills", Path(REPO) / "workspace/skills"]
        sources = skill_sources(skills, roots)
        missing = [skill for skill in skills if skill not in sources]
        if missing:
            print(f"warning: skills not found, not copied: {', '.join(missing)}", file=sys.stderr)
        ws = Path(mh) / "workspace"
        if ws.exists() or ws.is_symlink():
            raise ValueError('member workspace already exists; existing workspace is preserved')
        # The provider key is ${ANTHROPIC_API_KEY}, resolved from the member's own .env
        # (in2n-member.py loads it; the staged slice carries the key). Presence only.
        key = _anthropic_key(args.member_env or Path(mh) / ".env")
    else:
        # 2. strip comms plugins/channels that break --local; keep defenseclaw (guardrails).
        # Profile members: unchanged by spec 184 (see spec 184 "Known behaviour").
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
    if spec:
        for store in stores:
            private_dir(store)
        # Its own workspace: only its skills, copied; no Border file is reachable through
        # it, and anything the agent writes stays in the member home.
        workspace = private_dir(Path(mh) / "workspace")
        for skill, source in sources.items():
            copy_skill(source, workspace / "skills" / skill)
        record = {k: spec.get(k) for k in ("version", "name", "description", "servers", "skills", "tools",
                                           "model", "provider", "auth", "spec_file")}
        record.update(base_skills=spec["base_skills"], base_servers=spec["base_servers"],
                      skill_allowlist=skills, tool_policy=m["tools"],
                      dangerous_tools_allowed=spec["dangerous_tools"],
                      allow_dangerous_tools=bool(args.allow_dangerous_tools))
        fd = os.open(Path(mh) / "netclaw-member-spec.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(json.dumps(record, indent=2) + "\n")
    else:
        # Profile members keep sharing the Border's workspace (identity/skills).
        ws = f"{mh}/workspace"
        if not os.path.exists(ws):
            os.symlink(str(Path(args.border_config).expanduser().resolve().parent/"workspace"), ws)

    print(f"scoped home: {mh}")
    print(f"  mcp.servers: {list(m['mcp']['servers'].keys())}")
    if spec:
        print(f"  tools.allow: {m['tools']['allow']}")
        print(f"  skills: {m['agents']['defaults']['skills']}  (own workspace: {mh}/workspace)")
        if spec["dangerous_tools"]:
            print(f"  WARNING: dangerous tools allowed (--allow-dangerous-tools): {spec['dangerous_tools']}")
    if spec:
        where = args.member_env or f"{mh}/.env"
        binding = f"{spec.get('provider') or 'anthropic'}/{model}"
        if spec.get("auth") == "subscription":
            # Spec 185: the member signs in itself; the login lives in its own home.
            print(f"  model: {binding}  (subscription: sign this member in once, before its first task:")
            print(f"    OPENCLAW_STATE_DIR={shlex.quote(mh)} OPENCLAW_CONFIG_PATH={shlex.quote(mh + '/openclaw.json')} "
                  f"openclaw models auth login --provider {spec['provider']})")
        elif spec.get("provider"):
            refs = sorted(prof.server_env_refs(m["models"]["providers"][spec["provider"]]))
            have = _env_names(where)
            state = ", ".join(f"{r}: {'present' if r in have else 'MISSING'}" for r in refs) or "no variables"
            print(f"  model: {binding}  (the Border's {spec['provider']} provider; {state} in {where})")
        else:
            print(f"  model: {model}  (apiKey ${{ANTHROPIC_API_KEY}}: "
                  f"{'present' if key else 'MISSING'} in {where})")
        print(f"  memory: {mh}/memory  gait: {mh}/gait  (own stores)")
    else:
        print(f"  model: {model}  (anthropic key: {'present' if key else 'MISSING'})")
    print(f"  OPENCLAW_STATE_DIR={mh}")
    print(f"  OPENCLAW_CONFIG_PATH={mh}/openclaw.json")
    print(f"  N2N_MEMBER_MODEL={m['agents']['defaults']['model']['primary'] if spec else model}")


if __name__ == "__main__":
    main()
