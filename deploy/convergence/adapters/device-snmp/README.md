# Device SNMP (campus switches) — Phase 8 greenfield

Polls **wired infrastructure** (Cisco Catalyst, etc.) via Prometheus
`snmp_exporter` + IF-MIB. **Not** the wireless AP path
(`generic-snmp-wireless`).

## Enable (Docker)

1. Edit switch list in `deploy/convergence/prometheus/prometheus.yml` under
   job `device_snmp` (or regenerate from `config/convergence.yaml` — see
   `scripts/render-device-snmp-scrape.py`).

2. Community string: edit `adapters/device-snmp/snmp.yml` auth `community`
   (default `public`) or use SNMP v3 with the upstream generator later.

3. Start:

```bash
cd deploy/convergence
docker compose --env-file .env --profile device-snmp up -d
# reload prom if already running:
docker compose kill -s SIGHUP prometheus
```

4. Check:

```bash
curl -s 'http://127.0.0.1:9090/api/v1/query?query=ifOperStatus' | head -c 400
# or
curl -s 'http://127.0.0.1:9117/snmp?target=192.168.3.2&module=if_mib' | head
```

## Metrics (baseline)

| Metric | Meaning |
|--------|---------|
| `ifOperStatus` | 1=up, 2=down (per ifIndex) |
| `ifAdminStatus` | admin state |
| `ifHCInOctets` / `ifHCOutOctets` | traffic counters |
| `ifInErrors` / `ifOutErrors` | error counters |
| `ifDescr` | interface description |

Labels: `device_name`, `role=switch`, `site`, `instance` (device IP).

## Alerts

`prometheus/alerts/device.rules.yml`:

- `DeviceSnmpExporterDown` — snmp-device-exporter scrape failed  
- `SwitchInterfaceDown` — oper down while admin up (noisy interfaces may need
  relabel drop; tune in prod)

## Config (convergence.yaml)

See `config/convergence.example.yaml` → `device_telemetry.snmp`.

## K3s

`deploy/convergence/k8s/components/device-snmp/` — include from an overlay.

## Relation to pilot OBS

Pilot `k3s-observability-stack` OTEL SNMP is a **design reference** only.
This component is self-contained for greenfield PRs.
