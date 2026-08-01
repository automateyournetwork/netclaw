# Convergence Telemetry Architecture

How device telemetry flows from network devices into dashboards and alerts.

**Status**: Implemented (Phase 11, 2026-07-27)  
**Spec**: [`specs/080-convergence/otel-convergence.md`](../specs/080-convergence/otel-convergence.md)  
**Future**: [`specs/080-convergence/rag-driven-telemetry.md`](../specs/080-convergence/rag-driven-telemetry.md) (Phase 12 — RAG-driven vendor profiles)

---

## System diagram

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DEVICE TELEMETRY PIPELINE                                │
│                                                                              │
│  ┌──────────┐        ┌───────────────────────────────────────────┐           │
│  │  Cisco   │──SNMP──│                                           │           │
│  │  IOS-XE  │        │          OTel Collector                   │           │
│  │  switches │──syslog│  • syslog receiver (rfc3164)             │           │
│  └──────────┘  :1514 │  • vendor regex (Cisco mnemonic)          │           │
│                       │  • filterlog CSV parser (pfSense)         │           │
│  ┌──────────┐        │  • SNMP receivers (per device)            │──────┐    │
│  │ pfSense  │──syslog│  • device identity (IP → name map)        │      │    │
│  │ firewall │  :1514 │  • structured field promotion             │      │    │
│  │          │──SNMP──│                                           │      │    │
│  └──────────┘        └──────────┬────────────┬───────────────────┘      │    │
│                                  │            │                          │    │
│                    logs           │            │  metrics                 │    │
│              ┌────────┴────────┐ │            │                          │    │
│              ▼                  ▼ │            ▼                          ▼    │
│  ┌────────────────┐  ┌──────────────┐  ┌───────────┐  ┌─────────────────┐   │
│  │  Loki (14d)    │  │ VictoriaLogs │  │Prometheus │  │ VictoriaMetrics │   │
│  │  interactive   │  │   (365d)     │  │  (15d)    │  │    (365d)       │   │
│  │  bounded labels│  │  full fields │  │  alerting │  │  long-term      │   │
│  └───────┬────────┘  └──────────────┘  └─────┬─────┘  └─────────────────┘   │
│          │                                     │                              │
│          │  Loki ruler                         │                              │
│          │  (log-derived metrics)              │                              │
│          └─────── remote-write ───────────────▶│                              │
│                                                │                              │
│                                    ┌───────────▼───────────┐                  │
│                                    │  Alert rules          │                  │
│                                    │  • DeviceSnmpStale    │                  │
│                                    │  • SwitchLinkLost     │                  │
│                                    │  • SyslogIngestRefuse │                  │
│                                    │  • pfsense:blocks*    │                  │
│                                    └───────────┬───────────┘                  │
│                                                │                              │
│                                    ┌───────────▼───────────┐                  │
│                                    │    Alertmanager       │                  │
│                                    └───────────┬───────────┘                  │
│                                                │ webhook                      │
│                                    ┌───────────▼───────────┐                  │
│                                    │  alert-receiver       │                  │
│                                    │  (investigation       │                  │
│                                    │   policy: T0/T1/T2)   │                  │
│                                    └───────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                     HOST / AGENT LOG PIPELINE                                 │
│                                                                              │
│  ┌──────────────────┐       ┌────────────┐       ┌────────────────┐          │
│  │ /tmp/openclaw/   │──────▶│  promtail  │──────▶│  Loki (14d)    │          │
│  │ systemd journal  │       │  28 MiB    │       │                │          │
│  │ (user units)     │       └────────────┘       └────────────────┘          │
│  └──────────────────┘                                                        │
│                                                                              │
│  Why not OTel: collector image is distroless (no journalctl binary).         │
│  See T150 decision in otel-convergence.md.                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### OTel Collector (`otel/opentelemetry-collector-contrib:0.104.0`)

Single process, two signal types.

| Signal | Receiver | Protocol | Output |
|--------|----------|----------|--------|
| Logs | `syslog/devices` | RFC3164 UDP+TCP :1514 | Loki + VictoriaLogs |
| Metrics | `snmp/<device>` (per device) | SNMPv2c, 60s interval | Prometheus + VictoriaMetrics |

**Config**: `deploy/convergence/otel/otel-config.yaml`  
**Generated from**: `convergence.yaml` inventory via `scripts/render-convergence-telemetry.py`

### What gets structured at ingest

| Source | Fields extracted | Used by |
|--------|-----------------|---------|
| RFC3164 syslog (pfSense) | `appname`, `facility`, `priority`, `severity`, `hostname`, `message` | Security board, Loki ruler |
| pfSense `filterlog` CSV | `action`, `direction`, `fw_interface`, `protocol`, `ip_version`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `tracker` | Firewall detail panels, Loki ruler block/DNS metrics |
| Cisco IOS/IOS-XE mnemonic | `priority`, `sequence`, `device_time`, `mnemonic`, `sev_level`, `message` | NetClaw board, investigation correlation |
| SNMP interfaces | `interface_name` (from ifDescr), `device_name`, `role`, `vendor`, `site` | Network board, all interface alerts |

### Label cardinality (FR-042)

Loki labels are a **bounded, explicitly listed set**: `device_name`, `site`, `job`, `service_name`, `level`.

Everything else is a **structured field** queryable with `| json | field_name=...` but never a label. This is the guard against two measured failures:

- Cisco mnemonics (`%SEC_LOGIN-5-LOGIN_SUCCESS`) — hundreds of distinct values, each creates a Loki stream
- External scanner IPs — effectively unbounded

Rule: if the value set cannot be enumerated in advance, it is a field, never a label.

### Prometheus metrics (from SNMP)

| Metric | Source OID | Labels |
|--------|-----------|--------|
| `interface_status` | ifOperStatus 1.3.6.1.2.1.2.2.1.8 | `device_name`, `interface_name`, `instance`, `job`, `role`, `vendor`, `site` |
| `interface_admin_status` | ifAdminStatus 1.3.6.1.2.1.2.2.1.7 | same |
| `interface_octets_in_bytes_total` | ifHCInOctets 1.3.6.1.2.1.31.1.1.1.6 | same |
| `interface_octets_out_bytes_total` | ifHCOutOctets 1.3.6.1.2.1.31.1.1.1.10 | same |
| `interface_errors_in_total` | ifInErrors 1.3.6.1.2.1.2.2.1.14 | same |
| `interface_errors_out_total` | ifOutErrors 1.3.6.1.2.1.2.2.1.20 | same |

These names are emitted directly by the OTel `prometheusremotewrite` exporter (measured in T145). There are no recording rules or `label_replace` chains.

### Log-derived metrics (Loki ruler → Prometheus)

| Metric | Source |
|--------|--------|
| `pfsense:filterlog_blocks:rate5m` | `{job="device-syslog"} \| json \| attributes_appname="filterlog" \| attributes_action="block"` |
| `pfsense:filterlog_pass:rate5m` | same, `action="pass"` |
| `pfsense:filterlog_blocks_by_interface:rate5m` | by `interface`, `direction` |
| `pfsense:filterlog_blocks_by_protocol:rate5m` | by `protocol` |
| `pfsense:dns_queries:rate5m` | `attributes_appname="unbound"` + `query:` |
| `pfsense:dns_nxdomain:rate5m` | `NXDOMAIN` |
| `pfsense:dns_servfail:rate5m` | `SERVFAIL` |

These exist in Prometheus because pfSense exposes no block/DNS counters over SNMP.

---

## Retention

| Store | Retention | What | Notes |
|-------|-----------|------|-------|
| Prometheus | 15d | Metrics (scrape + remote-write) | Boards and alert rules query here |
| VictoriaMetrics | 365d | Same metrics (remote-write from OTel) | Long-term trend |
| Loki | 14d | Logs (interactive, bounded labels) | Dashboard panels, Loki ruler |
| VictoriaLogs | 365d | Same logs (full structured fields) | Long-term forensics |

---

## Inventory and setup

### Where device identity comes from

| Data | Source | Populated by |
|------|--------|--------------|
| Device name, IP, role | Nautobot (wizard `--mode nautobot`) or manual `convergence.yaml` | Operator |
| Platform / network driver | Nautobot `platform.network_driver` | Operator |
| **Which OIDs to poll** | Today: hardcoded IF-MIB. Phase 12: RAG knowledge base | Network engineer |
| **Syslog format** | Today: rfc3164 + Cisco regex. Phase 12: RAG per platform | Network engineer |
| SNMP community | `.env` (`SNMP_COMMUNITY`) | Operator |

### Setup flow

```bash
# 1. Populate inventory (once, or when devices change)
./scripts/convergence-telemetry-setup.sh --mode nautobot --apply
# or: --mode manual --add name=R1 ip=10.1.0.1 role=router vendor=cisco

# 2. Apply (idempotent, validates before restart)
./scripts/convergence-telemetry-apply.sh --config ~/.openclaw/convergence.yaml

# 3. Verify
./deploy/convergence/smoke-device-snmp.sh
./deploy/convergence/smoke-log-panels.sh
```

The apply script:
- Generates OTel receiver/processor/pipeline blocks from inventory
- Validates the collector config before restarting (exits on invalid)
- Restarts the collector (bind-mounted config, read at start, no reload)
- Reloads Prometheus
- Writes a device-config checklist (SNMP/syslog device-side guidance)

### Device-side configuration

Devices need two things. Neither is auto-pushed (v1); the generated checklist gives the exact commands:

1. **SNMP**: read-only community matching `SNMP_COMMUNITY`
2. **Syslog**: target `<convergence-host>:1514` UDP or TCP

Vendor-default syslog format is accepted — no RFC5424 reconfiguration required. Cisco benefits from `logging origin-id hostname` so `device_name` matches the SNMP inventory.

---

## Grafana boards

Three narrative boards at **http://127.0.0.1:3300** → folder Convergence:

| Board | UID | Story |
|-------|-----|-------|
| **Network** | `convergence-network` | Site health → WAN → named campus interfaces → Wi-Fi → edge |
| **Security** | `convergence-security` | Posture → alerts → edge/guest → firewall detail (parsed filterlog) → syslog/auth |
| **NetClaw** | `convergence-netclaw` | Tokens by provider → T0/T1/T2 investigations → gateway/mesh logs |

See [`deploy/convergence/grafana/README.md`](../deploy/convergence/grafana/README.md) for data dependencies per section.

---

## Alert rules

| Alert | Scope | `investigate` | Trigger |
|-------|-------|---------------|---------|
| `DeviceSnmpStale` | all devices | true | no fresh SNMP metrics in 5m |
| `SwitchIdlePortsPresent` | role=switch | false | admin-up + oper-down ports (expected) |
| `SwitchLinkLost` | role=switch | true | was oper-up 15m ago + admin still up |
| `SwitchInterfaceErrorsHigh` | role=switch | true | aggregate error rate > 5/s for 10m |
| `SyslogIngestRefusing` | collector | false | OTel rejecting received records |
| `LogExportFailing` | collector | false | records not reaching Loki/VictoriaLogs |
| `SyslogIngestNoEntries` | collector | false | zero records ingested for 1h |
| `LogIngestDown` | collector | false | OTel Collector not scraping |
| `HostLogShipDown` | promtail | false | promtail not scraping |

**Role scoping**: Today only `role=switch` has link/error/idle rules. Routers and firewalls get `DeviceSnmpStale` only. Phase 12 adds role-aware rules.

---

## Drift guard (K3s vs Docker)

K3s manifests carry **copies** of the collector config, alert rules, and Prometheus
config (Kustomize refuses symlinks outside its root). These previously drifted 210
lines silently. Now machine-checked:

```bash
deploy/convergence/k8s/check-config-drift.sh          # report
deploy/convergence/k8s/check-config-drift.sh --fix    # copy Docker → K8s
```

Run before applying any K3s overlay.

---

## Phase 12: RAG-driven vendor profiles

Today every device gets the same IF-MIB OID set regardless of role or platform.
Phase 12 adds a RAG lookup at setup time:

- The wizard queries the knowledge base for the platform's telemetry profile
- If found: extended metrics (BGP, OSPF, CPU, memory) are merged with IF-MIB
- If not found: IF-MIB only + guidance on what to provide and where

Supporting a new vendor = write one markdown document describing its MIB tables, ingest it, and re-run the wizard. No Python edits, no PRs.

See [`specs/080-convergence/rag-driven-telemetry.md`](../specs/080-convergence/rag-driven-telemetry.md).

---

## Key decisions and why

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| OTel over promtail for devices | Structured logs at ingest, one process for both signals, rfc3164 native | `otel-convergence.md` |
| Promtail kept for host sources | OTel image has no `journalctl`; partial migration adds complexity for zero gain | T150 in `otel-convergence.md` |
| Loki + VictoriaLogs dual write | Loki for interactive (bounded labels), VLogs for long-term (full fields) | `otel-convergence.md` |
| Prometheus + VictoriaMetrics dual write | Prometheus for alerting (15d), VM for trend analysis (365d) | T152 |
| `service.name=device_snmp` (not `network-devices`) | Preserves every existing selector without changing dashboards or alerts | `otel-convergence.md` compatibility gap section |
| Receive-time stamps, not device time | RFC3164 has no timezone; trusting it put pfSense lines 6h in the past | T141 finding, carried into OTel config |
| `src_ip`/`dst_ip` as fields, never labels | External scanner IPs are unbounded; promoting them explodes stream count | FR-042 |
| No ingest-time GeoIP/enrichment | Rate-limited APIs (AbuseIPDB 1k/day) and the `pfsense-threat-intel` skill already enriches at triage time | Operator decision 2026-07-27 |

---

## Files

| Path | Purpose |
|------|---------|
| `deploy/convergence/otel/otel-config.yaml` | Collector config (managed sections generated from inventory) |
| `deploy/convergence/otel/snmp-receivers.md` | OID/metric map and cutover strategy reference |
| `deploy/convergence/prometheus/alerts/device.rules.yml` | Device + ingest alert rules |
| `deploy/convergence/loki/rules/fake/convergence-security.yml` | Loki ruler — log-derived pfSense metrics |
| `deploy/convergence/loki/loki-config.yaml` | Loki config with ruler enabled |
| `deploy/convergence/promtail/promtail-config.yml` | Host log collection (agent files + journal) |
| `deploy/convergence/grafana/provisioning/dashboards/json/` | Three provisioned boards |
| `config/convergence.example.yaml` | Inventory schema (SNMP targets + syslog devices) |
| `scripts/render-convergence-telemetry.py` | Generator (inventory → collector config + Prometheus + checklist) |
| `scripts/convergence-telemetry-apply.sh` | Apply pipeline (generate → validate → restart → reload) |
| `deploy/convergence/k8s/components/otel-collector/` | K3s parity component |
| `deploy/convergence/k8s/check-config-drift.sh` | Drift guard for K3s copies |
| `deploy/convergence/smoke-device-snmp.sh` | SNMP collection smoke test |
| `deploy/convergence/smoke-log-panels.sh` | Grafana log panel validation |
