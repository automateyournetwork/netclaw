"""Literal optional-setting defaults for the qualified runtime config grammar.

No shell evaluation or operator values are serialized by native projection.
Defaults are materialized only while preparing configuration, never to hide a
broken live registration during readiness observation.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BARE = re.compile(r'\$\{([A-Z_][A-Z0-9_]*)\}')
FALLBACK = re.compile(r'\$\{([A-Z_][A-Z0-9_]*):-([^}]*)\}')


def defaults_for(server, repo=ROOT):
    path = Path(repo) / 'config/mcp-env-defaults.json'
    data = json.loads(path.read_text())
    if data.get('schemaVersion') != 1:
        raise ValueError('Unsupported MCP environment defaults schema')
    defaults = data['servers'].get(server, {})
    if any(not re.fullmatch(r'[A-Z_][A-Z0-9_]*', k) or not isinstance(v, str)
           or '${' in v for k, v in defaults.items()):
        raise ValueError('Invalid MCP environment defaults')
    return defaults


def native_entry(server, entry, values, repo=ROOT, *, allow_legacy=False):
    """Keep supplied native references; materialize only absent optional values."""
    defaults = defaults_for(server, repo)

    def visit(value):
        if isinstance(value, dict):
            return {k: visit(v) for k, v in value.items()}
        if isinstance(value, list):
            return [visit(v) for v in value]
        if not isinstance(value, str):
            return value
        if allow_legacy:
            # The Hermes converter historically accepts older source files.
            value = FALLBACK.sub(lambda m: '${' + m[1] + '}' if values.get(m[1]) else m[2], value)
        if FALLBACK.search(value):
            raise ValueError('Unsupported MCP fallback expression; regenerate registration')
        return BARE.sub(lambda m: defaults[m[1]]
                        if m[1] in defaults and not values.get(m[1]) else m[0], value)
    return visit(entry)


def migrate_known_value(server, old, template, prepared):
    """Upgrade only a canonical old expression; preserve ordinary custom values."""
    if not isinstance(old, str) or not FALLBACK.search(old):
        return old
    defaults = defaults_for(server)
    legacy = BARE.sub(lambda m: '${' + m[1] + ':-' + defaults[m[1]] + '}'
                      if m[1] in defaults else m[0], template) if isinstance(template, str) else None
    known = {legacy}
    if server in ('nautobot-mcp', 'nautobot-golden-config-mcp', 'nautobot-routing-mcp'):
        known.add('${ITSM_LAB_MODE:-true}' if template == '${ITSM_LAB_MODE}' else legacy)
    if old not in known:
        raise ValueError('Custom MCP fallback expression requires manual reconciliation')
    return prepared


def load_mcp_template(raw, limit=1024 * 1024):
    """Read strict registrations from an OpenClaw config that can include model prices."""
    from setup_schema import loads
    return loads(raw, limit, object_field="mcpServers")
