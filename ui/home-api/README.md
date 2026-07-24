# NetClaw Home API (`ui/home-api`)

API backend for the Visual HUD **HOME** tab (feature **067-home-noc**).

Lifted from `network-guardian-web` (Network Guardian). Primary consumers:

1. HUD `server.js` proxy at `/api/home/*`
2. NetClaw alert-receiver (events POST/PATCH)
3. Optional direct operators

## Dual-run (pilot)

Until Docker/K3s Home deploy lands, the HUD can point at the **existing** pilot:

```bash
# ~/.openclaw/.env or netclaw/.env
HOME_API_URL=https://network-guardian.localedgedatacenter.com
HOME_API_TOKEN=<same as NETWORK_GUARDIAN_TOKEN / API key>
# aliases accepted:
# NETWORK_GUARDIAN_URL / NETWORK_GUARDIAN_TOKEN
```

Local process (optional, needs Prometheus/Postgres reachable):

```bash
cd ui/home-api
cp .env.example .env   # fill PROMETHEUS_URL, PG*, API_KEYS, JWT_SECRET
npm install
npm start              # PORT=3080 recommended so it does not collide with HUD :3001
```

## API-first

EJS pages under `views/` remain for legacy/pilot parity; the NetClaw Home product UI is the HUD HOME tab, not these views.

## Spec

See `specs/067-home-noc/`.
