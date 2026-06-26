# NetClaw Alert Receiver

Lightweight webhook server that accepts Prometheus Alertmanager notifications, enriches them with device context from your source of truth, and triggers NetClaw investigation.

## Architecture

```
Prometheus (alert rules fire)
    │
    ▼
Alertmanager (192.168.3.250:9093)
    │
    │ POST /webhook
    ▼
Alert Receiver (192.168.3.252:8099)
    │
    ├── 1. Parse Alertmanager payload
    ├── 2. Extract hostname/instance from labels
    ├── 3. Lookup device in Nautobot (or local inventory.yaml)
    ├── 4. Build investigation prompt with device context
    ├── 5. POST to OpenClaw gateway → triggers NetClaw skill
    └── 6. (Optional) Post notification to Discord
```

## Setup

```bash
cd scripts/alert-receiver
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
```

## Run

```bash
python server.py
```

Or with uvicorn directly:

```bash
uvicorn server:app --host 0.0.0.0 --port 8099
```

## Test

Send a test alert:

```bash
curl -X POST http://localhost:8099/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "version": "4",
    "status": "firing",
    "receiver": "netclaw",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "InstanceDown",
        "instance": "pfsense:9100",
        "severity": "critical",
        "job": "network_devices"
      },
      "annotations": {
        "summary": "pfsense has been down for more than 2 minutes",
        "description": "The node_exporter on pfsense is unreachable."
      },
      "startsAt": "2026-06-26T10:00:00Z",
      "fingerprint": "abc123"
    }]
  }'
```

Check health:

```bash
curl http://localhost:8099/health
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERT_RECEIVER_HOST` | `0.0.0.0` | Bind address |
| `ALERT_RECEIVER_PORT` | `8099` | Listen port |
| `NAUTOBOT_URL` | — | Nautobot API base URL for device lookup |
| `NAUTOBOT_TOKEN` | — | Nautobot API token |
| `OPENCLAW_GATEWAY_URL` | — | OpenClaw gateway for triggering investigation |
| `OPENCLAW_HOOK_TOKEN` | — | Bearer token for OpenClaw hooks |
| `DISCORD_WEBHOOK_URL` | — | Discord webhook for alert notifications |
| `LOG_LEVEL` | `INFO` | Python log level |

## Device Lookup Order

1. **Nautobot** — queries `/api/dcim/devices/?name=<hostname>` for IP, platform, role, site
2. **Local inventory** — checks `inventory.yaml` for hostname match
3. **Passthrough** — if unresolved, uses the instance label as-is (assumes it's an IP)

## Alertmanager Integration

See `alertmanager-snippet.yaml` for the config to add to your OBS VM Alertmanager.

## Adding Devices

Either:
- Add the device to Nautobot (preferred — single source of truth)
- Add an entry to `inventory.yaml` (quick fallback for devices not yet in SoT)
