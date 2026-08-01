# Contract: Telemetry setup (080 Phase 10)

**Consumer**: setup wizard, render/apply scripts, installer catalog step
`convergence-device-snmp`, Prometheus, snmp_exporter, Grafana provisioning.  
**Detail**: [`../telemetry-setup.md`](../telemetry-setup.md)

## Inventory schema (`device_telemetry.snmp`)

```yaml
device_telemetry:
  snmp:
    enabled: boolean          # default false
    engine: snmp_exporter     # v1; otel reserved
    version: v2c              # v3 later via env
    poll_interval: duration   # default 60s
    targets:
      - name: string          # required; becomes label device_name
        ip: string            # required; scrape target / instance
        role: switch | firewall | other
        vendor: cisco | pfsense | generic
        template: cisco | pfsense | generic   # defaults from vendor if omitted
  syslog:
    enabled: boolean
    listen: string            # default "0.0.0.0:1514"
```

### Input modes (wizard)

| Mode | Writes |
|------|--------|
| `manual` | targets[] from prompts |
| `nautobot` | selected Nautobot devices → targets[] (`name`, primary IP, role/vendor when known) |
| `netbox` | same field shape as Nautobot |
| `from-yaml` | merge/import targets file |

### Secrets (never in yaml)

| Env | Purpose |
|-----|---------|
| `SNMP_COMMUNITY` | SNMPv2c community for templates |
| `SNMP_V3_*` | Reserved |
| `NAUTOBOT_URL` / `NAUTOBOT_TOKEN` | SoT list (when mode=nautobot) |
| `NETBOX_URL` / `NETBOX_TOKEN` | SoT list (when mode=netbox) |

## Template IDs ↔ modules

| `template` | Module file (deploy path) | Lookups required |
|------------|---------------------------|------------------|
| `cisco` | `adapters/device-snmp/modules/cisco.yml` or merged `snmp.yml` | ifDescr, ifName per metric |
| `pfsense` | `…/pfsense.yml` or merged | same |
| `generic` | `…/if_mib` / generic | same |

Auth community value comes from env at apply/runtime — not hardcoded in git
beyond example `public` for lab.

## Render CLI

**Proposed:** `scripts/render-convergence-telemetry.py` (extends or supersedes
scrape-only `render-device-snmp-scrape.py` for full Phase 10).

| Flag | Meaning |
|------|---------|
| `--config PATH` | convergence.yaml |
| `--targets PATH` | standalone targets YAML |
| `--out-scrape PATH` | Prometheus job fragment |
| `--out-snmp PATH` | snmp_exporter config (or modules dir) |
| `--out-checklist PATH` | device config markdown |
| `--site NAME` | site label (default from yaml) |

**Outputs MUST be deterministic** for the same inventory (stable ordering by
name/IP).

## Apply CLI

**Proposed:** `scripts/convergence-telemetry-apply.sh`

| Step | Behavior |
|------|----------|
| 1 | Call render with operator config |
| 2 | Write **managed sections** into Prometheus config |
| 3 | Install/update snmp_exporter module config |
| 4 | Ensure compose profiles (`device-snmp`, Grafana/full as needed) |
| 5 | Reload Prometheus; restart snmp_exporter if modules changed |
| 6 | Print checklist path + smoke hints |

### Managed section markers

```text
# BEGIN netclaw-convergence-device-snmp
...
# END netclaw-convergence-device-snmp
```

Apply replaces only content between markers. Absent markers → append once with
markers. Never delete unrelated jobs.

## Metric / label contract

### Scrape job

| Item | Value |
|------|--------|
| `job_name` | `device_snmp` |
| `metrics_path` | `/snmp` |
| `params.module` | template module id(s) |
| `params.auth` | auth profile using env community |

### Labels (required)

`device_name`, `role`, `site`, `instance` (device IP), `ifIndex`, `ifDescr`,
`ifName`.

### Recording rules

File: `deploy/convergence/prometheus/alerts/device-recording.rules.yml`  
Names: `interface_status`, `interface_octets_{in,out}_bytes_total`,
`interface_errors_{in,out}_total` with label `interface_name` from `ifDescr`
(fallback `ifName`).

Consumers (Grafana, HOME Devices, skills) SHOULD query recording names when
present; raw `if*` remains valid for debug.

## Dashboard suite (provisioned)

Exactly three boards are provisioned:

| Board | UID | Min acceptance |
|-------|-----|----------------|
| Network | `convergence-network` | Site KPIs (`convergence:*`), WAN blackbox, named campus interfaces (not ifIndex-only legends), UniFi, edge |
| Security | `convergence-security` | Prom `ALERTS` posture + edge/guest access render without any log source; log sections labelled as syslog-dependent |
| NetClaw | `convergence-netclaw` | `netclaw_model_*` cost/tokens by provider, `netclaw_investigations_by_tier` + suppressions/budget trips, gateway/mesh logs selected by `job`/`unit` |

Contract rules:

- Ported / single-subject pilot boards are **not** provisioned; they live unloaded
  in `dashboards/legacy/` with a README pointing at the active suite.
- Every provisioned panel MUST be backed by a collector installable from this repo
  (Docker profile or K3s component). No dependency on pilot `k3s-observability-stack`.
- Log panels MUST select by `job` / `unit` / `device_name` / `service`, never by
  message-content regex.
- Each board MUST declare its data dependencies so an empty panel reads as "source
  not deployed", not "healthy".

Grafana URL (Docker Convergence): host port **3300**.  
Path: `deploy/convergence/grafana/provisioning/dashboards/` (`json/` provisioned,
`legacy/` inert).

## Alerts

| Requirement | Contract |
|-------------|----------|
| Safety | Follow `docs/CONVERGENCE-ALERT-SAFETY.md` — no per-idle-port investigate |
| Annotations | Include `device_name` + interface identity when interface-scoped |
| Labels | `investigate=true|false` for Phase 9 policy |

## Installer

| Catalog ID | Phase 10 behavior |
|------------|-------------------|
| `convergence-device-snmp` | Run or document `convergence-telemetry-setup` / apply; not docs-only echo |

## Wizard CLI (implemented — PR2)

`scripts/convergence-telemetry-setup.sh` → `scripts/convergence-telemetry-setup.py`  
Inventory helpers: `scripts/lib/convergence_telemetry_inventory.py`

```text
modes: manual | nautobot | netbox | yaml | interactive
→ writes/updates convergence.yaml device_telemetry.snmp.targets
→ default write path: ~/.openclaw/convergence.yaml (never example by default)
→ optional --apply to chain convergence-telemetry-apply.sh
→ --dry-run / --select all|1,2,3|name-substr
→ SoT filters: exclude wireless + servers/k3s by default
Smoke: deploy/convergence/smoke-telemetry-setup.sh (T137)
```

## Log ingest (device + agent)

| Requirement | Contract |
|-------------|----------|
| Wire format | Receiver MUST accept **vendor-default** syslog (RFC3164/BSD) as shipped. Cisco IOS-XE and pfSense do not emit RFC5424 by default; requiring device-side RFC5424 is NOT an acceptable product default. |
| Implementation | Reformatting front-end (rsyslog/syslog-ng → RFC5424 → Loki) **or** an rfc3164-capable receiver (e.g. Alloy `loki.source.syslog`, `syslog_format = "rfc3164"`). |
| Failure visibility | Parse failures MUST be countable/observable; silent discard is a contract violation. |
| Labels | `device_name`, `host`, `app`, `site` for device syslog; `job`, `unit`, `service` for agent/journal streams. |
| Consumer rule | Dashboards select on these labels only — never message-content regex. |

Current state: promtail's `syslog` target (RFC5424-only) drops the entire
received device stream — see `tasks.md` T141.

## Non-requirements (Phase 10 v1)

- Auto config-push of SNMP/syslog onto devices  
- GUI inventory editor in HUD (CLI/wizard sufficient)  
- NetFlow / full pilot dashboard dump  
- K3s as the only path (Docker is primary greenfield apply path; K3s parity
  via existing components + rendered ConfigMaps later)  
- Changing investigation-policy schema (Phase 9 remains SoT for tiers)
