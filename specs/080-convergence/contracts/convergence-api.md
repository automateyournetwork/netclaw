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
| GET | `/api/events/:id` | Single event (notes, RAG id, feedback) |
| POST | `/api/events` | Create (agent) |
| PATCH | `/api/events/:id` | Update status/notes/feedback |
| POST | `/api/events/:id/reinvestigate` | Need More — reopen + optional alert-receiver hook |
| GET | `/api/alerts?site=` | Firing alerts |
| GET | `/api/security?site=` | Optional firewall blocks |

### Reinvestigate (Need More)

```http
POST /api/events/:id/reinvestigate?site=home
Authorization: Bearer <api-key>
Content-Type: application/json

{ "expert_feedback": "optional operator notes" }
```

Effects:
1. Event `status` → `investigating`; `feedback_quality` → `needs_more_context`
2. Appends operator note to `investigation_notes`
3. If `ALERT_RECEIVER_URL` is set on convergence-api, POSTs to `{receiver}/reinvestigate` so the host pipe re-triggers `alert-triage` / guardian-claw

### Feedback quality (PATCH)

`feedback_quality`: `correct` | `partially_correct` | `incorrect` | `needs_more_context`  
Also set `expert_feedback` free text. UI may set `status` to `resolved` on Correct.

Compatible with existing `network-guardian-web` routes where possible to ease migration.
