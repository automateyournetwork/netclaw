# Phase 1 Contract: Declared Visual Channels & Panel Shape

**Feature**: 101-hud-threejs-modernization
**Date**: 2026-08-06
**Input**: [spec.md](../spec.md) FR-046 · [data-model.md](../data-model.md)

This is the artifact FR-046 requires: a declaration of **which visual channel carries which
state**, so SC-002 and SC-003 become checkable against a screenshot instead of self-graded.

It is a *contract*, not a design mock — it fixes the channels and the separability rules that
must hold, and leaves exact constants to implementation, where `treatments.test.js`-style tests
enforce the rules on every run.

---

## 1. Channel inventory

Five orthogonal channels. Channels 1–4 carry **entity state**; channel 5 carries **selection**
and must never modify 1–4.

| # | Channel | Carries | Survives greyscale? | Survives reduced-motion? |
|---|---|---|---|---|
1 | **Form** (silhouette/geometry) | state | ✅ | ✅ |
2 | **Colour + luminance** | state | ✅ (luminance) | ✅ |
3 | **Motion** (pulse) | state, **redundantly** | ✅ (n/a) | ❌ — suppressed |
4 | **Label affix** (text) | state | ✅ | ✅ |
5 | **Outline** | selection only | ✅ | ✅ |

**Motion is deliberately redundant**, carrying no information that form + colour do not already
carry. This is feature 072's established rule (`nodes.js` header, R8) and it is why suppressing
motion for `prefers-reduced-motion` cannot collapse the encoding.

---

## 2. Selection is a separate channel (FR-007/009, plan.md primary risk)

**Rule**: selection MUST be expressed via channel 5 only. It MUST NOT be expressed by raising
`emissiveIntensity`, changing colour, changing form, or changing scale.

Today's treatment is `emissiveIntensity = 1.8` plus a scale bump — i.e. it *reuses state
channels*. That is the defect behind FR-007 and it has a concrete failure mode: selecting a
`COLD`/`STALE` node brightens it toward the healthy treatment, so the operator cannot tell
whether they selected a dim node or a live one.

**Required properties**:

- Legible against all six peer states and all four member treatments.
- Legible with seven post-processing passes active, bloom included.
- Legible at both extremes of the camera's configured zoom range (FR-011).
- Fully removed on deselect, leaving no residue (FR-008).
- Static, not animated, under `prefers-reduced-motion` (FR-010).
- At most one node selected at a time (FR-009).

An outline (or equivalently a rim treatment applied outside the silhouette) satisfies these
because it occupies space the state channels do not use. Bloom is a real hazard here — an
additive glow can wash out an outline — so implementation MUST verify against the *bloom-enabled*
scene, not a bare one.

---

## 3. Peer state → channels (US3, the defect fix)

Six states from [data-model.md](../data-model.md) §2. Today all six collapse to three colours
and one form, with five of seven live peers rendering identically to a healthy one.

| State | Form (ch 1) | Luminance band (ch 2) | Motion (ch 3) | Label affix (ch 4) |
|---|---|---|---|---|
`LIVE` | solid peer silhouette | brightest | gentle pulse | — |
`IDLE` | solid peer silhouette | bright, below LIVE | still | — |
`STALE` | peer silhouette, degraded edge | mid | still | `· stale 12d` |
`UNKNOWN` | peer silhouette, hollow/open | mid-low, cool | still | `· never seen` |
`UNREACHABLE` | broken outline | low-mid, warm | urgent pulse | `· unreachable` |
`SEVERED` | severed silhouette | lowest | still | `· severed` |

### Binding rules

- **R1 — Pairwise luminance ≥ 18.** Every pair of the six states MUST differ by ≥18 ITU-R BT.709
  relative luminance. Reuses the exact metric and threshold already enforced by
  `treatments.test.js`, which caught a real collision in feature 072 (COLD landed within 10
  luminance of FAULT). Six states need a wider spread than four; if the range cannot hold six
  at ≥18, **form and label affix must carry the difference** and the test asserts that instead
  of loosening the threshold.
- **R2 — `LIVE` and `IDLE` must not be confusable with `STALE`.** These are the pairs an
  operator acts on. They are checked explicitly, not just as part of the pairwise sweep.
- **R3 — `UNKNOWN` is not a failure state** (FR-016/017). It must not share the warm/alarm hue
  family used by `UNREACHABLE` and `SEVERED`, or "we have never heard from AB" reads as "AB is
  broken."
- **R4 — Peers stay recognisable as peers.** Feature 072 gives peers a distinct octahedron so
  band membership reads at a glance. State variation MUST modulate that silhouette, not replace
  it with a member shape.
- **R5 — Label affixes are additive.** They extend the existing label produced by
  `resolveLabel`/`disambiguateLabels`; they never replace it, and never make it blank.

---

## 4. Member state → channels (unchanged)

`HOT` / `WARM` / `COLD` / `FAULT` per `nodes.js` `TREATMENTS`. **This feature changes nothing
here** (FR-013, data-model §4). Listed so the selection channel can be verified against all ten
combined states, and so a reviewer can confirm the member path was deliberately left alone.

---

## 5. Link flow → channels (US4)

| Link condition | Flow |
|---|---|
Peer state `LIVE` | directional flow, Border-ward |
`IDLE` | none |
`STALE`, `UNKNOWN`, `UNREACHABLE`, `SEVERED` | none |

- **Direction MUST correspond to something real or be non-directional** (FR-019). Absent a real
  per-link direction signal in `/api/n2n`, flow is rendered toward the Border to represent
  *inbound capability availability*, and this choice is recorded rather than left implicit.
- Flow respects `prefers-reduced-motion` (FR-020): conveyed by a static treatment when
  suppressed, so the live/not-live distinction survives.
- Flow is **redundant** with §3's state channels. A viewer who cannot see motion loses nothing.

---

## 6. Peer detail panel contract (US1)

Rendered by the new `federation-peer` branch in `setDetail`, from
`src/orgchart/peer-detail.js`'s view-model. Reuses existing `detail-grid` / `detail-row` markup —
no new panel framework.

| Row | Source | Notes |
|---|---|---|
Heading | `label` | From feature 072's disambiguation. |
Identity | `identity` | **Required.** Two peers legitimately share "Hermes"; label alone is ambiguous. |
State | `state` | The six-state value, not the raw API string. |
Channel | `channel_state` | Raw, for operator cross-reference against `n2n_health`. |
Inventory | `freshness.ageText` + `judgement` | FR-004: never a bare timestamp. |
Chat | `chat_enabled` | |
In-flight tasks | `in_flight_tasks[]` | Empty renders as an explicit "none", not a blank. |
Not-in-feed banner | `presentInFeed === false` | FR-045. Only when the peer has vanished. |

### Binding rules

- **P1 — No fallthrough** (FR-006). An unrecognised `setDetail` kind MUST NOT reach the default
  overview branch. It MUST be loud in development. The silent fallthrough *is* the reported bug:
  the panel repaints with a *different subject's* content, which is why it read as "not
  clickable" while the mesh was pickable and hover-scaling correctly.
- **P2 — Never render `undefined`.** Every row either shows a value or an explicit placeholder.
  This is why the panel is driven by the `/api/n2n` shape and not routed through `peer-core`,
  whose BGP payload (`peer.as`, `peer.routerId`, `peer.peerIp`, `peer.routesReceived`,
  `peer.adjRibIn`) is absent here and would render a panel of blanks (FR-002).
- **P3 — Both activation paths** (FR-005): pointer (`main.js:2180`) and keyboard/a11y
  (`main.js:2765`) must reach the same renderer.
- **P4 — No secrets.** Peer identities and states only; no key material, no tokens.

---

## 7. Verification mapping

| Criterion | Checked by |
|---|---|
SC-002 | Screenshot: selected node shows channel 5, distinct from unselected same-type node |
SC-003 | Screenshot with LIVE + STALE + SEVERED peers: three distinct channel combinations |
R1/R2/R3 | Unit test on the declared constants — a permanent check, not a one-off screenshot, following `treatments.test.js`'s precedent |
FR-010/020 | Reduced-motion screenshot: encoding intact with channel 3 suppressed |
FR-014 | Greyscale luminance test (R1) |
SC-001 | Click each of 7 peers, panel shows that peer's identity |
FR-045 | Remove a selected peer from the feed; panel persists with banner, scene treatment drops |
SC-010 | Stop `netclaw-mesh.service`; no peer changes to a failure appearance, scene flags stale + age |

**The greyscale and reduced-motion rules are asserted as tests, not screenshots.** They are
properties of design constants, so they hold on every run rather than for one build on one
machine — the reasoning feature 072 recorded in `treatments.test.js` and the reason it caught a
real collision.
