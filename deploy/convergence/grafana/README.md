# Convergence Grafana (Phase 10 curated suite)

## Access

| Item | Value |
|------|--------|
| **Host URL** | `http://127.0.0.1:3300` (Docker full stack — **not** :3000) |
| **Default login** | see `deploy/convergence/.env` / compose (`GF_SECURITY_ADMIN_*`) |
| **Folder** | **Convergence** (file provider) |

Compose: `docker compose -f docker-compose.yml -f docker-compose.full.yml --profile full up -d grafana`

## Datasource UIDs (provisioned)

| UID | Name | URL (in-network) |
|-----|------|------------------|
| `prometheus` | Prometheus | `http://prometheus:9090` |
| `loki` | Loki | `http://loki:3100` |
| `victoriametrics-longterm` | VictoriaMetrics - Long Term | `http://victoriametrics:8428` |

Defined in `provisioning/datasources/datasources.yml`.

## Curated suite (default operator path)

| Board title | UID | Purpose |
|-------------|-----|---------|
| **Home NOC — Network Guardian** | `network-guardian` | Site health, WAN probes, UniFi, edge traffic (`convergence:*`) |
| **Campus Interfaces** | `network-interfaces` | Named IF traffic/status (`interface_*` + `interface_name`) |
| **Campus Switches (summary)** | `convergence-device-snmp` | device_snmp KPIs + named status table |
| **WAN Speedtest — Bandwidth Validation** | `wan-speedtest` | WAN/edge bandwidth checks |
| **NetClaw Agent — Tokens & Cost** | `netclaw-tokens` | `netclaw_model_*` agent metrics |

Tags: `curated`, `phase10`, plus board-specific tags.

## Optional / not default-curated

Boards titled **`[optional] …`** and tagged `optional` / `not-default-curated`:

| Board | Why optional |
|-------|----------------|
| NetFlow Overview | Needs goflow2 collector (not default full stack) |
| NetClaw Logs / Operations | Loki + log forward deep-dive |
| Model quota watch variants | Secondary to tokens board |

## Metric contract (dashboards)

Prefer recording rules from `prometheus/alerts/device-recording.rules.yml`:

- `interface_status`, `interface_octets_{in,out}_bytes_total`, `interface_errors_{in,out}_total`
- Label **`interface_name`** (from ifDescr, else ifName) — never ifIndex-only legends

WAN health: `convergence:health_score`, `convergence:wan_latency_ms:avg`, `convergence:wan_loss_ratio:5m`.

## Reload

Dashboards auto-reload every 30s from the bind-mounted JSON path. After git pull:

```bash
# optional hard restart
docker compose -f deploy/convergence/docker-compose.yml \
  -f deploy/convergence/docker-compose.full.yml --env-file deploy/convergence/.env \
  restart grafana
```

## Spec

`specs/067-convergence/telemetry-setup.md` · tasks T132–T133 · SC-012.
