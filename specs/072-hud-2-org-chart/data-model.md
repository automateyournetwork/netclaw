# Phase 1 Data Model: HUD 2.0

Feature: `072-hud-2-org-chart` · Date: 2026-07-27

The HUD owns no persistent state. Every entity below is derived, in-memory, from
`GET /api/n2n` (and, for retained panel renderers only, `GET /api/graph`). No
schema change and no server change (FR-019).

---

## Source payload (existing, unchanged)

### `n2n.risk`
| Field | Type | Use |
|---|---|---|
| `role` | `"border"` \| other | `!= "border"` must still render structure (FR-033b) |
| `risk_name` | string | Border node label |
| `member_count`, `members_active` | int | Header counts |

### `n2n.peers[]` — eN2N, external band
| Field | Type | Use |
|---|---|---|
| `identity` | string | **Dedup key** (FR-014) |
| `display_name` | string \| null | Label; falls back to `identity` (FR-015) |
| `state` | `federated` \| `severed` | Link style (FR-010) |
| `channel_state` | `unknown` \| `reconnecting` \| `unreachable` | Link style |
| `in_flight_tasks[]` | array | Activity badge |

> Live feed returns **`Hermes` twice** with conflicting `state`
> (`severed` + `federated`). Dedup by `identity`; **most restrictive state wins**
> (FR-014).

### `n2n.members[]` — iN2N, internal band and edge lane
| Field | Type | Use |
|---|---|---|
| `member_id` | `<risk>/<name>` | Identity; label fallback source (FR-015) |
| `display_name` | string \| null | **Null for both live edge nodes** — must not render blank |
| `node_type` | `agent` \| `edge` | `edge` → edge lane, never the member chart (FR-007) |
| `state` | `active` \| `provisioned` \| `unreachable` \| `quarantined` | Health input |
| `live` | bool | **Primary** health input — disagrees with `state` (5 active vs 4 live) |
| `heartbeat_age_s` | number \| null | WARM/FAULT discriminator (FR-008) |
| `skills[]` | string[] | Category derivation + tool expansion |
| `specialty_count` | int | Collapsed tool count (FR-024) |

### Integration catalog (existing, in `server.js`)
72 entries × `{ id, name, category, prefixes[] }`, 22 distinct categories.
**Passed as an argument**, never imported, so vendor neutrality is testable.

---

## Derived entities

### `HealthState` — enum (FR-008)

| Value | Derivation | Precedence |
|---|---|---|
| `HOT` | `live === true` | 1 (checked first) |
| `FAULT` | `state ∈ {unreachable, quarantined}` **or** (`heartbeat_age_s != null` and `> WARM_THRESHOLD_S`) | 2 |
| `WARM` | `heartbeat_age_s != null` and `<= WARM_THRESHOLD_S` | 3 |
| `COLD` | otherwise (never seen — `heartbeat_age_s` null/absent) | 4 (default) |

`WARM_THRESHOLD_S = 900` — a single named constant (FR-008a).

Precedence matters: it is evaluated top-down, so an explicitly `unreachable`
member is FAULT regardless of heartbeat age, and a member with no heartbeat
history is COLD rather than FAULT. **COLD (never started, normal) and FAULT
(died, needs attention) must never collapse into one another** — that
distinction is the reason four states exist.

### `Category`
| Field | Type | Notes |
|---|---|---|
| `name` | string | From the catalog, or `"Uncategorised"` (FR-006a) |
| `members[]` | Member[] | Ordered within the category |
| `heat` | int | Count of HOT members — ordering input |
| `column`, `row` | int | Assigned once (FR-034) |

Derivation: `member.skills[]` → first matching `integration.prefixes[]` →
`integration.category`; the **most frequent** category among a member's skills
wins; no match → `Uncategorised`. Measured: 25/29 members, 93% of agent members.

### `ChartNode`
| Field | Type | Notes |
|---|---|---|
| `id` | string | `identity` (peer) or `member_id` (member/edge) |
| `kind` | `peer` \| `border` \| `member` \| `edge` | Band assignment |
| `label` | string | Never blank — falls back to `member_id` tail (FR-015) |
| `health` | HealthState | Members and edges only |
| `position` | `{x, y, z}` | **Immutable for the session** (FR-034) |
| `expanded` | bool | Runtime only; not positional |
| `toolCount` | int | Shown when collapsed (FR-024) |

### `Band` — three, fixed
`external` (north, y > boundary) · `border` (centre, y = 0) · `internal`
(south, y < boundary). Plus `edgeLane`, flanking the Border **inside** the
boundary but outside the member chart (FR-007). Bands render even when empty
(FR-033).

### `LinkStyle` — six distinct (FR-010/011)
`en2n-healthy` · `en2n-unreachable` · `en2n-severed` · `in2n-healthy` ·
`in2n-cold` · `edge-push` (asymmetric Border→device, FR-011).

---

## State transitions

Only **appearance** changes at runtime. Position is assigned once (FR-034).

```
                 heartbeat within 900s
        HOT ──────────────────────────► WARM
         ▲                                │  age > 900s
         │ live=true                      ▼
        COLD ◄──(never seen)         FAULT ◄── state=unreachable|quarantined
         └──────────── live=true ──────────┘
```

A transition repaints the node. It **must not** move it, reorder its category,
or re-pack the chart (FR-034a) — a claw that fails changes how it looks, never
where it is.

---

## Validation rules

| Rule | Source | Enforced in |
|---|---|---|
| Peers deduped by `identity`; most restrictive state wins | FR-014 | `normalize.js` |
| No node renders a blank label | FR-015 | `normalize.js` |
| `node_type=edge` never enters the member chart | FR-007 | `layout.js` |
| Every member lands in exactly one category | FR-006a | `categorize.js` |
| Unmatched members → `Uncategorised`, never dropped | FR-006a | `categorize.js` |
| Health precedence HOT → FAULT → WARM → COLD | FR-008 | `health.js` |
| Category order computed once per session | FR-006b, FR-034 | `ordering.js` |
| Positions stable across polls | FR-034 | `layout.js` |
| New member appends without displacing siblings | FR-034b | `layout.js` |
| Correct at 0, 1, 29, 100 members | FR-029, FR-033 | fixtures × all modules |
