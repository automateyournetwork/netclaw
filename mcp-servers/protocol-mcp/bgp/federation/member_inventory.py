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
    return {"mcp_servers": out, "llm": {"primary_model": _name(llm.get("primary_model")) if isinstance(llm, dict) else None},
            'harness':project_harness(card.get('harness'),source='member-advertised'),
            "source": "member configuration", "availability": "configured; execution not verified", "available": card.get("available") is not False}


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
            {"name": name, "tools": value.get("tools", [])} for name, value in servers.items() if isinstance(value, dict)]})
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
