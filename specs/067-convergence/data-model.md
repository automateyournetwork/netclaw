# Data Model: 067-convergence

## HomeSite
| Field | Type | Notes |
|-------|------|-------|
| id | string | e.g. `home` |
| name | string | display |
| thresholds | object | latency/loss/retry thresholds |
| adapters | object | firewall, wireless, sot bindings |

## HomeEvent (diary)
Aligned with existing Guardian `events` table:

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | PK |
| site | string | FK logical site |
| status | enum | investigating, resolved, escalated, logged |
| severity | enum | ok, info, watch, alert |
| alert_name | string | optional |
| alert_fingerprint | string | optional |
| message | string | one-line summary |
| root_cause | string | classification + detail |
| investigation_notes | text | |
| expert_feedback | text | optional |
| feedback_quality | enum | correct, partial, incorrect, needs_more_context |
| rag_document_id | string | optional |
| timestamps | datetime | created/updated |

## InvestigatorMember
| Field | Type | Notes |
|-------|------|-------|
| risk_name | string | `N2N_RISK_NAME` |
| member_id | string | `{risk}/guardian-claw` |
| profile | string | `network-guardian` |
| skills | list | alert-triage, wifi-diagnosis, … |
| unit | string | systemd user unit name |

## AdapterConfig (convergence.yaml)
See contracts/adapters.md.

## Metrics (external TSDB)
Not owned by Home DB: Prometheus series `convergence:*`, `unifi_*`, `probe_*`, `speedtest_*`.
