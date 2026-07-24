# Contract: Home API

Base URL (from HUD): `/api/home` → proxies to `HOME_API_URL`.

Auth: Bearer JWT (humans) or API key (NetClaw/alert-receiver) — same model as Network Guardian.

## Endpoints (v1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Liveness (no auth) |
| GET | `/api/health?site=` | KPIs: score, latency, loss, bandwidth, alerts |
| GET | `/api/wifi?site=` | AP clients + retries |
| GET | `/api/devices?site=` | Edge + APs + probes |
| GET | `/api/events?site=&status=&limit=` | Diary |
| GET | `/api/events/escalated?site=` | Triage queue |
| POST | `/api/events` | Create (agent) |
| PATCH | `/api/events/:id` | Update status/notes/feedback |
| GET | `/api/alerts?site=` | Firing alerts |
| GET | `/api/security?site=` | Optional firewall blocks |

Compatible with existing `network-guardian-web` routes where possible to ease migration.
