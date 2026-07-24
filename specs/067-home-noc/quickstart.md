# Quickstart: NetClaw Home (067)

## Spec / tracking
```bash
cd /path/to/netclaw
ls specs/067-home-noc/
# Track work in tasks.md — update checkboxes as slices land
```

## PR1 — HUD tabs
```bash
cd ui/netclaw-visual
npm install
npm run build
systemctl --user restart netclaw-hud.service
# Open http://localhost:3001 → COMMAND | HOME
```

## PR2 — Live HOME (dual-run pilot Guardian)
```bash
# ~/.openclaw/.env
HOME_API_URL=https://network-guardian.example.com
HOME_API_TOKEN=<api-key>
systemctl --user restart netclaw-hud.service
```

## PR3 — Docker minimal (this host)

Single-host stack: **postgres + prometheus + alertmanager + blackbox + home-api**  
Optional: **unifi-exporter** (`--profile unifi`).

```bash
cd /path/to/netclaw

# 1. Local secrets (never commit .env)
cp deploy/home/.env.example deploy/home/.env
# Edit: PGPASSWORD, JWT_SECRET, API_KEYS key, ALERT_RECEIVER_URL
# Keep single-quotes around JSON values in .env so Compose preserves them.

# 2. Render Alertmanager → host alert-receiver webhook
./deploy/home/render-config.sh
# Default: http://host.docker.internal:8099/webhook
# Ensure alert-receiver is listening on the host (e.g. :8099)

# 3. Start core stack
docker compose -f deploy/home/docker-compose.yml --env-file deploy/home/.env up -d --build

# 4. Smoke
./deploy/home/smoke-docker.sh

# 5. Point HUD at local home-api
# ~/.openclaw/.env
#   HOME_API_URL=http://127.0.0.1:3080
#   HOME_API_TOKEN=dev-home-api-key-change-me   # must match API_KEYS[].key
systemctl --user restart netclaw-hud.service
# Open http://localhost:3001 → HOME
```

### Optional UniFi metrics

```bash
# deploy/home/.env
#   UNIFI_HOST=https://<controller>
#   UNIFI_API_KEY=<Integration API key>
docker compose -f deploy/home/docker-compose.yml --env-file deploy/home/.env --profile unifi up -d
```

See [deploy/home/README.md](../../deploy/home/README.md) and [adapters/unifi](../../deploy/home/adapters/unifi/README.md).

### Default ports

| Service | Port |
|---------|------|
| home-api | 3080 |
| prometheus | 9090 |
| alertmanager | 9093 |
| blackbox | 9115 |
| unifi-exporter | 9899 |

## Later — Full pipeline (PR5)
```bash
./scripts/install.sh --profile home   # when catalog lands
# Setup ensures risk + guardian-claw; preserves any existing risk
```

## Deploy mode choice
| Mode | Use when |
|------|----------|
| Docker | Single host lab / easy trial |
| K3s | Already run OBS in cluster (like this pilot) |

Agent + **guardian-claw** stay on the NetClaw host by default.
