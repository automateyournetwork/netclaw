# Nautobot SoT adapter (Home Docker / K3s)

Provides device inventory lookup from Nautobot as the Source of Truth for the
NetClaw Convergence pipeline. Used by `home-api` to enrich device views and
triage panels with authoritative inventory data (roles, locations, IPs, platforms).

## Enable

Set in `config/convergence.yaml`:

```yaml
sot:
  type: nautobot
```

Set credentials in `deploy/convergence/.env` (Docker) or K8s secret:

```bash
NAUTOBOT_URL=https://nautobot.internal.byrnbaker.me
NAUTOBOT_TOKEN=<your-api-token>
```

The adapter is a library module inside `home-api` — no separate container needed.
It calls the Nautobot REST/GraphQL API directly from the Node.js process.

## What it provides

| Method | Nautobot query | Returns |
|--------|---------------|---------|
| `lookup(query)` | `GET /api/dcim/devices/?q=<query>` | Device records (name, role, platform, location, status, primary IP) |
| `getDevice(name)` | `GET /api/dcim/devices/?name=<name>` | Single device detail |
| `getInterfaces(device)` | `GET /api/dcim/interfaces/?device=<name>` | Interface list with IPs, VLANs |
| `getIPAddresses(query)` | `GET /api/ipam/ip-addresses/?q=<query>` | IP address records |

## Secrets

Never commit tokens. Only set `NAUTOBOT_TOKEN` in `.env` (gitignored).

## Dependencies

Requires `home-api` to be running (the adapter is imported as a library module).
No additional containers or exporters are needed — Nautobot is an existing
external service.

## MCP integration

For deeper investigative queries (golden config, compliance, BGP), NetClaw uses
the dedicated Nautobot MCP servers (`nautobot-mcp-v2`, `nautobot-routing-mcp`,
`nautobot-golden-config-mcp`, `nautobot-firewall-mcp`). This adapter handles
the simpler REST lookups needed by the Home UI device/inventory views.
