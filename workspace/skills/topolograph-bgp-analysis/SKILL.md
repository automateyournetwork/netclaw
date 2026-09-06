---
name: topolograph-bgp-analysis
description: "Reason over BGP topology as a whole -- speakers, peering sessions, the route table, VRF/VPN membership, and whether a BGP epoch is bound to a stored IGP graph. Use when the question is about what the BGP control plane believes (learned routes, session state, VRF placement, BGP-to-IGP correlation) rather than what one live device's BGP table currently shows. Read-only."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "env": ["TOPOLOGRAPH_API_TOKEN"] } } }
---

# Topolograph BGP Topology Analysis

`pyats-routing`, `pyats-junos-routing` and `multivendor-device-query` each
read **one live device's** BGP table. This one reasons over BGP topology
Topolograph has already collected via BMP — speakers, sessions, the route
table across every reporting peer, VRF/VPN placement, and whether that BGP
epoch actually corresponds to a stored IGP graph.

It answers "what does BGP believe the topology and route state are" — not
"what is in this router's BGP table right now."

## Remote, read-only

Same server as `topolograph-igp-analysis` (spec 119): `topolograph-mcp` is a
remote HTTP MCP registered in `config/openclaw.json`, no local server,
fronting **your own** Topolograph instance (`TOPOLOGRAPH_MCP_URL`, default
`https://topolograph.com/mcp`), bearer `TOPOLOGRAPH_API_TOKEN`. No
second credential — if the IGP skill already works, this one does too.

The server runs with `TOPOLOGRAPH_MCP_READ_ONLY=true`: mutation tools are
absent from `tools/list`. None of the 14 BGP tools mutate anything.

**Requires Topolograph >= 2.69** and a `topolograph-mcp-server` build that
includes the BGP tool surface (upstream PR #1). Older instances will list
these tools but every call 404s or returns empty — check `TOOLS.md` for the
version note before assuming a live instance is broken.

## Client-side allowlist

```bash
defenseclaw tool allow topolograph-mcp list_bgp_graphs
defenseclaw tool allow topolograph-mcp get_bgp_graph
defenseclaw tool allow topolograph-mcp list_bgp_nodes
defenseclaw tool allow topolograph-mcp list_bgp_sessions
defenseclaw tool allow topolograph-mcp search_bgp_routes
defenseclaw tool allow topolograph-mcp get_bgp_node_route_summary
defenseclaw tool allow topolograph-mcp get_bgp_route_state
defenseclaw tool allow topolograph-mcp compare_bgp_routes
defenseclaw tool allow topolograph-mcp get_bgp_events_timeline
defenseclaw tool allow topolograph-mcp list_bgp_bindings
defenseclaw tool allow topolograph-mcp get_bgp_binding
defenseclaw tool allow topolograph-mcp resolve_route
defenseclaw tool allow topolograph-mcp get_vrf_inventory
defenseclaw tool allow topolograph-mcp list_vpn_routers
```

Same belt-and-braces note as the IGP skill: the server already hides
mutation tools; this allowlist is the client-side floor in case a
misconfigured instance widens the surface.

## Tools

| Tool | Answers |
|---|---|
| `list_bgp_graphs` / `get_bgp_graph` | Which BGP epochs (BMP collection cycles) exist; the full graph for one. Start here to get a `bgp_graph_time`. |
| `list_bgp_nodes` | BGP speakers in an epoch — role, ASN, route-reflector/PE/core device role. |
| `list_bgp_sessions` | Peering sessions — eBGP/iBGP, families, policy direction, relation to the IGP topology. |
| `search_bgp_routes` | The route table, whole-graph or scoped to one speaker's resolved RIB view — prefix, community, AS-path, RT, and 15+ other filters. |
| `get_bgp_node_route_summary` | One speaker's route totals: per-RIB-tag histogram, Adj-RIB-Out count. |
| `get_bgp_route_state` | Point-in-time route state as of a timestamp. |
| `compare_bgp_routes` | What changed (added/withdrawn/changed) between two instants, optionally scoped to one router, across a collector restart. |
| `get_bgp_events_timeline` | BGP session/route monitoring events. |
| `list_bgp_bindings` / `get_bgp_binding` | Whether a BGP epoch's speaker set is matched to a stored IGP graph, and how confidently (`source_coverage`, matched router IDs). |
| `resolve_route` | Resolve a destination end to end, including a BGP/VPN/MPLS handoff — not just the IGP shortest path. |
| `get_vrf_inventory` / `list_vpn_routers` | VRF names/RDs/route-targets per router; which routers are VPN-PE candidates for `resolve_route`. |

## Boundary — when to use something else

| Question | Skill |
|---|---|
| "What BGP speakers/sessions/routes does this topology have?" | **this skill** |
| "What is in *this router's* BGP table / VRF right now?" | `pyats-routing`, `pyats-junos-routing`, `multivendor-device-query` |
| "What does the IGP topology look like / what if this link fails?" | `topolograph-igp-analysis` |
| "Is this BGP epoch actually the same network as that IGP graph?" | **this skill** — `list_bgp_bindings` |
| "Push a policy / session change" | device-write path, gated — never here |

## Never

- Never present `compare_bgp_routes` or `resolve_route` output as something
  observed on the wire this second — both describe a stored epoch. Report
  how old the `bgp_graph_time` is.
- Never treat a `bound` binding state as permanent — `list_bgp_bindings`
  reflects one BGP epoch matched against one IGP graph; a later epoch can
  have a different `source_coverage`, or `needs_mapping` state.
- Never report an empty result from any of these 14 tools as "no BGP data
  exists" without first checking `TOOLS.md`'s version note — every one of
  them silently returned empty on Topolograph instances predating the
  auth fix in v2.69.1/v2.69.2 (spec 120 research R2), which looks identical
  to "no data" from the caller's side.
