# Quickstart: BGP Route Observability

**Feature**: `031-bgp-route-observability`

## Prerequisites

- Part 13 observability stack running (`docker compose -f observability/docker-compose.observability.yml up -d`)
- ContainerLab topology on `clab-mgmt` (192.168.220.0/24)
- SNMP `public` on devices; syslog to `192.168.220.200:1514`
- Spec-kit initialized (`.specify/` present in repo root)

## Spec-Kit Commands

From repo root with your AI agent:

```text
/speckit.specify   # already captured in specs/031-bgp-route-observability/spec.md
/speckit.plan      # plan.md
/speckit.tasks     # tasks.md (this feature)
/speckit.implement # execute current phase from tasks.md
/speckit.analyze   # before Phase 5 — cross-artifact consistency
```

## Phase Checkpoints

### Phase 1 — Router BGP metrics

```bash
cd /home/ubuntu/netclaw

# Lab must be running (devices on clab-mgmt)
docker network inspect clab-mgmt >/dev/null || \
  (cd ~/Nautobot-Workshop/clabs && sudo clab deploy --topo nautobot-workshop-topology.clab.yml)

python3 observability/otel-collector/generate-config.py
docker compose -f observability/docker-compose.observability.yml up -d --build bgp-snmp-exporter
docker compose -f observability/docker-compose.observability.yml restart otel-collector victoriametrics
sleep 90

# Checkpoint script (exporter :9102 + VM scrape)
bash scripts/validate-bgp-metrics.sh --phase 1

# Manual: RR1 peer 100.0.254.13 prefixes = 4
curl -sf 'http://localhost:8428/api/v1/query' \
  --data-urlencode 'query=netclaw_bgp_peer_prefixes_received{device_name="rr1",neighbor="100.0.254.13"}'
```

**Canonical Phase 1 source**: `observability/exporters/bgp_snmp_exporter.py` → VictoriaMetrics job `netclaw-bgp-snmp` (not Protocol MCP).

### Phase 2 — Jitter + syslog

```bash
bash scripts/validate-bgp-metrics.sh --phase 2

# Manual checks
curl -sf 'http://localhost:8428/api/v1/query' \
  --data-urlencode 'query=netclaw_path_jitter_ms{device_name="pe2"}'

curl -sf -G 'http://localhost:3100/loki/api/v1/labels' | jq '.data | index("device_name")'
curl -sf -G 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={device_name=~".+"} |~ "(?i)BGP"'
```

### Phase 3 — BMP pipeline

```bash
cd /home/ubuntu/netclaw

docker compose -f observability/docker-compose.observability.yml \
  -f observability/docker-compose.bmp.yml up -d --build
sleep 45

bash scripts/validate-bgp-metrics.sh --phase 3

# Manual: BMP collector listens on clab-mgmt for production peers
docker ps --filter name=gobmp --filter name=redpanda --filter name=bgp-bmp-consumer
curl -sf http://localhost:9100/metrics | grep netclaw_bmp_consumer_up
```

**Topics**: gobmp publishes OpenBMP-equivalent parsed JSON to `gobmp.parsed.*` (e.g. `gobmp.parsed.unicast_prefix_v4`). The consumer maps `add`/`del` → `netclaw_bgp_prefix_*`. Cisco IOL does not speak BMP — metrics stay idle until a BMP-capable router peers to `192.168.220.205:5000`.

### Phase 4 — gNMI stream

```bash
docker compose -f observability/docker-compose.observability.yml \
  -f observability/docker-compose.gnmi.yml up -d --build
bash scripts/validate-bgp-metrics.sh --phase 4

curl -sf 'http://localhost:8428/api/v1/query' \
  --data-urlencode 'query=netclaw_bgp_peer_state{source="gnmi",device_name="west-spine01"}'
```

### Phase 6 — Golden config BMP + gNMI

```bash
# Sync datasource context (bmp/gnmi blocks) into Nautobot, then render + deploy
python3 scripts/nautobot-push-observability.py
bash scripts/validate-bgp-metrics.sh --phase 6
```

Push template changes to `nautobot_workshop_golden_config_templates` on GitHub and run **Git Repository Sync** in Nautobot for intended-config API parity.

### Phase 5 — Alerts, skills, baselines

```bash
docker restart grafana   # reload provisioned netclaw alert rules
bash scripts/validate-bgp-metrics.sh --phase 5

# Scenario B (PE1 Gi2 shutdown) — see docs/baselines/bgp-route-stability.md
# Invoke bgp-route-stability-watch — netclaw_* + Loki + pyATS (no Protocol MCP RIB)
```

## Key URLs

| Service | URL |
|---------|-----|
| VictoriaMetrics | http://192.168.220.201:8428 |
| Grafana | http://192.168.220.203:3000 |
| Loki | http://192.168.220.202:3100 |
| BGP dashboard | Grafana → BGP Route Stability & Path Quality |

## Architecture Doc

See [docs/architecture/bgp-route-observability.md](../../docs/architecture/bgp-route-observability.md)

## Blog

Part 15 rewrite: [docs/blogs/blog-part15-route-stability-observability.md](../../docs/blogs/blog-part15-route-stability-observability.md)