# NetClaw Convergence — Docker minimal (067 Phase 3+)

Single-host OBS + **convergence-api** stack for the HUD **HOME** tab
(site health, Wi‑Fi, devices, diary, triage). Paths and compose project:
`deploy/convergence` / `name: netclaw-convergence`.

| Service | Host port (default) | Role |
|---------|---------------------|------|
| convergence-api *(service id)* / image `netclaw-convergence-api` | 3080 | Health / wifi / devices / events / inventory API |
| prometheus | 9090 | Metrics + rules |
| alertmanager | 9093 | Routes alerts → host **alert-receiver** |
| blackbox | 9115 | WAN TCP/HTTP probes |
| postgres | (internal) | Events diary |
| unifi-exporter | 9899 | Optional (`--profile unifi`) |
| snmp-wireless-exporter | 9116 | Optional (`--profile generic-snmp-wireless`, T071) |

Full stack overlay (`docker-compose.full.yml`, T072) adds Loki, VictoriaMetrics,
Grafana, and speedtest — see below.

## Quick start

```bash
cd /path/to/netclaw
cp deploy/convergence/.env.example deploy/convergence/.env
# edit PGPASSWORD, JWT_SECRET, API_KEYS key string, ALERT_RECEIVER_URL

./deploy/convergence/render-config.sh
docker compose -f deploy/convergence/docker-compose.yml --env-file deploy/convergence/.env up -d --build
./deploy/convergence/smoke-docker.sh
```

### Wire the HUD

```bash
# ~/.openclaw/.env
HOME_API_URL=http://127.0.0.1:3080
HOME_API_TOKEN=dev-convergence-api-key-change-me   # must match API_KEYS[].key
systemctl --user restart netclaw-hud.service
```

Open http://localhost:3001 → **HOME**.

### UniFi metrics

```bash
# deploy/convergence/.env
UNIFI_HOST=https://<controller>
UNIFI_API_KEY=<integration-api-key>
docker compose -f deploy/convergence/docker-compose.yml --env-file deploy/convergence/.env --profile unifi up -d
```

See [adapters/unifi/README.md](./adapters/unifi/README.md).

### Second wireless vendor (generic SNMP, T071)

```bash
# deploy/convergence/.env — set SNMP target directly in prometheus/prometheus.yml
docker compose -f deploy/convergence/docker-compose.yml --env-file deploy/convergence/.env --profile generic-snmp-wireless up -d
```

See [adapters/generic-snmp-wireless/README.md](./adapters/generic-snmp-wireless/README.md).

### Full stack overlay: Loki, VictoriaMetrics, Grafana, speedtest (T072)

Additive overlay on top of the minimal stack — long-term log/metric storage,
dashboards, and active WAN bandwidth testing.

```bash
docker compose \
  -f deploy/convergence/docker-compose.yml \
  -f deploy/convergence/docker-compose.full.yml \
  --env-file deploy/convergence/.env \
  --profile full \
  up -d --build
```

| Service | Host port (default) | Role |
|---------|---------------------|------|
| loki | 3100 | Log aggregation (14d retention) |
| victoriametrics | 8428 | Long-term metrics (365d) |
| grafana | 3300 | Dashboards (Prometheus + Loki + VictoriaMetrics datasources pre-provisioned) |
| pushgateway | 9091 | Receives speedtest results for Prometheus scrape |
| speedtest | (none) | Runs Ookla CLI hourly, pushes to pushgateway |

Just the speedtest path (no Loki/Grafana/VM):

```bash
docker compose -f deploy/convergence/docker-compose.yml -f deploy/convergence/docker-compose.full.yml \
  --env-file deploy/convergence/.env --profile speedtest up -d
```

Open Grafana at http://localhost:3300 (anonymous viewer access by default).

## Alert-receiver (T031)

Alertmanager posts to `ALERT_RECEIVER_URL` (default
`http://host.docker.internal:8099/webhook`). Compose sets
`extra_hosts: host.docker.internal:host-gateway` so Linux can reach the NetClaw
host where `services/alert-receiver` listens.

Re-render after changing the URL:

```bash
./deploy/convergence/render-config.sh
docker compose -f deploy/convergence/docker-compose.yml --env-file deploy/convergence/.env up -d alertmanager
```

## Installer profile (Phase 5)

```bash
./scripts/install.sh --profile convergence
./scripts/setup.sh    # adapters + deploy mode + ensure guardian-claw
python3 scripts/ensure-guardian-claw.py   # idempotent alone
```

Config example: `config/home-noc.example.yaml`  
Pilot cutover: [DEPRECATION-PILOT.md](./DEPRECATION-PILOT.md)

## K3s (Phase 4)

Same services via kustomize under [`k8s/`](./k8s/). Namespace **`netclaw-convergence`**.

```bash
cp deploy/convergence/k8s/secret.example.yaml deploy/convergence/k8s/secret.yaml
# edit secrets; set alertmanager webhook URL in k8s/base/configs/alertmanager.yml
docker build -t netclaw-convergence-api:local ui/convergence-api
# load image into cluster (k3s example)
docker save netclaw-convergence-api:local | sudo k3s ctr images import -
kubectl apply -f deploy/convergence/k8s/secret.yaml
kubectl apply -k deploy/convergence/k8s/overlays/greenfield
./deploy/convergence/k8s/smoke-k8s.sh
```

See [k8s/README.md](./k8s/README.md), [k8s/OVERLAY-PILOT.md](./k8s/OVERLAY-PILOT.md) (vs pilot OBS), [k8s/SMOKE.md](./k8s/SMOKE.md).

## Files

```text
docker-compose.yml
docker-compose.full.yml   # T072 overlay: loki, victoriametrics, grafana, speedtest
.env.example
render-config.sh
smoke-docker.sh
prometheus/prometheus.yml
prometheus/alerts/home.rules.yml
alertmanager/alertmanager.yml[.tmpl]
blackbox/blackbox.yml
loki/loki-config.yaml
grafana/provisioning/datasources/datasources.yml
speedtest/run.py
adapters/unifi/
adapters/nautobot/              # T070 SoT adapter
adapters/generic-snmp-wireless/ # T071 second wireless vendor
k8s/                    # Phase 4 kustomize base + overlays
```
