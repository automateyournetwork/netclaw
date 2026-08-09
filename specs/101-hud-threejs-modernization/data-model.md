# Phase 1 Data Model: HUD three.js Modernization

**Feature**: 101-hud-threejs-modernization
**Date**: 2026-08-06
**Input**: [spec.md](./spec.md) · [research.md](./research.md) · [plan.md](./plan.md)

**No persistence, no schema, no API change.** Every entity here is derived client-side from a
`GET /api/n2n` response and lives for one poll interval. FR-039 forbids touching `server.js` or
the endpoint contract.

---

## 1. The measured defect this model exists to fix

`nodes.js` treats peers as **structural**, so they skip the four-state health treatment
entirely and get their colour from `colorForStructural()`:

```js
if (node.kind === 'border') return 0xffd97a;
if (node.severed)            return 0xa85c5c;   // luminance 108
if (node.channelState === 'unreachable' || node.channelState === 'reconnecting')
                             return 0x86a9cc;   // luminance 164
return 0x8ad6ff;                                // luminance 201  ← the catch-all
```

Three colours, one fixed octahedron, no motion. **`stale` is never read, and
`channel_state: "unknown"` falls through to the healthy default.** Against the live feed:

| Peer | `state` | `channel_state` | `stale` | Renders as |
|---|---|---|---|---|
Nate | federated | `up` | false | `0x8ad6ff` healthy |
**Byrn** | federated | `unknown` | **true** | **`0x8ad6ff` — identical to Nate** |
**Nicholas** | federated | `unknown` | **true** | **`0x8ad6ff` — identical to Nate** |
**Hermes** (`as65008`) | federated | `unknown` | **true** | **`0x8ad6ff` — identical to Nate** |
**AB** | federated | `unknown` | null | **`0x8ad6ff` — identical to Nate** |
**Carapace** | federated | `unknown` | null | **`0x8ad6ff` — identical to Nate** |
Hermes (`as65007`) | severed | `unknown` | null | `0xa85c5c` severed |

**Five of seven peers are visually indistinguishable from the one healthy peer.** That is US3's
whole justification, and it is a data-mapping defect rather than a rendering one — which is why
the fix belongs in pure `src/orgchart/`, not in the render layer.

---

## 2. `PeerViewState` — derived, pure

Computed by `src/orgchart/liveness.js` from one `/api/n2n` peer row. Six states, ordered
most-known-good to least. Precedence is top-down: the **first** matching rule wins, so a severed
peer is never reported as live regardless of other fields.

| State | Rule | Meaning to an operator |
|---|---|---|
`SEVERED` | `state === 'severed'` | Deliberately cut. Terminal until re-enrolled. |
`UNREACHABLE` | `channel_state ∈ {unreachable, reconnecting}` | Was reachable, is not now. Actionable. |
`STALE` | `stale === true`, or inventory older than the staleness horizon | Federated, but what we know is old. |
`UNKNOWN` | `inventory_received_at == null` | Never told us anything. **Not** a failure (FR-016/017). |
`IDLE` | federated, no live channel, inventory fresh | Normal steady state. Nothing wrong. |
`LIVE` | `channel_state === 'up'` | Channel up right now. |

`LIVE` is last in the table but checked **first** in precedence — an `up` channel overrides
everything below it.

### Why `UNKNOWN` is its own state and not folded into `STALE`

FR-016 requires `unknown` be distinct from both healthy and dead, and FR-017 forbids
overstating confidence. AB and Carapace have never sent an inventory. Rendering them as `STALE`
would assert their data went bad; rendering them as healthy is today's bug. "We have never
heard from this peer" is a third thing and the only honest one.

### Fields

| Field | Type | Purpose |
|---|---|---|
`identity` | string | The stable key. Shown in the panel because two peers legitimately share a `display_name` (both Hermes rows). |
`label` | string | From feature 072's `resolveLabel`/`disambiguateLabels` — never blank, never ambiguous. |
`state` | one of the six above | Drives the declared channels (see visual-contract.md). |
`freshness` | `FreshnessView` (§3) | Operator-readable inventory age. |
`chatEnabled` | boolean | Straight through. |
`inFlightTasks` | array | Straight through, for the panel. |
`presentInFeed` | boolean | **False** once the peer vanishes from the feed while selected (FR-045). |

`presentInFeed` is the only field not derivable from a single row — it needs the previous poll
for comparison, which is why §5 exists.

---

## 3. `FreshnessView` — operator terms, not timestamps

`src/orgchart/freshness.js`. FR-004 forbids showing a bare timestamp: an operator should not
have to do date arithmetic to learn a peer went quiet twelve days ago.

| Field | Type | Notes |
|---|---|---|
`receivedAt` | ISO string \| null | Raw value, retained for the tooltip. |
`ageSeconds` | number \| null | `null` when never received — distinct from `0`. |
`ageText` | string | `"just now"`, `"14m ago"`, `"12d ago"`, `"never"`. |
`judgement` | `fresh` \| `aging` \| `stale` \| `never` | The explicit call FR-004 requires. |

`judgement` is **not** a restatement of the API's `stale` flag. It is derived from age so the
HUD can say "aging" before the daemon flips `stale`, and the API flag forces `stale` when set.
Both inputs, one output — with the pessimistic reading winning, matching the precedence
principle feature 072's `normalize.js` already uses for peer state.

---

## 4. `MemberViewState` — extend, never replace

FR-013 requires consistency with feature 072's existing visual-weight rules rather than a
competing scheme. Members already resolve to `HOT` / `WARM` / `COLD` / `FAULT` via
`orgchart/health.js`, with `TREATMENTS` in `nodes.js` and a permanent greyscale-separability
test in `treatments.test.js`.

**This feature does not touch that.** Members are already correctly differentiated by `live`
state. The member-side work is limited to confirming no regression. All new state modelling is
peer-side, because that is where the defect is.

---

## 5. `FeedState` — freeze and flag

`src/orgchart/feed-state.js`. Implements FR-041/042/043 from the Q1 clarification. In-memory,
one instance for the page's lifetime.

| Field | Type | Purpose |
|---|---|---|
`lastGood` | payload \| null | The last successfully parsed `/api/n2n` response. |
`lastGoodAt` | epoch ms \| null | Drives the age reported by FR-042. |
`consecutiveFailures` | number | For the scene-level indicator. |
`degraded` | boolean | True while the most recent poll failed. |

### Rules

- A poll that throws, returns non-2xx, or fails to parse is a **failure**: `lastGood` is
  retained untouched and **no** per-entity liveness is recomputed (FR-041). The scene keeps
  rendering `lastGood`.
- While `degraded`, the HUD shows a scene-level stale-data indicator carrying the age of
  `lastGoodAt` (FR-042).
- A successful poll clears `degraded` and resets `consecutiveFailures` on the next tick, with no
  reload and no acknowledgement (FR-043).
- **A successful poll containing zero peers is not a failure.** It is a real, renderable state
  (fresh install) and must reach the empty-state path feature 072 already defines — conflating
  "the daemon says nothing is federated" with "I could not reach the daemon" would be the same
  class of error in the opposite direction.

**Why this is pure and tested**: the decision "is this a failure, and what do we show" is the
part most likely to be wrong and most dangerous when wrong — a bug here fabricates an outage.
Putting it in `src/orgchart/` means it is unit-tested, whereas the render layer has no coverage
at all (plan.md, recorded weakness).

---

## 6. `SelectionState` — orthogonal by construction

Extends what `main.js` already holds in `state.selected`.

| Field | Type | Purpose |
|---|---|---|
`kind` | `local-core` \| `member-core` \| `federation-peer` \| … | Now includes the previously-missing `federation-peer` (FR-001/002). |
`nodeId` | string \| null | Which mesh carries the treatment. |
`stillPresent` | boolean | Mirrors `presentInFeed`; false drops the scene treatment while the panel persists (FR-045). |

**Invariant (FR-009)**: at most one node reads as selected. Selection is a **separate visual
channel** from state (visual-contract.md §2), never a modification of the state channels —
otherwise selecting a stale peer would make it look healthy, which is the collision plan.md
names as the primary risk.

---

## 7. State transitions

```
        ┌──────────────── poll succeeds ────────────────┐
        ▼                                              │
   ┌─────────┐   poll fails    ┌────────────────────┐   │
   │ current ├────────────────►│ degraded           │───┘   FR-043: recovery needs
   │ (live)  │                 │ (frozen @ lastGood)│       no reload, no ack
   └────┬────┘                 └────────────────────┘
        │                        · per-entity liveness NOT recomputed  (FR-041)
        │                        · scene flags stale + age of lastGood (FR-042)
        │
        │ peer row disappears while selected
        ▼
   ┌───────────────────────────────────────────────┐
   │ panel: last known detail, marked "not in feed"│  FR-045
   │ scene: selected treatment dropped             │
   └───────────────────────────────────────────────┘
```

Peer state transitions (`LIVE → STALE → UNREACHABLE → SEVERED` and back) carry no special
handling: each poll recomputes `PeerViewState` from scratch, so a transition is simply a
different derivation. That is deliberate — there is no state machine to desynchronise, and
`FeedState` is the only thing holding memory between polls.

---

## 8. Validation rules

| Rule | Source |
|---|---|
Six peer states MUST be pairwise distinguishable in greyscale, ≥18 luminance delta | FR-014; reuses `treatments.test.js`'s existing metric and threshold |
No state may be carried by colour alone | FR-014 |
Precedence is top-down; a severed peer is never reported live | FR-017; mirrors `normalize.js` |
`ageSeconds === null` (never) MUST NOT render as `0` (just now) | FR-004 |
A failed poll MUST NOT mutate any entity's liveness | FR-041 |
Zero peers on a **successful** poll is an empty state, not a failure | §5, feature 072 first-run |
`identity` MUST appear in the panel, not only `label` | spec Edge Cases — two peers share "Hermes" |
