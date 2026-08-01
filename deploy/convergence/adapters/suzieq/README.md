# SuzieQ State-History Adapter (Phase 12)

Optional scale-tier component for the Convergence stack. Provides historical
network state queries so investigations can answer "what was the BGP/route/MAC/
ARP/LLDP state before the alert fired" without SSHing to devices at
investigation time.

## When to enable

Turn this on when **any** of the following holds:
- More than ~25 polled devices
- Any BGP / EVPN / VXLAN / MLAG fabric
- Multi-site deployments (namespace-per-site becomes the credential boundary)
- An existing SuzieQ deployment in the customer environment

Below that threshold, the OTel SNMP path plus on-demand pyATS covers it and
SuzieQ adds complexity for little return.

## What this deploys

```
docker compose --profile suzieq up -d
```

Two containers:
- **suzieq-poller**: polls devices via SSH, writes to a parquet lake
- **suzieq-rest**: REST API (port 8000) serving the MCP server

Named volume `suzieq-parquet` persists the state lake across restarts.

## Credential model — read this before enabling

Unlike the rest of the Convergence stack (read-only SNMP community, push-syslog),
SuzieQ needs **SSH login credentials to every device** in the fleet. This is a
material escalation in blast radius.

**Required controls:**
- Dedicated **read-only** service account per platform (privilege level 1 or
  equivalent — never a shared admin credential)
- Credentials in `deploy/convergence/.env` only — **never in the inventory YAML**
- Per-namespace credential separation for multi-site
- The service account should have no `configure terminal` privilege

**Environment variables:**
```
SUZIEQ_DEVICE_USER=suzieq-readonly
SUZIEQ_DEVICE_PASSWORD=<your read-only password>
SUZIEQ_API_KEY=<random key for REST API access>
```

The `inventory.yaml` in this directory contains `${SUZIEQ_DEVICE_USER}` and
`${SUZIEQ_DEVICE_PASSWORD}` references that Docker Compose resolves from `.env`.

## Inventory

The inventory is **auto-rendered** from `config/convergence.yaml` by:

```bash
python3 scripts/render-convergence-telemetry.py \
  --config config/convergence.yaml \
  --out-suzieq deploy/convergence/adapters/suzieq/inventory.yaml
```

Or automatically via `scripts/convergence-telemetry-apply.sh` when
`device_telemetry.state.suzieq.enabled: true` in the config.

**Do not maintain a separate device list.** The inventory renders from
`device_telemetry.snmp.targets` — the same list that feeds the OTel Collector,
Prometheus, and the device checklist.

## Supported platforms

| Vendor | SuzieQ devtype | Verified |
|--------|---------------|----------|
| Cisco IOS-XE | `iosxe` | ✅ 16.12.05b (Catalyst 9300) |
| Arista EOS | `eos` | upstream supported |
| Cumulus/SONiC | `cumulus` / `sonic` | upstream supported |
| Juniper Junos | `junos-*` | upstream supported |
| Cisco NX-OS | `nxos` | upstream supported |
| pfSense/FreeBSD | — | ❌ not supported |

Unsupported roles are excluded via `exclude_roles: [firewall]` in the config.

## Architecture notes

- SuzieQ's own SNMP collection is **off**. The OTel Collector remains the only
  SNMP poller in this architecture (FR-045).
- The REST API is HTTP-only inside the Docker network. For external access,
  front it with the Convergence reverse proxy or mTLS.
- Staleness alerting: `sqPoller` table health should be scraped into Prometheus
  (T164) to detect a dead poller before investigations serve old state.

## Spec reference

- Decision record: `specs/080-convergence/suzieq-state-observability.md`
- FR-043 through FR-050 in `specs/080-convergence/spec.md`
- Tasks T158–T170 in `specs/080-convergence/tasks.md`
