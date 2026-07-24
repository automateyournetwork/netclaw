# Quickstart: NetClaw Home (067)

## Spec / tracking
```bash
cd /path/to/netclaw
# Feature docs live in:
ls specs/067-home-noc/
# Track work in tasks.md — update checkboxes as PRs land
```

## PR1 — HUD tabs only (current slice)
```bash
cd ui/netclaw-visual
npm install
npm run build
# or npm run dev
# Production service:
systemctl --user restart netclaw-hud.service
# Open http://localhost:3001 → COMMAND | HOME
```

## Later — Docker minimal (PR3)
```bash
# After deploy/home exists:
docker compose -f deploy/home/docker-compose.yml up -d
export HOME_API_URL=http://127.0.0.1:8080   # example
systemctl --user restart netclaw-hud.service
```

## Later — Full pipeline (PR5)
```bash
./scripts/install.sh --profile home   # when catalog lands
# or --add "home-noc-core home-noc-metrics home-noc-unifi visual-hud"
# Setup ensures risk + guardian-claw; preserves any existing risk
```

## Deploy mode choice
| Mode | Use when |
|------|----------|
| Docker | Single host lab / easy trial |
| K3s | Already run OBS in cluster (like this pilot) |

Agent + **guardian-claw** stay on the NetClaw host by default.
