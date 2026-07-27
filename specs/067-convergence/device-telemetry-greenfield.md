# Greenfield device telemetry + agent observability (optional PR)

**Parent**: 067-convergence  
**Status**: Phase 8 **plumbing shipped** (collectors, scrape jobs, recording rules,
partial Grafana, smoke T088). Phase 10 productizes setup (wizard, templates,
apply, curated boards) — see [`telemetry-setup.md`](./telemetry-setup.md).  
**Intent**: First-class **optional** install components for a **greenfield** Convergence
deploy so a new site gets switch SNMP, device syslog, NetClaw agent metrics/logs,
and Grafana dashboards **without** depending on `k3s-observability-stack` or a
pilot cutover.

> **Not a migration plan.** Pilot stacks may already run similar collectors; this
> feature ships **self-contained** configs under `deploy/convergence/` and catalog
> IDs under the NetClaw installer. Operators who already have a pilot OBS may
> continue dual-run; greenfield users enable profiles/components only.

---

## Problem

Today Convergence ships:

| Included | Gap |
|----------|-----|
| WAN blackbox, health score, UniFi REST exporter | No **L2/L3 switch** interface SNMP |
| Optional `generic-snmp-wireless` (IF-MIB APs) | Not Cisco Catalyst / campus switch monitoring |
| Optional `full` (empty Loki/VM/Grafana + speedtest) | No **device syslog** path, no **NetClaw agent** scrapes/dashboards |
| alert-receiver + guardian-claw | Investigator has no switch metrics unless pilot Prom is scraped |

The production house site already proved:

- OTEL SNMP receivers for HomeSwitch01/02/04 + pfSense (+ UniFi APs over SNMP)
- Syslog → Loki with `device_name` labels
- Grafana network dashboards
- Host `openclaw-metrics` token/cost exporter + rsyslog forward of mesh/gateway logs

That work must be **repackaged as greenfield product**, not “copy from pilot.”

---

## Goals / non-goals

### Goals

1. **Greenfield optional components** selectable in installer / compose profiles / k8s components.
2. **Docker and K3s parity** for the same logical services.
3. **Documented inventory** of switches (IP, SNMP community/v3, labels) via
   `config/convergence.yaml` + env secrets.
4. **Prometheus-compatible metrics** for interface status/octets/errors (and
   extensible OIDs).
5. **Syslog ingest** into Convergence Loki when full-stack logs are enabled.
6. **NetClaw agent observability**: token/cost exporter scrape + optional log ship
   of gateway/mesh/alert-receiver into Loki; provisioned Grafana dashboards.
7. **Alerts** for interface down, exporter down, agent exporter down — wired to
   existing Alertmanager → alert-receiver pipe.

### Non-goals

- Replacing pyATS/gNMI for config change or deep BGP RIB analysis.
- Shipping vendor-private MIB packs for every AP brand (wireless stays UniFi REST
  or generic-snmp-wireless).
- Auto-migrating an existing pilot `observability` namespace.
- Embedding full Grafana chrome as the primary HOME UI (native KPIs stay first;
  dashboards optional embed/link).

---

## User stories

### US-DT1 — Greenfield switch SNMP without a pilot stack (P1)

**As** an operator installing Convergence for a new site,  
**I want** to declare my switches (e.g. Catalyst 3850s) and enable a device-SNMP
component,  
**so that** interface up/down, errors, and traffic appear in Prometheus and
HOME Devices without cloning `k3s-observability-stack`.

**Acceptance**

1. Given `deploy: docker` and `device_snmp.enabled: true` with two switch targets,
   when compose starts with the device-snmp profile, then Prometheus has a healthy
   scrape job and `interface.status` (or documented metric names) exist per
   `device_name`.
2. Given a switch interface admin-down, when the poll interval elapses, then an
   alert rule can fire and reach Alertmanager (and optionally alert-receiver).
3. Given K3s greenfield overlay + component, when applied, then the same metrics
   are available in-cluster.

### US-DT2 — Device syslog into Convergence Loki (P2)

**As** an operator,  
**I want** switches/firewall to send syslog into the Convergence log path,  
**so that** DIY queries and Grafana explore work on a greenfield stack.

**Acceptance**

1. Given full-stack Loki + syslog receiver (OTEL or equivalent), when a test
   syslog line is sent with a known device IP, then Loki returns a stream labeled
   `device_name=<configured>`.
2. Install docs list firewall/switch syslog target (host IP or NodePort).

### US-DT3 — NetClaw agent metrics and logs (P1)

**As** an operator,  
**I want** LLM token/cost and gateway/mesh/alert-receiver logs in the same OBS
plane as site metrics,  
**so that** I can watch agent health next to network health on a greenfield deploy.

**Acceptance**

1. Given catalog component `convergence-agent-metrics` (or equivalent), when
   installed, then `openclaw-token-exporter` (or successor) listens on a stable
   port and Prometheus scrapes `netclaw_model_*`.
2. Given agent-log forward enabled, when the gateway logs a line, then it is
   queryable in Convergence Loki (or documented host→Loki path).
3. Grafana provisions at least one **NetClaw agent** dashboard from repo JSON
   (`scripts/openclaw-metrics/grafana-dashboard-netclaw-quota.json` or successor
   under `deploy/convergence/grafana/provisioning/dashboards/`).

### US-DT4 — Optional Grafana boards for network + agent (P3)

**As** an operator,  
**I want** provisioned dashboards for switches and NetClaw,  
**so that** greenfield Grafana is useful out of the box.

**Acceptance**

1. Dashboard JSON is in-repo and auto-loaded when Grafana profile is on.
2. Datasources already provisioned (Prometheus, Loki, VictoriaMetrics) are used.
3. HOME may deep-link “Open dashboards” to Grafana; iframe embed is optional
   follow-up (auth/`allow_embedding`).

---

## Architecture (greenfield)

```text
                    ┌─────────────────────────────────────┐
  Switches / FW     │  device telemetry (optional)        │
  SNMP :161  ──────►│  OTEL Collector (snmp receivers)    │──► Prometheus
  Syslog :514/1514 ►│  + syslog/udplog receiver           │──► Loki
                    └─────────────────────────────────────┘

  NetClaw host
  ├── openclaw-token-exporter :9110  ──scrape──► Prometheus
  ├── rsyslog / journal forward  ───────────► Loki (or OTEL)
  └── alert-receiver :8099       ◄── webhook── Alertmanager

  Convergence stack (always / optional full)
  ├── prometheus + alertmanager + blackbox + convergence-api
  ├── unifi profile (REST)
  ├── generic-snmp-wireless profile (APs only — distinct)
  └── full: Loki + VM + Grafana + speedtest
```

**Metric naming**: Prefer stable labels `device_name`, `device_ip`, `site`,
`job`. Document mapping from OTEL metric names to Prom series used in alerts
and HOME Devices.

**Reference implementation (for design only, not a runtime dependency):**

- Pilot OTEL SNMP layout: homeswitch01/02/04, pfSense, UniFi APs (interface
  octets/errors/status OIDs).
- Host: `scripts/openclaw-metrics/`, `scripts/rsyslog-netclaw-forward.conf`.

Ship **rewritten/minimal** configs under `deploy/convergence/`; do not import
pilot namespace manifests as-is.

---

## Config contract (extends `config/convergence.yaml`)

```yaml
site: home
deploy: docker | k3s

# Existing
firewall: { type: none | pfsense | ... }
wireless: { type: none | unifi | generic-snmp }
sot: { type: none | nautobot | netbox }

# NEW — campus / access device telemetry (greenfield)
device_telemetry:
  snmp:
    enabled: false
    # OTEL collector recommended; snmp_exporter modules allowed as alternative
    engine: otel | snmp_exporter
    version: v2c            # v3 via secrets later
    poll_interval: 60s
    targets:
      - name: HomeSwitch01
        ip: 192.168.3.2
        role: switch
        # community from env SNMP_COMMUNITY or per-target secret
      - name: HomeSwitch02
        ip: 192.168.3.3
        role: switch
      - name: HomeSwitch04
        ip: 192.168.3.5
        role: switch
      # optional: include firewall SNMP if not covered elsewhere
      # - name: pfSense-FW01
      #   ip: 192.168.3.1
      #   role: firewall
  syslog:
    enabled: false
    listen: "0.0.0.0:1514"   # or 514 with capabilities
    # map peer IP → device_name (same names as snmp targets)

agent_observability:
  token_exporter:
    enabled: false
    # host systemd unit; scrape target = host:9110 from stack
    port: 9110
  log_forward:
    enabled: false
    # rsyslog/journal → Convergence Loki or OTEL
    include: [gateway, mesh, alert-receiver]

grafana:
  provision_network_dashboards: true
  provision_agent_dashboards: true
```

### Env secrets (`.env.example` additions)

```bash
# Device SNMP (greenfield optional)
SNMP_COMMUNITY=public
# SNMP_V3_* later

# Agent metrics scrape (from stack Prometheus → host)
# NETCLAW_METRICS_HOST=host.docker.internal
# NETCLAW_METRICS_PORT=9110
```

---

## Installer catalog (proposed)

| Component ID | Profile group | Description |
|--------------|---------------|-------------|
| `convergence-device-snmp` | Convergence | OTEL/snmp device poller for switches (+ optional FW) |
| `convergence-device-syslog` | Convergence | Syslog receiver → Loki (requires full logs or bundled Loki) |
| `convergence-agent-metrics` | Convergence | Host openclaw-token-exporter + Prom scrape + rules |
| `convergence-agent-logs` | Convergence | rsyslog/journal ship to Convergence Loki |
| `convergence-grafana-dashboards` | Convergence | Provision network + agent dashboard JSON |

Compose profiles (illustrative):

- `device-snmp`
- `device-syslog` (implies Loki available — depend on `full` or slim Loki service)
- agent pieces remain **host** install via `setup.sh` / systemd templates

K3s: `deploy/convergence/k8s/components/device-snmp/`, `device-syslog/`,
`agent-scrape/` + dashboard ConfigMaps.

---

## HOME / API surface (optional but desirable)

| Surface | Behavior |
|---------|----------|
| Devices | Show switches from SoT **or** device_telemetry targets; link to interface health if metrics exist |
| Overview | Optional “switch health” KPI (count of interfaces down) when device_snmp enabled |
| Skills | `alert-triage` / monitoring skills document PromQL for `device_name` + job |
| Dashboards | Link or embed Grafana when provisioned |

---

## Tasks (Phase 8)

See `tasks.md` Phase 8 (T080–T095) — **complete** (plumbing).

## Phase 10 (productized setup — not Phase 8 rework)

Phase 8 left operators able to enable profiles and edit targets by hand. Phase 10
owns:

| Gap after Phase 8 | Phase 10 owner |
|-------------------|----------------|
| Inventory wizard (manual / Nautobot / NetBox) | T129–T131, T137 |
| Vendor templates + idempotent apply | T125–T128, T135–T136 |
| Human interface names end-to-end (ifDescr/ifName → interface_*) | metric contract in telemetry-setup + T126/T135 |
| Curated Grafana suite (not dump / ifIndex garbage) | T132–T133 |
| Device SNMP/syslog config checklist | T131 |
| Installer invokes setup/apply | T130 |

Do **not** re-open Phase 8 checkboxes. Detail and acceptance:
[`telemetry-setup.md`](./telemetry-setup.md) · `tasks.md` Phase 10 (T120–T138).

---

## Testing (greenfield)

1. **Empty host** (or CI compose): enable only `convergence-core` + `convergence-device-snmp` with a mock SNMP agent or lab switch → metrics appear.
2. **No pilot cluster** required for CI; optional integration job against lab 3850s.
3. Agent metrics: generate a gateway turn → `netclaw_model_calls_total` increases.
4. Syslog: `logger`/`nc -u` test line → Loki query returns label.
5. Full profile: Grafana lists provisioned dashboards without manual import.

---

## PR framing (upstream)

**Title idea:** `feat(convergence): greenfield device SNMP + agent observability (optional)`

**Scope for first PR (suggested slice):**

1. Spec + contracts (this doc + adapters.yaml extension) — **this change**  
2. Follow-up PR: OTEL device-snmp compose + k8s component + alerts  
3. Follow-up PR: agent-metrics host unit + scrape + dashboard provisioning  
4. Follow-up PR: syslog → Loki + network dashboards  

Each PR must be **optional** (default off) and must not break minimal UniFi/WAN-only installs.
