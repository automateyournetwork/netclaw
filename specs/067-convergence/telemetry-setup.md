# Telemetry setup productization (067 Phase 10)

**Feature**: 067-convergence  
**Phase**: 10 (optional PR after Phase 8 plumbing + Phase 9 investigation policy)  
**Status**: Spec'd; **PR1–PR3 implemented** (render/apply, wizard/SoT, curated boards + safe alerts).  
**Related**: [`device-telemetry-greenfield.md`](./device-telemetry-greenfield.md) (Phase 8 collectors),  
[`investigation-policy.md`](./investigation-policy.md) (Phase 9 when to investigate)

## Problem

Phase 8 shipped **collectors and partial boards** (snmp_exporter `device-snmp`,
recording rules, promtail syslog, agent metrics, some Grafana JSON). Operators
still cannot easily:

1. **Declare inventory** — manual vendor+IP **or** Nautobot/NetBox select.  
2. **Apply vendor SNMP templates** (Cisco, pfSense first) into live Prometheus /
   snmp_exporter without hand-editing YAML.  
3. Get **device-side** SNMP/syslog configuration guidance (site-specific
   checklist; MCP-assisted verify later).  
4. Use a **curated** Grafana suite equivalent in quality to the pilot
   `k3s-observability-stack` (not a raw dump of empty/ifIndex-only boards).  
5. Rely on a complete **safe** alert pack with named interfaces and
   investigation labels (`investigate`).

Phase 9 (investigation policy) is independent and already shipped; Phase 10
feeds better, named signals into that pipe.

## Goals

1. **Inventory → templates → apply → boards**: one productized path for
   greenfield campus telemetry setup.  
2. **Manual and SoT input**: wizard supports `manual` | `nautobot` | `netbox` |
   `from-yaml`.  
3. **Vendor templates**: Cisco and pfSense first; generic IF-MIB fallback.  
4. **Idempotent apply**: managed Prometheus/snmp sections; compose profile
   enable; Prom reload — re-runs safe.  
5. **Human interface names**: every interface series exposes `ifDescr` and/or
   `ifName`; recording rules produce `interface_*` + `interface_name` for
   dashboards and alerts.  
6. **Curated Grafana**: Home NOC, Campus Interfaces, WAN/edge, agent tokens
   (minimum suite); document Grafana **:3300**.  
7. **Safe alerts**: cardinality-safe rules with interface identity in
   annotations; honor investigation-policy labels.  
8. **Device checklist**: generated markdown with site-specific SNMP/syslog
   guidance (no auto config-push in v1).

## Non-goals

- Auto-push SNMP/syslog config onto devices via MCP in v1 (checklist + optional
  MCP **verify** only).  
- Full NetFlow / AI-box / VPS dashboard suite.  
- Deleting pilot PVCs or migrating historical TSDB.  
- One OpenClaw claw per MCP tool.  
- Replacing HOME native KPIs with Grafana as primary UI.  
- Re-opening Phase 8 checkboxes — Phase 8 plumbing stays complete; Phase 10
  owns productization.

## Relationship to Phase 8 / 9

| Phase | Role after Phase 10 |
|-------|---------------------|
| **8** | Collectors exist (snmp_exporter profile, promtail, agent metrics). **Plumbing complete.** |
| **9** | When to investigate (T0/T1/T2). Unchanged; consumes better alerts. |
| **10** | **How** inventory → templates → apply → boards/alerts → device checklists. |

```text
wizard/setup → convergence.yaml → render → apply → Docker Prom/snmp/Grafana
                     ↑
              Nautobot / NetBox (optional seed)
```

## Inventory model

Source of truth for **device list** (not secrets):

```yaml
# config/convergence.yaml (or ~/.openclaw/convergence.yaml)
site: home
deploy: docker   # docker | k3s

device_telemetry:
  snmp:
    enabled: true
    engine: snmp_exporter    # v1 path; otel reserved
    version: v2c
    poll_interval: 60s
    # community / v3: env only — SNMP_COMMUNITY, never committed
    targets:
      - name: HomeSwitch01
        ip: 192.168.3.2
        role: switch           # switch | firewall | other
        vendor: cisco          # cisco | pfsense | generic
        template: cisco        # maps to snmp module / template pack
      - name: HomeSwitch04
        ip: 192.168.3.5
        role: switch
        vendor: cisco
        template: cisco
      - name: pfSense-FW01
        ip: 192.168.3.1
        role: firewall
        vendor: pfsense
        template: pfsense
  syslog:
    enabled: true
    listen: "0.0.0.0:1514"
    # peer IP → device_name uses snmp.targets names when present
```

### Input modes

| Mode | Behavior |
|------|----------|
| `manual` | Wizard prompts name, IP, vendor/template, role per device |
| `nautobot` | List devices from Nautobot API; operator selects set → writes targets |
| `netbox` | Same schema as Nautobot when `NETBOX_*` env present |
| `from-yaml` | Import existing `targets.yml` or partial convergence.yaml |

**SoT default (v1):** Nautobot is the required SoT path when `sot.type=nautobot`;
NetBox uses the same inventory field shape if env is present. Manual always works
with `sot.type=none`.

### Secrets

| Secret | Location | Rule |
|--------|----------|------|
| SNMP community | `SNMP_COMMUNITY` in `.env` / deploy `.env` | Never in yaml or git |
| SNMPv3 (later) | `SNMP_V3_*` | Same |

## Vendor templates

| Template ID | Scope | snmp_exporter module (illustrative) |
|-------------|--------|-------------------------------------|
| `cisco` | Catalyst / IOS-XE IF-MIB + name lookups | `if_mib` (or `cisco_if_mib`) |
| `pfsense` | pfSense IF-MIB (+ blackbox edge as separate job) | `if_mib` (or `pfsense_if_mib`) |
| `generic` | Any IF-MIB device | `if_mib` |

Templates MUST include **per-metric lookups** for `ifDescr` and `ifName` (not
module-level lookups alone — invalid on snmp_exporter v0.26+ auth-split format).

### Metric / label contract

**Raw scrape (job `device_snmp`):**

| Metric | Meaning |
|--------|---------|
| `ifOperStatus` | Oper state (1=up, 2=down, …) |
| `ifAdminStatus` | Admin state |
| `ifHCInOctets` / `ifHCOutOctets` | Traffic counters |
| `ifInErrors` / `ifOutErrors` | Error counters |

**Required labels on series:**

| Label | Source |
|-------|--------|
| `device_name` | Inventory target name |
| `role` | Inventory role |
| `site` | Site id |
| `instance` | Device IP |
| `ifIndex` | SNMP index |
| `ifDescr` | Lookup from IF-MIB |
| `ifName` | Lookup from IF-MIB |

**Recording rules** (pilot-compatible names for dashboards/skills):

| Recording name | Source | Extra label |
|----------------|--------|-------------|
| `interface_status` | `ifOperStatus` | `interface_name` ← `ifDescr` (fallback `ifName`) |
| `interface_octets_in_bytes_total` | `ifHCInOctets` | same |
| `interface_octets_out_bytes_total` | `ifHCOutOctets` | same |
| `interface_errors_in_total` | `ifInErrors` | same |
| `interface_errors_out_total` | `ifOutErrors` | same |

Dashboards and HOME Devices SHOULD prefer `interface_*` + `interface_name` so
legends are human-readable (not bare ifIndex).

## Apply pipeline

```text
convergence.yaml / targets.yml
        │
        ▼
  render-convergence-telemetry.py
        │  produces:
        │  · Prometheus scrape fragment (job device_snmp)
        │  · snmp_exporter modules (from templates)
        │  · device config checklist markdown
        ▼
  convergence-telemetry-apply.sh
        │  · write managed sections (markers)
        │  · enable compose profiles (device-snmp, full/grafana as needed)
        │  · Prometheus reload / snmp_exporter restart
        ▼
  Live Prom + Grafana + optional checklist file
```

### Managed sections

Apply MUST use marked blocks so re-runs are idempotent and do not clobber
hand-tuned jobs outside the block, e.g.:

```yaml
# BEGIN netclaw-convergence-device-snmp
...generated...
# END netclaw-convergence-device-snmp
```

Missing inventory with `enabled: false` → empty managed section (or omit job);
minimal WAN+UniFi installs remain unaffected.

## Device config checklist

Generator emits markdown (path under `deploy/convergence/` or operator-chosen)
including:

- SNMP community env name (`SNMP_COMMUNITY`) — not the secret value  
- Syslog destination: Convergence host IP + port (default **1514/udp**)  
- Per-vendor snippet hints (Cisco `snmp-server`, pfSense SNMP/syslog UI paths)  
- Optional “verify with MCP” notes (no auto-apply)

## Dashboard suite (curated)

Grafana host port for Convergence Docker: **:3300** (not :3000).

| Board (minimum) | Purpose |
|-----------------|---------|
| Home NOC / Network Guardian | Site health overview |
| Campus Interfaces | Switch/firewall IF-MIB with **named** interfaces |
| WAN / edge | Blackbox + edge signals |
| NetClaw agent / tokens | `netclaw_model_*` quota and cost |

**Acceptance:** Campus Interfaces legends show `ifDescr`/`interface_name`, not
ifIndex-only. Empty or pilot-only dump boards are retired or tagged, not left as
the default suite.

Datasource UIDs and provisioning path stay under
`deploy/convergence/grafana/provisioning/`.

## Alert packs

Rules live under `deploy/convergence/prometheus/alerts/` and MUST follow
[`docs/CONVERGENCE-ALERT-SAFETY.md`](../../docs/CONVERGENCE-ALERT-SAFETY.md):

| Alert (examples) | Investigate? | Notes |
|------------------|--------------|-------|
| `DeviceSnmpExporterDown` | yes | scrape failed |
| `SwitchLinkLost` | yes | was oper-up, now down (real loss) |
| `SwitchIdlePortsPresent` | **no** | aggregate idle ports — dashboard only |
| ~~`SwitchInterfaceDown`~~ | removed | per-ifIndex storms |

Annotations SHOULD include `device_name` and interface identity
(`ifDescr` / `interface_name`) where the alert is interface-scoped. Prom labels
such as `investigate=false` remain force-T0 under Phase 9 policy.

## Installer integration

| Component | Phase 10 expectation |
|-----------|----------------------|
| `convergence-device-snmp` | Install-step invokes or clearly documents `convergence-telemetry-setup` / apply — not docs-only |
| Catalog profile `convergence` | Optional components remain off by default |
| `.env.example` | `SNMP_COMMUNITY`, Grafana port notes, policy paths already present |

## Acceptance (independent test)

1. **Empty targets → wizard with ≥2 Cisco switches → apply**: within **5 minutes**,
   Prometheus has `device_snmp` target(s) up and `interface_status` (or
   `ifOperStatus`) with **non-empty** interface name labels.  
2. **Nautobot mode**: lists devices and writes the selected set into
   `convergence.yaml` without manual IP typing.  
3. **Grafana**: folder Convergence shows Campus Interfaces with named interfaces
   for lab switches (port **:3300**).  
4. **Checklist**: includes site-specific syslog host:port and SNMP community
   **env name** (not the committed secret).  
5. **Idempotent apply**: second apply does not duplicate jobs or wipe unrelated
   Prometheus config.  
6. **Minimal install**: device options off → no extra containers (Phase 8
   parity).

## Tasks

See `tasks.md` Phase 10 (T120–T138).

## PR framing (post-spec)

| PR | Tasks | Outcome |
|----|-------|---------|
| **PR0 Spec** | T120–T124 | Spec Kit complete; reviewable without code |
| **PR1 Render/apply** | T125–T128, T135–T136 | Lab re-applyable without hand-editing |
| **PR2 Wizard + SoT** | T129–T131, T137 | Manual + Nautobot path |
| **PR3 Boards + alerts** | T132–T134, T138 | Operator-visible quality |
