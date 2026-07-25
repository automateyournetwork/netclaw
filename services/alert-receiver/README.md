# NetClaw Alert Receiver

Lightweight webhook server that accepts Prometheus Alertmanager notifications, enriches them with device context from your source of truth, and triggers NetClaw investigation.

## Architecture

```
Prometheus (alert rules fire)
    │
    ▼
Alertmanager
    │
    │ POST /webhook
    ▼
Alert Receiver (:8099)
    │
    ├── 1. Parse Alertmanager payload
    ├── 2. Extract hostname/instance from labels
    ├── 3. Lookup device in Nautobot (or local inventory.yaml)
    ├── 3b. Investigation safety rails (policy + dedup + rate + concurrency)
    ├── 4. Build investigation prompt with device context
    ├── 4b. (Optional) Scope runtime skills to the alert — shrinks token cost
    ├── 5. POST to OpenClaw gateway → triggers NetClaw skill (if admitted)
    └── 6. (Optional) Post notification to Discord
```

### Investigation safety rails

Each OpenClaw hook session can spawn the **full MCP set**. A high-cardinality
alert (e.g. per-switch-port) must never open dozens of concurrent sessions.

| Control | Default | Env |
|---------|---------|-----|
| Policy (`investigate` label, deny-list, min severity) | skip `info` + deny noisy names | `INVESTIGATE_*` |
| Fingerprint dedup | 30 min | `INVESTIGATION_DEDUP_TTL` |
| Rate limit | 3 / minute | `MAX_INVESTIGATIONS_PER_MINUTE` |
| Concurrency | 2 in-flight (no queue) | `MAX_CONCURRENT_INVESTIGATIONS` |

See **`docs/CONVERGENCE-ALERT-SAFETY.md`** for the 2026-07 incident and the
alert-authoring checklist. Metrics: `netclaw_investigations_suppressed_*` on `/metrics`.

## Setup

```bash
cd services/alert-receiver
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
| `SKILL_SCOPING_ENABLED` | `false` | Scope runtime skills to the alert before investigation |
| `SKILL_SELECTOR_PYTHON` | current python | Interpreter to run the selector (use repo venv) |
| `SKILL_SELECTOR_PINS` | safety+device set | Skills always kept regardless of alert |
| `SKILL_SELECTOR_K` | `8` | Top-k relevant skills to select |
| `SKILL_SELECTOR_RANKER` | `keyword` | `keyword` \| `embeddings` \| `auto` |

## Skill Scoping (Token Optimization)

When `SKILL_SCOPING_ENABLED=true`, the receiver scopes the runtime skills
directory to the alert-relevant subset (plus a pinned safety core) before
triggering investigation. This shrinks the skill index OpenClaw injects into the
system prompt by ~65–94% per turn, cutting quota/latency on autonomous triage.

It is **opt-in** and **fail-open**: if the selector errors or times out, the
investigation proceeds with the full catalog. See
[`docs/architecture/skill-context-scoping.md`](../../docs/architecture/skill-context-scoping.md)
for the full explanation, measurements, and caveats.

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
