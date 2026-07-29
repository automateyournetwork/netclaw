# Phase 1 Data Model: NCFED Mobile Biometrics and Capture

No new tables (research D1/D5/D6) — extends existing columns/values only.

## Entities

### Capture Capability (in `member.scope`, no schema change)

```json
{"name": "camera.capture", "type": "tool", "tier": "specialty"}
{"name": "camera.record_video", "type": "tool", "tier": "specialty"}
{"name": "audio.record", "type": "tool", "tier": "specialty"}
```

Written by `n2n/edge/register_capabilities` (replaces prior capture entries in `scope`,
leaving any other entries untouched); read unchanged by `RiskRouter.covers()`/`candidates()`.
Absence = disabled (FR-007a) — there is no "advertised but disabled" state to represent.

### Biometric Approval Resolution (existing `approval_request` row, one new `resolved_via` value)

| Field | Value when resolved via phone |
|-------|-------------------------------|
| `resolved_via` | `"biometric"` (new value; existing column, existing free-text semantics) |
| everything else | unchanged — same fields any resolution already carries |

### Capture (ephemeral — travels as message content, not a persisted entity)

```json
{"content_type": "image", "content": "<base64>", "caption": "what am I looking at?"}
```

Phone-initiated (US2): an optional `attachment` field on `n2n/edge/ask`'s existing request
shape. Border-requested (US3): the RESULT of `n2n/edge/capture`, same shape.

### Approval Push Payload (new `content_type` on the EXISTING `n2n/edge/message`, research D5)

```json
{
  "content_type": "approval",
  "approval_id": 42,
  "device": "R2-Toronto",
  "change": "shutdown interface Gi0/1",
  "reason": "flapping BGP session",
  "requesting_agent": "netclaw-core",
  "risk_name": "acme-ops",
  "pushed_at": "2026-07-23T14:00:00Z"
}
```
