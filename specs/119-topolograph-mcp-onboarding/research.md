# Research — Spec 119

## R1 — Integration kind

Topolograph MCP is remote HTTP, bearer-token, and is called through
`scripts/mcp-call.py` by server key. The repo's established pattern for that
exact shape is a `config/openclaw.json` `mcpServers` entry with a `url` key
(not `command`/`args`), as used by `globalping-mcp` (spec 079) and
`thousandeyes-official-mcp`.

`globalping-mcp` is registered that way and is **not** in
`EXTERNAL_INTEGRATIONS`, so it counts once as a config entry.
`thousandeyes-official-mcp` is in both, which double-counts it in the "167".
Decision: follow the globalping precedent — config entry only — so the count
stays honest. This differs from a first reading of `docs/ADDING-AN-MCP.md`
("remote/OAuth → no config entry"), which fits a server that is proxied
through another (Zoom Meetings MCP via `zoom-rtms-mcp`), not one called
directly.

## R2 — Read-only posture

Upstream `topolograph-mcp-server` gained `TOPOLOGRAPH_MCP_READ_ONLY`
(default `true`): mutation tools (`upload_graph`, `add_lsp`, `update_lsp`,
`delete_lsp`) are removed from `tools/list` via FastMCP `exclude_tags`, with
a server-side guard as defence in depth. NetClaw consumes the default
read-only surface. A client-side `defenseclaw tool allow` allowlist scopes
it further to the analysis tools the skill actually uses.

## R3 — Credential shape

One variable: `TOPOLOGRAPH_API_TOKEN`, sent as `Authorization: Bearer` to the
operator's own Topolograph instance. The instance base URL is configured on
the MCP server itself (`TOPOLOGRAPH_API_BASE`); the hosted instance's public
endpoint is `https://topolograph.com/mcp`.

## R4 — Deferred: manifest size + acceptance tests

Measuring the read-only vs full manifest token counts, and running the
functional acceptance matrix (OSPFv2/OSPFv3/IS-IS graph load, event
timeline, shortest/backup path, edge-failure reaction, MPLS-TE/CSPF, auth),
both need a running Topolograph + MongoDB + Docker stack. Not available in
this environment. Tracked as follow-up; the read-only tool surface and its
tags are verifiable from the upstream source without a live instance.

## R5 — Skill boundary

`topolograph-igp-analysis` owns link-state topology reasoning. It does not
overlap pyATS/junos routing skills (those read one live device's RIB/LSDB);
Topolograph reasons over the whole area's LSDB and simulates change. Live
per-device verification stays with the platform-first routing skills.
