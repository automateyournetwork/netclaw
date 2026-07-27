> **Phase 11 / T153: snmp_exporter is retired.** Device SNMP is collected by the
> OTel Collector and remote-written to Prometheus (15d) and VictoriaMetrics (365d).
> Metric names are unchanged (`interface_status`, `interface_octets_*_bytes_total`,
> `interface_errors_*_total`) and `interface_admin_status` is new. Labels lose
> `ifIndex`/`ifName`/`ifDescr`/`snmp_module`. See
> [`../../otel/snmp-receivers.md`](../../otel/snmp-receivers.md) and
> [`../../../specs/067-convergence/otel-convergence.md`](../../../specs/067-convergence/otel-convergence.md).
> The `snmp.yml` module pack here is still used by the wireless exporter and is the
> input the T154 generator reads for OID/vendor mapping.

# Device SNMP (campus switches) — Phase 8 plumbing + Phase 10 apply

Polls **wired infrastructure** (Cisco Catalyst, pfSense IF-MIB, etc.) via
Prometheus `snmp_exporter`. **Not** the wireless AP path
(`generic-snmp-wireless`).

## Recommended path (Phase 10)

```bash
# 1. Inventory wizard (manual | nautobot | netbox | yaml)
./scripts/convergence-telemetry-setup.sh
# or non-interactive:
./scripts/convergence-telemetry-setup.sh --mode nautobot --select all --write

# 2. Secrets: SNMP_COMMUNITY in deploy/convergence/.env

# 3. Apply (managed Prom section + snmp modules + checklist)
./scripts/convergence-telemetry-apply.sh
# dry-run:
./scripts/convergence-telemetry-apply.sh --dry-run

# 4. Smoke
./deploy/convergence/smoke-telemetry-setup.sh   # inventory path (T137)
./deploy/convergence/smoke-device-snmp.sh       # live metrics (T136)
```

Device config MoP: [`device-config-snippets.md`](./device-config-snippets.md).

Apply will:

1. Render snmp modules (`cisco` / `pfsense` / `generic` + `if_mib` alias)
2. Inject managed Prometheus section (`# BEGIN/END netclaw-convergence-device-snmp`)
3. Write device config checklist → `deploy/convergence/generated/device-config-checklist.md`
4. Start/restart `snmp-device-exporter` and reload Prometheus

### Render only

```bash
python3 scripts/render-convergence-telemetry.py \
  --config config/convergence.example.yaml \
  --out-scrape /tmp/scrape.yml \
  --out-snmp deploy/convergence/adapters/device-snmp/snmp.yml \
  --out-checklist /tmp/checklist.md
```

### Vendor templates

| template | Module file | Notes |
|----------|-------------|-------|
| `cisco` | `modules/cisco.yml` | Catalyst / IOS-XE IF-MIB |
| `pfsense` | `modules/pfsense.yml` | pfSense IF-MIB |
| `generic` | `modules/generic.yml` | Any IF-MIB device |
| `if_mib` | alias | Phase 8 scrape compatibility |

All modules use **per-metric** `ifDescr` / `ifName` lookups.

## Metrics

| Metric | Meaning |
|--------|---------|
| `ifOperStatus` | 1=up, 2=down (per ifIndex) |
| `ifAdminStatus` | admin state |
| `ifHCInOctets` / `ifHCOutOctets` | traffic counters |
| `ifInErrors` / `ifOutErrors` | error counters |

**Labels:** `device_name`, `role`, `site`, `vendor`, `instance`, `ifIndex`,
`ifDescr`, `ifName`, `snmp_module`.

### Recording rules (pilot-compatible)

| Recording name | Source + `interface_name` |
|----------------|---------------------------|
| `interface_status` | `ifOperStatus` (ifDescr, else ifName) |
| `interface_octets_*` | HC octets |
| `interface_errors_*` | error counters |

Grafana (host **:3300**): folder **Convergence**.

## Manual / legacy enable (Phase 8)

```bash
cd deploy/convergence
docker compose --env-file .env --profile device-snmp up -d
# Edit prometheus job device_snmp or re-run apply
./deploy/convergence/smoke-device-snmp.sh
```

## Alerts

See `prometheus/alerts/device.rules.yml` and
[`docs/CONVERGENCE-ALERT-SAFETY.md`](../../../../docs/CONVERGENCE-ALERT-SAFETY.md).

Do **not** reintroduce per-`ifIndex` admin-up/oper-down as `investigate=true`.

## Config

See `config/convergence.example.yaml` → `device_telemetry.snmp` and
`specs/067-convergence/telemetry-setup.md`.

## K3s

`deploy/convergence/k8s/components/device-snmp/` — include from an overlay.
Phase 10 Docker apply is the primary greenfield path; K3s ConfigMap render follows.
