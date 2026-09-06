# Research — Spec 120

## R1 — Upstream tool surface (verified against live API + source, not the plan doc)

14 new `@mcp.tool` functions in `topolograph-mcp-server`'s `mcp-server.py`
(PR #1), all tagged `read`, all `readOnlyHint=True`:

`list_bgp_graphs`, `get_bgp_graph`, `list_bgp_nodes`, `list_bgp_sessions`,
`search_bgp_routes`, `get_bgp_node_route_summary`, `get_bgp_route_state`,
`compare_bgp_routes`, `get_bgp_events_timeline`, `list_bgp_bindings`,
`get_bgp_binding`, `resolve_route`, `get_vrf_inventory`, `list_vpn_routers`.

Verified end-to-end against a live Topolograph instance + seeded demo BGP
data (owner-scoped bearer token, real `bgp_graphs`/`bgp_route_current_state`/
`bgp_igp_bindings` Mongo collections) — not just read from source. Field
names in the tool output (`BgpNode`, `BgpSession`, `BgpRoute`, `Vrf`,
`VpnRouter`, etc.) match the backend's actual serializers
(`bgp_query.py`, `vrf_inventory.py`), corrected once during review where the
draft plan's field names had drifted from what the backend really emits.

## R2 — Requires `topolograph-mcp-server` >= the PR #1 commit; Topolograph >= 2.69

The BGP endpoints these tools call
(`/bgp-graph*`, `/graph/{graph_time}/vrfs`, `/graph/{graph_time}/vpn-routers`)
only exist in `flask-visual` from v2.69 onward, and only became correctly
**authenticated** as of v2.69.2 — a pre-existing bug found while verifying
this spec had 12 of those endpoints running with no `security:` scheme in
`swagger.yml`, so `bearer_auth` was silently never invoked and every one of
them served empty/anonymous-scoped results regardless of a valid token.
Fixed and shipped in `flask-visual` v2.69.1/v2.69.2 (parallel session work,
not part of this spec). An operator on an older Topolograph will see the new
tools list but every call will 404/empty — same failure shape spec 119
already documents for a missing `TOPOLOGRAPH_API_TOKEN`.

## R3 — Same credential, same server, no new registration

No new `config/openclaw.json` entry, no new `EXTERNAL_INTEGRATIONS` line, no
new `TOPOLOGRAPH_API_TOKEN`-equivalent. The 14 tools arrive in the same
`tools/list` response from the already-registered `topolograph-mcp` server
once the operator upgrades both `topolograph-mcp-server` and their
Topolograph instance.

## R4 — Skill boundary vs `topolograph-igp-analysis`

BGP and IGP are separate control planes answering different questions:
IGP reasons over the SPF/LSDB graph (spec 119); BGP reasons over peering
sessions, the route table, VRF/VPN membership, and BGP-to-IGP graph binding
(`list_bgp_bindings` — is this BGP epoch's speaker set actually matched to
a stored IGP graph, and how confidently). Kept as two skills rather than one
combined "topolograph" skill so each skill's tool list and boundary section
stays legible — matches the one-skill-per-question-domain pattern the
platform routing skills already use (`pyats-routing` vs
`pyats-junos-routing` vs `multivendor-device-query`).

## R5 — Deferred: manifest size + acceptance tests

Same constraint as spec 119 R4: measuring token-count impact of the 14 new
tools on the manifest, and a functional acceptance matrix (BGP session
list, route search filters, VRF inventory, route resolution across a
VPN/MPLS handoff) against a live Topolograph + BMP watcher + MongoDB stack,
both need infrastructure not available in this environment. The tool
surface and field shapes are independently verified (R1) without it.

## R6 — Upstream PR #1 not yet merged

Documenting against a reviewed, live-verified, not-yet-merged upstream
branch is the same shape spec 119 used for `TOPOLOGRAPH_MCP_READ_ONLY`
before the corresponding release shipped. Two Codex P1 findings on that PR
(`READ_ONLY` fail-open on an invalid env value; `list_bgp_sessions` missing
pagination) were found and fixed before this spec was written, so nothing
here documents a tool shape expected to change before merge.
