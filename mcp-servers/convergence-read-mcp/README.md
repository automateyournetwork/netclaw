# Convergence read-only MCP

Optional stdio connector for an independently operated Convergence service. It
collects no traffic and changes no service, case, network, model or investigation.
Install this component in its own Python environment through NetClaw setup.

| Tool | Arguments | Result |
|---|---|---|
| `convergence_flow_summary` | `range`: 15m/1h/6h/24h; optional `exporter` | Site-scoped retained rankings, exact observation window, coverage and limits |
| `convergence_flow_evidence` | IP `address`, ISO `start`/`end` with timezone, optional `exporter` | Latest 100 retained matching records involving that IP as source or destination |

Both tools return `{ok:true,data:...}` or `{ok:false,error:{code,message}}`.
Errors distinguish `disabled`, `not_configured`, `invalid_argument`, `unauthorized`,
`unavailable`, `timeout` and `compatibility`. A successful summary can itself have
`status: active`, `empty` or `not_configured`. Failed reads are never fresh zeroes.
Unknown fields are discarded; required fields, site, exporters and windows are
validated before presentation. Credentials and backend error bodies are not returned.

## Private configuration

| Variable | Purpose |
|---|---|
| `CONVERGENCE_ENABLED` | Explicit `true` enables reads; default `false` |
| `CONVERGENCE_API_URL` | HTTPS service origin, without path, userinfo, query or fragment |
| `CONVERGENCE_API_TOKEN` | Viewer credential restricted to the configured site |
| `CONVERGENCE_SITE` | Fixed site identifier, up to 64 letters/digits/dots/underscores/hyphens |
| `CONVERGENCE_EXPORTERS` | Required comma-separated exporter IP allowlist matching the service site |
| `CONVERGENCE_ALLOW_LOOPBACK_HTTP` | Explicit `true` permits HTTP only to literal loopback IPs for a local trial/port-forward |

`localhost` and non-loopback HTTP are deliberately refused. HTTPS verifies system
certificate authorities. Redirects and environment proxy settings are ignored;
configure the final trusted origin. Each read has a 20-second total transport
budget and a 1 MiB body limit. Encoded response bodies are refused; the client
requests `Accept-Encoding: identity`. No raw URL, site, token or query is a tool input.

The API compatibility target is the public Convergence fork revision
[`f54bafca82f339d8573c55c53795fa05bd9dd843`](https://github.com/byrn-baker/netclaw-convergence/tree/f54bafca82f339d8573c55c53795fa05bd9dd843).
This is an exact tested contract, not a promise of an independently versioned API.
[Connection and external setup guidance](../../docs/CONVERGENCE.md) explains the
Linux Docker demonstration, K3s deployment links and current qualification limits.
The connector is new Apache-2.0 NetClaw code; no external service source is vendored.

## Manual isolated installation and smoke test

```bash
python3 -m venv mcp-servers/convergence-read-mcp/.venv
mcp-servers/convergence-read-mcp/.venv/bin/pip install -r mcp-servers/convergence-read-mcp/requirements.txt
mcp-servers/convergence-read-mcp/.venv/bin/python mcp-servers/convergence-read-mcp/server.py
```

The last command serves MCP stdio; use a compatible MCP client, rather than typing
HTTP or chat messages into stdin. Tests use a disposable loopback HTTP fixture and
real MCP initialization/tool discovery/tool calls without devices or model access:

```bash
mcp-servers/convergence-read-mcp/.venv/bin/python tests/convergence-read/test_connector.py
```

Preserve the summary's start/end/exporter for evidence. Records cover either
direction and are a bounded subset, so their bytes need not reproduce the ranking.
Coverage distinguishes synthetic demo, selected host interface and network exporters.
Old receipt timestamps alone do not prove collector failure, and flow metadata does
not establish an attack, application identity, firewall verdict or packet IDS coverage.
Disable by setting `CONVERGENCE_ENABLED=false` and restarting the connector/HUD;
no Convergence data or services are removed.
