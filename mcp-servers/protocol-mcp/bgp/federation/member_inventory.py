"""Content-free member runtime inventory for the operator's internal HUD.

These are configuration observations, never execution permissions or live tool
availability. Never project command lines, URLs, environment values or credentials.
"""
import json
import os
import re
from pathlib import Path


def _name(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:/@+-]{1,200}", value) else None


def project_inventory(card):
    from .runtime import project_harness
    if not isinstance(card, dict):
        return {"mcp_servers": [], "llm": {"primary_model": None}, "source": "member configuration",'harness':project_harness(None)}
    llm = card.get("llm") or {}
    servers = card.get("mcp_servers")
    out = []
    for server in (servers if isinstance(servers, list) else [])[:256]:
        if not isinstance(server, dict) or not _name(server.get("name")):
            continue
        tools = server.get("tools")
        out.append({"name": server["name"], "tools": list(dict.fromkeys(
            n for value in (tools if isinstance(tools, list) else [])[:512]
            if (n := _name(value if isinstance(value, str) else value.get("name") if isinstance(value, dict) else None))))})
    result = {"mcp_servers": out, "llm": {"primary_model": _name(llm.get("primary_model")) if isinstance(llm, dict) else None},
            'harness':project_harness(card.get('harness'),source='member-advertised'),
            "source": "member configuration", "availability": "configured; execution not verified", "available": card.get("available") is not False}
    if isinstance(card.get("unavailable_skills"), list):
        result["unavailable_skills"] = project_unavailable(card["unavailable_skills"])
    return result


# Spec 174: why a scoped skill will not load in the member's own runtime.
_REASONS = {"missing_requirements", "disabled", "blocked", "agent_filtered", "not_loaded", "not_installed"}
_REQUIREMENT_KINDS = ("bins", "anyBins", "env", "config", "os")
SKILL_CHECK_TIMEOUT_S = 30.0


def project_unavailable(entries):
    """Skill names and the names of their missing requirements, never values."""
    out = []
    for entry in (entries if isinstance(entries, list) else [])[:512]:
        if not isinstance(entry, dict) or not _name(entry.get("name")) or entry.get("reason") not in _REASONS:
            continue
        missing = entry.get("missing") if isinstance(entry.get("missing"), dict) else {}
        out.append({"name": entry["name"], "reason": entry["reason"], "missing": {
            kind: [n for n in missing[kind][:32] if _name(n)]
            for kind in _REQUIREMENT_KINDS if isinstance(missing.get(kind), list) and missing[kind]}})
    return out


def unavailable_skills(member):
    """Scoped skills a member reported its runtime will not load. Empty when it has
    not reported (an older member, Hermes, a failed check): routing is unchanged."""
    inventory = stored_inventory(member) or {}
    return {e["name"] for e in inventory.get("unavailable_skills") or []}


def skill_report(scope, check):
    """Scoped skills an `openclaw skills check --json` report says the agent will
    not load. The base floor is served by the member daemon, not OpenClaw, so it
    is skipped; every other scope entry is a workspace skill name."""
    from .risk import BASE_FLOOR
    if not isinstance(check, dict) or not isinstance(check.get("eligible"), list):
        return None
    daemon = {e["name"] for e in BASE_FLOOR}
    eligible = set(check["eligible"])
    missing = {e.get("name"): e.get("missing") for e in check.get("missingRequirements") or [] if isinstance(e, dict)}
    other = {}
    for key, reason in (("disabled", "disabled"), ("blocked", "blocked"), ("agentFiltered", "agent_filtered")):
        for e in check.get(key) or []:
            other.setdefault(e if isinstance(e, str) else e.get("name") if isinstance(e, dict) else None, reason)
    workspace = check.get("workspaceDir")
    out = []
    for name in sorted(n for n in scope if _name(n) and n not in eligible and n not in daemon):
        if name in missing:
            out.append({"name": name, "reason": "missing_requirements", "missing": missing[name]})
        elif name in other:
            out.append({"name": name, "reason": other[name]})
        elif isinstance(workspace, str) and (Path(workspace) / "skills" / name / "SKILL.md").is_file():
            # On disk but in no list: OpenClaw did not load it, for example past
            # skills.limits.maxSkillsLoadedPerSource.
            out.append({"name": name, "reason": "not_loaded"})
        else:
            out.append({"name": name, "reason": "not_installed"})
    return project_unavailable(out)


async def check_skills(scope, env=None):
    """Ask this member's own OpenClaw which scoped skills it will not load.

    Returns None when unknown: a Hermes runtime, or the check failing. A member
    runs no gateway, and `openclaw skills check` asks the configured gateway first
    (the Border's, which answers with its own environment or refuses the member's
    token). Pointing it at a port nothing listens on makes OpenClaw evaluate this
    member's workspace and environment locally, as its embedded turns do."""
    import asyncio
    import socket
    import tempfile
    from .gateway import _agent_env, _member_agent_args, _openclaw_bin
    from .runtime import selected
    env = dict(_agent_env() if env is None else env)
    try:
        if not scope or selected(env).kind == "hermes":
            return None
    except (OSError, ValueError):
        return None
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        env["OPENCLAW_GATEWAY_PORT"] = str(probe.getsockname()[1])
    env.pop("OPENCLAW_GATEWAY_URL", None)
    cmd = [_openclaw_bin(), "skills", "check", *_member_agent_args(), "--json"]
    # A regular file, not a pipe: Node can truncate a large pipe write on exit.
    with tempfile.TemporaryFile() as output:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=output, stderr=asyncio.subprocess.DEVNULL, env=env)
        except OSError:
            return None
        try:
            await asyncio.wait_for(proc.wait(), SKILL_CHECK_TIMEOUT_S)
        except BaseException as e:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            if isinstance(e, asyncio.TimeoutError):
                return None
            raise
        if proc.returncode != 0:
            return None
        output.seek(0)
        try:
            check = json.loads(output.read(8 * 1024 * 1024))
        except ValueError:
            return None
    return skill_report(scope, check)


def local_inventory(env=None):
    env = os.environ if env is None else env
    from .runtime import selected,local_harness
    runtime=selected(env);home=runtime.home;source=runtime.config
    try:
        if source.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("oversized config")
        if runtime.kind=='hermes':
            import yaml
            config=yaml.safe_load(source.read_text()) or {}
            model=config.get('model') or {}
            primary=model.get('default') or model.get('model') if isinstance(model,dict) else model
            servers=config.get('mcp_servers') or {}
            return project_inventory({'harness':local_harness(runtime),'llm':{'primary_model':primary},'mcp_servers':[
                {'name':name,'tools':value.get('tools',{}).get('include',[]) if isinstance(value.get('tools'),dict) else value.get('tools',[])} for name,value in servers.items() if isinstance(value,dict)]})
        config = json.loads(source.read_text())
        servers = (config.get("mcp") or {}).get("servers")
        if servers is None:
            servers = config.get("mcpServers") or {}
        model = ((config.get("agents") or {}).get("defaults") or {}).get("model")
        for agent in (config.get("agents") or {}).get("list") or []:
            if agent.get("id") == env.get("N2N_AGENT_ID", "main") and agent.get("model") is not None:
                model = agent["model"]
        primary = env.get("N2N_MEMBER_MODEL") or (model.get("primary") if isinstance(model, dict) else model)
        return project_inventory({'harness':local_harness(runtime),"llm": {"primary_model": primary}, "mcp_servers": [
            {"name": name, "tools": (value.get("toolFilter") or {}).get("include", value.get("tools", []))} for name, value in servers.items() if isinstance(value, dict)]})
    except (OSError, ValueError, TypeError, AttributeError):
        return {"mcp_servers": [], "llm": {"primary_model": _name(env.get("N2N_MEMBER_MODEL"))}, "source": "member configuration unavailable", "available": False,'harness':local_harness(runtime)}


def stored_inventory(member):
    try:
        health = json.loads(member["health"] or "{}")
        if not isinstance(health.get("inventory"), dict):
            return None
        return {**project_inventory(health["inventory"]), "received_at": health.get("inventory_at")}
    except (KeyError, TypeError, ValueError):
        return None
