# Third-Party Notice — Catalyst Center tool catalogue

NetClaw adopts the **tool catalogue** from Cisco's official Catalyst Center MCP server. It does
**not** vendor or run that server's code.

| | |
|---|---|
| **Upstream** | https://github.com/cisco-en-programmability/catc-mcp-oss |
| **Branch** | `release/2.3.7.11` — targets Catalyst Center 2.3.7.11 |
| **Licence** | **Apache-2.0** — identical to NetClaw's own |
| **What is used** | the generated API operation definitions (`uri`, `method`, `parameterLocation`, description) |
| **What is not used** | the server runtime, its Dockerfile, its HTTP transport, its dependency set |
| **Adopted by** | spec 087 |

## Why the catalogue and not the runtime

The catalogue is the valuable artifact — 515 generated definitions covering the whole Catalyst
Center API surface, each carrying enough metadata to dispatch a call. Reusing it with a thin
NetClaw client avoids three upstream properties at once:

1. **`fastmcp>=2.0.0` is unbounded** and resolves to 3.x. Five NetClaw servers pin `fastmcp<3` —
   the hazard that blocked spec 083's first candidate.
2. **Transport is streamable HTTP on port 7001.** Every other NetClaw MCP server is stdio.
3. **A container** would otherwise be required purely to isolate (1).

## Two things about the upstream repository worth knowing

- **`main` contains no code** — only governance files. The implementation lives on
  `release/<catalyst-version>` branches. A default-branch clone looks like an empty project.
- **It is version-coupled by design.** The branch name is the supported appliance version, and its
  manifest excludes 19 tools as `unsupported_release`. Regenerating the catalogue against a
  different Catalyst Center version is the intended upgrade path.

## Regenerating the catalogue

```bash
git clone https://github.com/cisco-en-programmability/catc-mcp-oss
cd catc-mcp-oss && git checkout release/<M.N.P.Q>
# then re-derive catalog/*.json from
#   catalyst_center_mcp/bundled_tools/Agent_DNAC/autogen/promoted/api_*.json
```

Only **GET** operations are included. The single mutating operation in the upstream bundle
(`api_complianceRemediation`, POST) is deliberately excluded — see `README.md`.
