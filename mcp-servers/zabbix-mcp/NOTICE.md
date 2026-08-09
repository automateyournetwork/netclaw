# Third-Party Notice — `zabbix-mcp-server`

This directory vendors a **third-party program that NetClaw does not own and does not modify**.

| | |
|---|---|
| **Upstream** | https://github.com/mpeirone/zabbix-mcp-server |
| **Pinned revision** | `0722f48` — 2026-05-10, "Feature/v2" |
| **Licence** | **GNU General Public License v3.0** — see `vendor/zabbix-mcp-server/LICENSE`, retained verbatim |
| **Relationship to NetClaw** | A separate program, invoked over stdio from its own virtualenv |
| **Adopted by** | spec 083 / roadmap R11 |

## NetClaw is Apache-2.0; this is GPL-3.0

That difference is deliberate and understood. NetClaw **invokes** this program as a subprocess over the
Model Context Protocol; it does not link against it, import it, or incorporate its code. Invocation across a
process boundary is not linkage, so the two licences coexist without either constraining the other.

## Do not modify this tree

The copy under `vendor/` is **byte-identical to upstream at the pinned revision**, and must stay that way.

- A local fork creates a maintenance burden and a licence-obligation question that adopting-as-is exists to
  avoid.
- If a change is needed, **it goes upstream.** Two defects found during evaluation are being reported rather
  than patched locally:
  1. `scripts/start_server.py:139` defaults `READ_ONLY` to `False`, while `src/.../utils.py:29` defaults it
     to `True`. The shipped launcher inverts the safe default. NetClaw works around this by **forcing
     `READ_ONLY=true` in its own configuration** and adding a destructive-method deny-list — see the
     server README.
  2. `pyproject.toml` declares `fastmcp>=v3.2.0`, which is not a valid PEP 440 specifier (stray `v`).

## Why it runs in its own virtualenv

It requires **fastmcp 3.x**. Five NetClaw servers pin `fastmcp<3` — `netbox-mcp-server`,
`CiscoFMC-MCP-server-community`, `Wikipedia_MCP`, `rag-mcp`, `ISE_MCP`. Installing this into the shared
interpreter would break all five. The virtualenv is not a convenience; removing it is a regression.
