# TOOLS.md — Local Infrastructure Notes

Skills define *how* tools work. This file is for *your* specifics — the environment
details unique to this deployment.

> **Scope:** NetClaw looks after a **live home/production network** (site "House").
> The source of truth is **Nautobot at https://192.168.3.253**. A separate
> ContainerLab demo lab exists on VLAN 220 — see the note at the bottom — but that is
> NOT the network you monitor for alerts.

## Source of Truth — Nautobot

- **URL:** https://192.168.3.253
- **Token:** in `~/.openclaw/.env` as `NAUTOBOT_TOKEN` (never hard-code it)
- Authoritative inventory for all managed devices, VMs, IPs, and VLANs.
- Query it first (via `nautobot-mcp`) before falling back to the local
  `scripts/alert-receiver/inventory.yaml`.

## Managed Devices (from Nautobot, site "House")

| Device | Mgmt IP | Role | Platform | Model |
|--------|---------|------|----------|-------|
| pfSense-FW01 | 192.168.3.1 (web/API :440) | firewall | pfsense_plus | Netgate 8200 Max |
| HomeSwitch01 | 192.168.3.2 | home_switch | cisco_ios (IOS-XE) | Cisco WS-C3850-48P |
| HomeSwitch02 | 192.168.3.3 | home_switch | cisco_ios (IOS-XE) | Cisco WS-C3850-48P |
| U6-Pro - Basement Laundry Room | 192.168.3.15 | wireless-ap | Ubiquiti | U6-Pro |
| U6-Pro - Sophies Office | 192.168.3.16 | wireless-ap | Ubiquiti | U6-Pro |
| r640-pve | proxmox.home.byrnbaker.me:443 | hypervisor | Proxmox VE | Dell PowerEdge R640 |

Credentials for device access are in `~/.openclaw/.env`
(`NETCLAW_USERNAME` / `NETCLAW_PASSWORD`), consumed by the pyATS testbed via
`%ENV{}` syntax.

## Accessing the Old Switches (legacy SSH key exchange)

HomeSwitch01/02 are Cisco Catalyst 3850s running older IOS-XE that only negotiate
legacy Diffie-Hellman key exchange. A modern SSH client rejects them by default with
"no matching key exchange method". You must enable the legacy algorithms:

```bash
ssh -oKexAlgorithms=+diffie-hellman-group-exchange-sha1,+diffie-hellman-group14-sha1 \
    admin@192.168.3.2
```

This is already wired into:
- **`~/.ssh/config`** — a `Host 192.168.3.2 192.168.3.3` block sets `KexAlgorithms`
  so any SSH (including pyATS/unicon, which shells out to `ssh`) negotiates correctly.
- **pyATS testbed** (`testbed/testbed.yaml`) — the switch connections carry the
  matching `ssh_options`. The testbed is auto-generated, so the option is emitted by
  `scripts/generate-testbed-from-nautobot.py` and survives regeneration.

If you add another legacy device, add its IP to the `~/.ssh/config` block (or the
generator) with the same `KexAlgorithms` line.

## Network Layout — pfSense VLANs / Subnets

pfSense-FW01 (192.168.3.1) is the gateway for every VLAN. Key segments:

| VLAN | Interface | Subnet | Purpose | DHCP range |
|------|-----------|--------|---------|-----------|
| 3 | device_mgmt (lagg0.3) | 192.168.3.0/24 | Network devices, mgmt, OBS, Nautobot, NetClaw, APs, iLO/iDRAC | .20–.254 |
| 30 | K3S_LAN (lagg0.30) | 192.168.30.0/24 | local-ai (.50), k3s, reverse-proxy | .50–.220 |
| 100 | HomeLan (lagg0.100) | 192.168.100.0/24 | Servers/clients: r640-pve (.20), BakerNas (.22), DiskStation (.23), cameras, Mac mini | .40–.254 |
| 13 | PIHOLES (lagg0.13) | 192.168.13.0/24 | DNS: pihole01 (.253), pihole02 (.254) | .2–.249 |
| 102 | IOT (lagg0.102) | 192.168.102.0/24 | IoT / cameras | .20–.254 |
| 2 | ToberWifi (lagg0.2) | 192.168.2.0/24 | Guest/printer wifi | .55–.254 |
| 101 | kidslaptops (lagg0.101) | 192.168.101.0/24 | Kids' devices | .10–.254 |
| 103 | byrnscomputer (lagg0.103) | 192.168.103.0/24 | Workstation | .45–.254 |
| 35 | nautobot_testing (lagg0.35) | 192.168.35.0/24 | Nautobot test | — |
| 220 | ContainerLabsMGMTNetwork (lagg0.220) | 192.168.220.0/24 | **Demo lab only — not monitored** | — |

WAN is DHCP on igc0.201. The physical `LAN` (igc1, 192.168.1.0/24) is disabled.

## Observability Stack — home-obs-stack (192.168.3.250)

| Service | Address | Query via | Use |
|---------|---------|-----------|-----|
| Prometheus | 192.168.3.250:9090 | `prometheus-mcp` | Metrics, `up`/probe status |
| Grafana | 192.168.3.250:3000 | `grafana-mcp` | Dashboards + Loki/VictoriaMetrics datasources |
| Loki | 192.168.3.250:3100 | `grafana-mcp` | Logs, syslog, NetFlow flow records |
| VictoriaMetrics | 192.168.3.250:8428 | `grafana-mcp` | `goflow2_*` flow metrics |
| Alertmanager | 192.168.3.250:9093 | HTTP `/api/v2/alerts` | Firing alerts |
| goflow2 (NetFlow/IPFIX) | 192.168.3.250:4739/udp | via Loki | Flow ingest (see alert-triage skill) |

## NetClaw Services

- **Alert receiver:** 192.168.3.252:8099 (FastAPI, `netclaw-alert-receiver` service) —
  receives Alertmanager webhooks, enriches from Nautobot / `inventory.yaml`, triggers
  investigation.
- **OpenClaw gateway:** 127.0.0.1:18789 (systemd `--user` service).
- **Discord:** findings posted via the native OpenClaw channel bridge
  (`openclaw message send --channel discord`).

## Virtualization — Proxmox (r640-pve, 192.168.100.20)

- Dell PowerEdge R640, Proxmox VE 9.2.3. Also reachable at proxmox.home.byrnbaker.me:443.
- Hosts the VMs modeled in Nautobot.
- Managed via `proxmox-mcp`.

## pyATS Testbed

- Auto-generated from Nautobot (`scripts/generate-testbed-from-nautobot.py`), and
  auto-synced on a `preTaskExecution` hook — Nautobot stays the source of truth.
- `PYATS_TESTBED_PATH` → `testbed/testbed.yaml`. Do not hand-edit; change Nautobot or
  the generator instead. The generator emits the legacy `ssh_options` for IOS/IOS-XE
  devices (see the switches section above).

## Memory MCP (Hybrid Structured + Semantic)

Persistent memory across sessions (`memory-mcp`).

- **Facts:** `memory_record_fact(entity=, key=, value=)`, `memory_get_facts(entity=)`,
  `memory_timeline(entity=)`, `memory_invalidate(fact_id=)`
- **Decisions:** `memory_record_decision(context=, decision=, rationale=)`,
  `memory_get_decisions(...)`
- **Semantic:** `memory_store_session(summary=)`, `memory_recall(query=)`

**Entity naming:** use the Nautobot device name exactly (e.g., "HomeSwitch01").

## Platform Credentials

All credentials live in `~/.openclaw/.env`. Never put credentials in skill files or
this document.

```
Reference only — actual values in .env:
- Device SSH (switches) → NETCLAW_USERNAME, NETCLAW_PASSWORD
- Nautobot              → NAUTOBOT_URL (https://192.168.3.253), NAUTOBOT_TOKEN
- pfSense               → PFSENSE_URL, PFSENSE_USERNAME, PFSENSE_PASSWORD
- Proxmox               → PROXMOX_HOST, PROXMOX_TOKEN_NAME, PROXMOX_TOKEN_VALUE
- pyATS testbed         → PYATS_TESTBED_PATH
```