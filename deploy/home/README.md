# NetClaw Home — Docker minimal (067 Phase 3)

Single-host OBS + home-api stack for the HUD **HOME** tab.

| Service | Host port (default) | Role |
|---------|---------------------|------|
| home-api | 3080 | Health / wifi / devices / events API |
| prometheus | 9090 | Metrics + rules |
| alertmanager | 9093 | Routes alerts → host **alert-receiver** |
| blackbox | 9115 | WAN TCP/HTTP probes |
| postgres | (internal) | Events diary |
| unifi-exporter | 9899 | Optional (`--profile unifi`) |

## Quick start

```bash
cd /path/to/netclaw
cp deploy/home/.env.example deploy/home/.env
# edit PGPASSWORD, JWT_SECRET, API_KEYS key string, ALERT_RECEIVER_URL

./deploy/home/render-config.sh
docker compose -f deploy/home/docker-compose.yml --env-file deploy/home/.env up -d --build
./deploy/home/smoke-docker.sh
```

### Wire the HUD

```bash
# ~/.openclaw/.env
HOME_API_URL=http://127.0.0.1:3080
HOME_API_TOKEN=dev-home-api-key-change-me   # must match API_KEYS[].key
systemctl --user restart netclaw-hud.service
```

Open http://localhost:3001 → **HOME**.

### UniFi metrics

```bash
# deploy/home/.env
UNIFI_HOST=https://<controller>
UNIFI_API_KEY=<integration-api-key>
docker compose -f deploy/home/docker-compose.yml --env-file deploy/home/.env --profile unifi up -d
```

See [adapters/unifi/README.md](./adapters/unifi/README.md).

## Alert-receiver (T031)

Alertmanager posts to `ALERT_RECEIVER_URL` (default
`http://host.docker.internal:8099/webhook`). Compose sets
`extra_hosts: host.docker.internal:host-gateway` so Linux can reach the NetClaw
host where `scripts/alert-receiver` listens.

Re-render after changing the URL:

```bash
./deploy/home/render-config.sh
docker compose -f deploy/home/docker-compose.yml --env-file deploy/home/.env up -d alertmanager
```

## Files

```text
docker-compose.yml
.env.example
render-config.sh
smoke-docker.sh
prometheus/prometheus.yml
prometheus/alerts/home.rules.yml
alertmanager/alertmanager.yml[.tmpl]
blackbox/blackbox.yml
adapters/unifi/
```
