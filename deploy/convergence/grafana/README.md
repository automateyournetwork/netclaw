# Convergence Grafana — holistic suite (Phase 10)

## Access

| Item | Value |
|------|--------|
| **URL** | **http://127.0.0.1:3300** (not :3000) |
| **Folder** | Convergence |
| **Primary boards** | **Network** · **Security** · **NetClaw** |

Cross-links between the three boards are in each dashboard header.

## The three boards

### 1. Network (`convergence-network`)

Site-wide network health as one story:

| Section | Data |
|---------|------|
| Site overview | `convergence:health_score`, WAN latency/loss, SNMP/Wi‑Fi counts |
| WAN | blackbox `probe_success` / latency |
| Campus switching | named `interface_*` traffic, ports up, errors, down table |
| Wi‑Fi | UniFi clients, TX retries, AP uplink |
| Edge | blackbox edge HTTPS |

### 2. Security (`convergence-security`)

Posture and access, not random stats:

| Section | Data |
|---------|------|
| Posture KPIs | firing/critical ALERTS, edge mgmt, UniFi up, guest clients |
| Active alerts | `ALERTS{alertstate="firing"}` table (+ investigate label) |
| Edge & wireless | edge probe, guest vs wireless clients |
| Syslog / auth | Loki `device-syslog`, block/deny keywords, login noise |

**Data needs:** devices send syslog → host **:1514** (udp or tcp) → syslog-gateway
(RFC3164 → RFC5424) → promtail → Loki. Vendor-default BSD format is fine; see
`adapters/device-syslog/README.md`. Without a syslog source the log panels stay
empty while posture/alert/edge/wireless panels still work (spec FR-033).

Ingest health is scraped (`job=promtail`) and alerted on
(`SyslogIngestParseFailing`, `SyslogIngestNoEntries`, `LogShipDown`), because the
original failure mode here was a **silent** drop: port open, packets arriving,
Loki empty.

### 3. NetClaw (`convergence-netclaw`)

Agent plane end-to-end:

| Section | Data |
|---------|------|
| LLM by provider | `netclaw_model_*` rates + cost by `provider` / `model` / `agent` |
| Totals | input tokens table, sessions, USD total |
| Investigation pipe | alerts received, T0/T1/T2 tiers, suppressions, budget trips |
| Gateway & N2N logs | OpenClaw files + journal mesh/member units |

**Data needs:**

| Source | How |
|--------|-----|
| Token/cost metrics | `openclaw-token-exporter` → Prom job `netclaw-openclaw` (:9110) |
| Investigation metrics | host `alert-receiver` → Prom job `netclaw-alert-receiver` (:8099) |
| Gateway logs | host `/tmp/openclaw/*.log` mounted into promtail |
| Mesh / N2N / members | promtail journal scrape of user units |

## Datasource UIDs

| UID | Service |
|-----|---------|
| `prometheus` | Prometheus :9090 |
| `loki` | Loki :3100 |
| `victoriametrics-longterm` | VictoriaMetrics (optional long-term; primary boards use Prometheus) |

## Legacy boards

Pilot/ported JSON lives under `provisioning/dashboards/legacy/` and is **not**
provisioned. Re-enable only if you intentionally re-add files to `json/`.

## Reload after changes

```bash
cd deploy/convergence
docker compose -f docker-compose.yml -f docker-compose.full.yml --env-file .env \
  up -d promtail grafana
curl -s -X POST http://127.0.0.1:9090/-/reload
# Open http://127.0.0.1:3300 → Convergence → Network | Security | NetClaw
```

## Spec

`specs/067-convergence/telemetry-setup.md` · Phase 10 curated suite.
