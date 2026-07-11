# n2n-mcp — NetClaw-to-NetClaw Federation MCP Server

Operator/agent control surface for **N2N Federation** (feature 052): let
consenting NetClaw operators exchange capability inventories, and (in later
phases) invoke each other's tools/skills and chat claw-to-claw — all over the
existing BGP mesh.

This server is a **thin stdio proxy** over the mesh daemon's `/n2n/*` HTTP API
(`bgp-daemon-v2.py`, `127.0.0.1:8179`). The daemon is the single source of
truth; this MCP works from any gateway session (Slack/Webex/CLI/HUD). Same
pattern as `protocol-mcp` proxying the daemon for BGP state.

## Prerequisites

- The mesh daemon running with federation enabled (`N2N_ENABLED=true`).
- At least one NetClaw mesh peer (BGP Established) to federate with.

## Tools (US1 — capability exchange & queries)

| Tool | Purpose |
|------|---------|
| `n2n_status` | Federation overview: identity, peers, states, inventory freshness |
| `n2n_consent` | Consent to federate with a peer (mutual consent required) |
| `n2n_kill` | Kill switch — sever federation with a peer (BGP untouched) |
| `n2n_peer_capabilities` | A peer's advertised skills/tools/badges, with staleness |
| `n2n_compare_capabilities` | Diff a peer's capabilities against ours |
| `n2n_set_visibility` | Control what you advertise (all / selected peers / hidden) |

Later phases add `n2n_grant`/`n2n_invoke`/`n2n_approvals` (US2 — remote
invocation) and `n2n_chat` (US3 — claw-to-claw chat).

## Environment variables

| Var | Default | Purpose |
|-----|---------|---------|
| `BGP_DAEMON_API` | `http://127.0.0.1:8179` | Mesh daemon HTTP API base URL |

Federation behavior (budgets, timeouts, refresh) is configured on the **daemon**
via `N2N_*` variables — see `.env.example` and
`specs/052-n2n-federation/contracts/n2n-daemon-api.md`.

## Transport

stdio (FastMCP). Registered in `config/openclaw.json` as `n2n-mcp`.

## Install

```bash
pip install -r mcp-servers/n2n-mcp/requirements.txt
```

## See also

- Skill: `workspace/skills/n2n-federation/SKILL.md`
- Spec: `specs/052-n2n-federation/`
