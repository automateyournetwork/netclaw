# UniFi adapter (Home Docker)

Pure-stdlib Prometheus exporter for UniFi Network **Integration API** keys
(same approach as the pilot `unifi-exporter` on K3s).

## Enable

```bash
cd deploy/convergence
# in .env:
#   UNIFI_HOST=https://192.168.x.x:443   # or :11443 for some consoles
#   UNIFI_API_KEY=<Integration API key>
docker compose --env-file .env --profile unifi up -d unifi-exporter
```

Core Prometheus already scrapes `unifi-exporter:9899` (job `unifi`).
If the profile is off, that target is simply down (alert `UniFiExporterDown` after 5m).

## Metrics

See header comments in `exporter.py` (`unifi_up`, clients, radio tx retries, …).

## Secrets

Never commit real API keys. Only set `UNIFI_API_KEY` in `deploy/convergence/.env` (gitignored pattern via local `.env`).
