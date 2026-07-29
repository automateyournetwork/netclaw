# Feature Specification: HUD 2.0 — Top-Down Trust Org Chart

**Feature Branch**: `072-hud-2-org-chart`
**Created**: 2026-07-27
**Status**: Draft
**Input**: User description: "the orbiting space theme is clunky and hard to navigate — can we make an org-chart style top down, with external claws (eN2N) 'north' or clearly external to the org chart; mobile connections should look like iN2N but special; and then the member claws; the border in the center. DON'T touch the chat interface or the right-side info bar."

## Context: what the current HUD does and why it is hard to navigate

`ui/netclaw-visual/src/main.js` (132 KB) renders every entity as a core orbiting
a shared centroid: `CORE_CENTROID = (12, 0, 0)`, members fanned onto a ring of
radius `RISK_LAYOUT.tierRadius = 46`, edge nodes assigned one of three fixed
"close orbit" slots, peers on their own orbits. The camera is a
`PerspectiveCamera(48°)` driven by unconstrained `OrbitControls`.

Two things make it clunky, and only one of them is the theme:

1. **Free orbit destroys hierarchy.** With rotation unconstrained, any given
   frame shows the topology from an arbitrary angle. "External vs internal" and
   "who reports to whom" are relationships that only read if the viewer and the
   layout agree on which way is up. This is the dominant cause and it is a
   camera problem, not an aesthetic one.
2. **Every node is given equal visual weight** regardless of whether it matters.

### Measured state of the live data (2026-07-27, `GET /api/n2n`)

These numbers drive the layout and are not hypothetical:

| Quantity | Value |
|---|---|
| Members total | **29** |
| — `state=provisioned` (cold) | **22** |
| — `state=active` | 5 |
| — `state=unreachable` | 2 |
| — actually `live: true` | **4** (`cml`, `ipfabric`, `pyats`, `viz`) |
| `node_type=agent` / `edge` | 27 / 2 |
| eN2N peers | 5 rows (4 distinct — see FR-014) |
| Distinct `profile` values | **28 across 29 members** |

Three consequences:

- **A flat row of 29 members is unreadable at any zoom.** 25 of the 29 are cold
  or unreachable. The layout must demote them, not merely place them.
- **`profile` cannot be the org chart's middle tier.** It is effectively 1:1
  with the member (28 distinct values for 29 members) — grouping by it produces
  28 groups of one. A genuine middle tier has to come from somewhere else
  (FR-006), or the chart is a 29-wide flat fan with extra steps.
- **The chart is shallow.** Every member is depth-1 from the Border. This is a
  tiered band layout, not a general tree, so no Reingold–Tilford / tidy-tree
  algorithm is required. Row packing within bands is sufficient.

## Proposed layout

```
              ╔═ EXTERNAL — eN2N ═════════════════════════════════════╗
   NORTH      ║   ( AB )      ( Nicholas )    ( Byrn )     ( Hermes ) ║
              ║  federated     unreachable   unreachable    SEVERED   ║
              ╚═══╤═══════════════╤═══════════════╤═══════════╌╌╌╌════╝
                  │               ┊               ┊            ✂
        ══════════╪═══════════════╪═══════════════╪══════════════════════
         TRUST    │      B O R D E R   B O U N D A R Y
        ══════════╪═══════════════╪═══════════════╪══════════════════════
                  │               ┊               ┊
                       ╭──────────────────╮              ┌── EDGE LANE ──┐
   CENTRE            ╭─┤   B O R D E R    ├─╌╌╌╌╌╌╌╌╌╌╌╌►│  ( phone 1 )  │
                     │ │  johns-risk      │   push ch.   │  ( phone 2 )  │
                     │ ╰──────────────────╯              └───────────────┘
                     │
        ─────────────┴──── INTERNAL — iN2N ──────────────────────────────
                     │
       ┌─────────────┼──────────────┬─────────────┬──────────┬─── … ───┐
   HOT GROUPS FIRST (categories containing a live member lead)   COLD GROUPS →
       │             │              │             │          │
   [Device Autom.] [Labs]    [Visualization] [Uncategorised] [Security] [Observ.]
       │             │              │             │          │          │
 SOUTH ◆pyats      ◆cml           ◆viz        ◆ipfabric    ·ise      ·suzieq
       │           ·containerlab                ·forward    ·paloalto ·gtrace
       │                                                    ·nmap     ·packet
       ├─ [expanded] ──────────┐                            ·nvd
       │  pyats-health-check   │  ← FR-020: tools revealed  ·fwrule
       │  pyats-troubleshoot   │    in place, siblings do   ·fortimanager
       │  pyats-parallel-ops   │    not reflow (FR-022)
       └───────────────────────┘

   ◆ HOT (live, animated)   ◇ WARM (seen <15m, idle)
   · COLD (never started, inert)   ✖ FAULT (was reachable, now not)
   States differ in form + colour + motion — not opacity alone (FR-009a).
   FAULT is the most salient state after HOT (FR-009b) so a dead claw is
   never lost among the by-design-cold ones. Legend required (FR-009c).
```

Categories above are **derived**, not authored — see FR-006. A different
operator's Border produces different columns from the same rule.

The Border reads as the centre of a vertical stack and as the root of the
internal chart at the same time — external above the boundary, internal below,
edges in their own lane at the boundary line.

## Glossary

Three terms are used for overlapping concepts across these artifacts. They are
not interchangeable:

| Term | Means | Used in |
|---|---|---|
| **member** | The data entity from `/api/n2n` `members[]` | Data model, pure logic, requirements |
| **claw** | The user-facing name for a NetClaw agent (member or peer) | Prose, UI copy, user stories |
| **node** | A rendered object in the scene — the visual of a member, peer, Border or edge | Render layer, layout maths |

A member is data; a claw is what the operator calls it; a node is what gets drawn.

## Clarifications

### Session 2026-07-27

- Q: Does "Border in the center" conflict with "org chart top down"? → A: No.
  The Border is the center of a three-band vertical stack: external above,
  Border in the middle, internal below. It is the root of the *internal* chart
  and the boundary node for the *external* one. Both readings hold.
- Q: Should this be true 3D or a flat diagram? → A: Planar layout on a single
  plane, with depth used only for band separation and hover lift. The 3D engine
  is retained for material quality, bloom, and link animation — not for
  free-form spatial arrangement.

### Resolved 2026-07-27 (second pass)

- Q: Should the category taxonomy be a hardcoded map of this deployment's member
  names? → A: **No.** NetClaw ships to every operator, and no two deployments
  have the same members. A hardcoded list would categorise the author's lab and
  leave everyone else with an "Uncategorised" chart. The middle tier MUST be
  derived from data NetClaw already ships — see FR-006.
- Q: Should cold members be hidden behind a toggle? → A: **No — visible, but
  distinctly cold.** Coldness is information an operator wants on the face of
  the chart. Hot and cold must be unmistakably different treatments, not a
  slight opacity difference (FR-008/FR-009).
- Q: Should a member's tools be visible? → A: Yes, via per-node expand/collapse
  (FR-020).

### Session 2026-07-27 (clarify, pass 2)

- Q: FR-020 (expand tools) and US3/AC1 (click selects → detail panel) both claim
  the click. Which gesture does what? → A: **Click = select** (invokes
  `setDetail`, panel unchanged); **expand is a dedicated affordance** on the
  node (chevron/`+`). Two independent, separately discoverable actions. See
  FR-020a.

- Q: What accessibility scope does HUD 2.0 carry? → A: **Keyboard + screen
  reader via a DOM overlay** — every node focusable and labelled, arrow/tab
  traversal, Enter selects, expand affordance reachable. Reuses the existing
  CSS2D layer. Full WCAG AA conformance is out of scope. See FR-032.

- Q: FR-029b's "interactive frame rate on the reference machine" is undefined.
  What is the target? → A: **60 fps sustained on a discrete GPU** at the FR-029
  ceiling. A relative regression guard (never slower than HUD 1.0 on identical
  data) applies alongside it. See FR-029b/029c.

- Q: A fresh install has no risk, no members and no peers — and FR-030 removes
  the integration/device populations. What does a first-run HUD 2.0 render?
  → A: **Structure always visible.** Bands and the trust boundary render even
  when empty, each with an empty state and a short CTA. See FR-033.

- Q: FR-006b orders categories by heat, but the HUD polls continuously — so a
  claw changing state would re-rank its category and re-pack the whole chart,
  contradicting the spatial-memory principle behind FR-022/FR-031a. Live
  re-sort or stable order? → A: **Stable within session.** Order is computed
  once at load; live updates change appearance only. See FR-006b (amended) and
  FR-034.

### Session 2026-07-27 (clarify)

- Q: Migration strategy — hard replace the orbit layout, coexist behind a view
  toggle, or build a separate entry point? → A: **Hard replace.** The work is on
  a feature branch, so git provides the revert path; a runtime toggle would be
  redundant safety at the cost of carrying two layouts. See FR-026.
- Q: What scale must the layout handle before it is allowed to degrade?
  → A: **~100 members / ~25 categories**, all simultaneously visible, no
  virtualisation or level-of-detail required. See FR-029.
- Q: How many member health states must the visual language encode?
  → A: **Four — HOT / WARM / COLD / FAULT.** Binary would conflate "never
  started" (normal) with "died" (a fault), and both edge nodes are currently
  unreachable. WARM is derived from `heartbeat_age_s`. See FR-008.
- Q: The `#search` input currently filters the integration/device populations
  being removed. Does search carry forward? → A: **Yes — retargeted to the org
  chart** (members, categories, tool names), matching by highlight/dim in place
  rather than by hiding, so the layout never reflows. See FR-031.
- Q: The scene currently renders a second graph alongside the trust topology —
  72 integration clusters with orbiting skill sprites, plus testbed devices
  (`/api/graph`). What happens to it? → A: **Org chart only.** Integrations are
  represented solely as expanded member tools (FR-020); devices leave the 3D
  scene and remain in the right-hand panel. See FR-030.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read the trust topology at a glance (Priority: P1)

An operator opens the HUD and, without rotating, panning, or clicking anything,
can immediately answer: who is outside my organisation, who is inside it, which
of them are alive right now, and where is the boundary between the two.

**Why this priority**: This is the entire point of the redesign. Every other
story is refinement. If the first frame does not answer those four questions,
the rebuild has failed and the orbit version was no worse.

**Independent Test**: Load the HUD on a clean session. Without any input,
confirm the external peers, the Border, and the internal members are each
identifiable, and the trust boundary between external and internal is visible
as an explicit graphic element rather than implied by distance.

**Acceptance Scenarios**:

1. **Given** a loaded HUD at default camera, **When** the operator looks at the
   scene without interacting, **Then** eN2N peers appear in a band above an
   explicitly drawn trust boundary, the Border sits on the centre line, and
   iN2N members occupy the band below it.
2. **Given** 4 live members among 29 total, **When** the scene renders, **Then**
   the 4 live members are visually dominant and the 25 cold/unreachable ones are
   demoted, so live capacity is legible without counting.
3. **Given** the operator drags the mouse, **When** they attempt to orbit,
   **Then** the camera pans within the layout plane and does not rotate out of
   the top-down orientation.
4. **Given** a severed peer, **When** the scene renders, **Then** its link to the
   Border is drawn as broken//severed and is distinguishable from a merely
   unreachable peer at a glance.

---

### User Story 2 - Distinguish mobile edges from member claws (Priority: P2)

An operator can spot their enrolled phones instantly and tell them apart from
server-side member claws, without hunting through the member band.

**Why this priority**: Edge nodes are internal (enrolled members, `node_type=edge`)
but behave nothing like member claws — they are user-carried, intermittently
connected, and receive pushes rather than serving delegations. The current HUD
already special-cases them into close-orbit slots for exactly this reason; that
intent must survive the redesign.

**Independent Test**: With at least one edge node enrolled, confirm it renders in
its own lane, is not mixed into the member rows, and its link to the Border is
visually distinct from a member link.

**Acceptance Scenarios**:

1. **Given** 2 enrolled edge nodes, **When** the scene renders, **Then** they
   appear in a dedicated lane flanking the Border, inside the trust boundary but
   outside the member chart.
2. **Given** an edge node that is unreachable, **When** the scene renders,
   **Then** its last-seen age is legible without opening the detail panel.
3. **Given** an edge node with a null `display_name`, **When** the scene renders,
   **Then** a stable fallback label derived from `member_id` is shown rather
   than a blank (see FR-015).

---

### User Story 3 - Drill into any node without losing the map (Priority: P2)

Clicking any node populates the existing right-hand detail panel while the
overall chart stays in place and oriented.

**Why this priority**: The operator explicitly wants the chat interface and the
right-hand info bar kept as-is. This story exists to guarantee the redesign is
additive to them and does not change their contract.

**Independent Test**: Click a peer, a member, and an edge node in turn; confirm
the right-hand panel updates exactly as it does today and the camera does not
jump or reframe.

**Acceptance Scenarios**:

1. **Given** any node, **When** the operator clicks it, **Then** the existing
   `setDetail(kind, payload, related)` contract is invoked unchanged.
2. **Given** a selected node, **When** the detail panel is open, **Then** the
   chart remains fully visible and does not reflow.

---

### Edge Cases

- **Zero members / zero peers** (fresh Border): bands must render with an empty
  state, not collapse into an unlabelled void.
- **A member enrolling while the HUD is open**: must appear on the next poll
  without a reload, preserving the existing `refreshRiskMembers()` behaviour.
- **More edge nodes than lane slots**: must wrap or scroll, not overlap. The
  current implementation stacks a 4th phone onto the last slot; that regression
  must not be carried forward.
- **Very long display names**: must truncate with the full value available in
  the detail panel.
- **A member that is both `active` and not `live`**: state and liveness are
  distinct fields and disagree in the live data (5 active vs 4 live). The
  visual must encode `live`, not `state`, for the dominance rule in FR-008.

## Requirements *(mandatory)*

### Layout

- **FR-001**: The scene MUST be laid out as three horizontal bands on a single
  plane: external (north), Border (centre), internal (south).
- **FR-002**: An explicit trust boundary MUST be drawn between the external band
  and the Border — a visible graphic element, not implied whitespace.
- **FR-003**: eN2N peers MUST occupy the external band, above the boundary, and
  MUST NOT be rendered as children of the Border in the org chart sense.
- **FR-004**: The Border MUST sit on the centre line, and MUST be the visual
  root of the internal chart and the attachment point for external links.
- **FR-005**: iN2N member claws MUST occupy the internal band below the Border,
  arranged as a top-down chart.
- **FR-006**: Members MUST be grouped into a middle tier by **category derived
  from the shipped integration catalog**, not from a hardcoded list of member
  names. `profile` MUST NOT be used as the grouping key (it is 1:1 with the
  member).

  **This requirement exists because NetClaw ships to every operator.** No two
  deployments have the same members, so any hand-written member→category map
  categorises exactly one lab and degrades to "Uncategorised" everywhere else.
  The grouping must be a *rule*, not a *list*.

  The derivation, using data that already ships and is already maintained:

  ```
  member.skills[]  →  integration (match skill against integration.prefixes[])
                   →  integration.category
                   →  member category = most frequent category among its skills
  ```

  `ui/netclaw-visual/server.js` already defines the catalog: **72 integrations
  across 22 categories**, each with `category` and `prefixes`. It is the same
  catalog the HUD already uses to cluster skills, so the org chart inherits any
  future catalog maintenance for free, on every install.

  Measured against this deployment's live data: **25 of 29 members
  auto-categorise (86%)**; excluding the 2 edge nodes, which belong in the edge
  lane and must not be categorised at all, **25 of 27 agent members (93%)**.

- **FR-006a**: A member whose skills match no integration prefix MUST fall into
  an explicit "Uncategorised" group, never be dropped. On this deployment that
  is `ipfabric` and `forward` — both are gaps in the shipped catalog's
  `prefixes`, i.e. **data fixes to the catalog, not code changes to the chart**.
  Fixing them there improves categorisation for every NetClaw install at once.

- **FR-006b**: The layout MUST adapt to however many categories a deployment
  yields — 1 to N — with column packing and wrapping. It MUST NOT assume a
  fixed set. Categories are ordered **by heat first, then by size**, so the
  handful of hot claws lead regardless of how many cold categories exist. On
  this deployment that places Labs, Device Automation, Visualization and
  Uncategorised (the 4 hot groups) ahead of 18 cold ones.

  **This ordering is computed once per session, at load — never live.** See
  FR-034; heat ordering helps on arrival, when the operator has no spatial
  memory yet, and works against them afterwards.
- **FR-007**: Mobile edge nodes MUST render in a dedicated lane flanking the
  Border — inside the trust boundary, outside the member chart — and MUST NOT be
  interleaved with member claws.

### Visual weight

- **FR-008**: Members MUST be rendered in one of **four health states**, derived
  from the existing payload. `state` alone MUST NOT be used — it disagrees with
  liveness in live data (5 `active` vs 4 `live`).

  | State | Derivation | Meaning to the operator |
  |---|---|---|
  | **HOT** | `live == true` | Running now |
  | **WARM** | `!live` and `heartbeat_age_s` ≤ threshold | Seen recently; idle or on-demand, not a fault |
  | **COLD** | `!live` and never seen (`heartbeat_age_s` null/absent), typically `state == provisioned` | Inert by design — normal |
  | **FAULT** | `!live` and `heartbeat_age_s` > threshold, or `state` ∈ {`unreachable`, `quarantined`} | Was reachable, no longer is — needs attention |

- **FR-008a**: The WARM/FAULT threshold MUST be a single named constant, not a
  magic number scattered through the layout code. Default **900 s (15 min)**.
  The distinction that matters is COLD (never started) vs FAULT (died) — those
  MUST never share a treatment, because a fault hidden among 22 by-design-cold
  claws is precisely the failure this redesign exists to fix.
- **FR-009**: Non-HOT members MUST remain **visible by default** — never hidden
  behind a toggle. Their state is information the operator wants on the face of
  the chart, not something to go looking for.
- **FR-009a**: The four states MUST be **categorically different treatments**,
  not one treatment at four opacities. A viewer must never have to compare two
  nodes side by side to classify either. Each state SHOULD be carried by more
  than one channel at once — for example form/silhouette, colour temperature,
  and whether the node animates: HOT reads as running, WARM as idle, COLD as
  inert, FAULT as demanding attention.
- **FR-009b**: FAULT MUST be the most visually salient state after HOT. An
  operator scanning the chart for problems MUST find faults without searching,
  even when they are outnumbered ~10:1 by COLD claws.
- **FR-009c**: A legend MUST be present. Four states is past the point where an
  operator can be expected to infer the encoding.
- **FR-010**: Link styling MUST distinguish, at a glance: healthy eN2N,
  unreachable eN2N, severed eN2N, healthy iN2N, cold iN2N, and the edge/push
  channel.
- **FR-011**: The edge/push link MUST be visually distinct from a member
  delegation link, reflecting that it is asymmetric (Border → device).

### Camera and interaction

- **FR-012**: The camera MUST be constrained so the top-down orientation cannot
  be lost. Free rotation MUST be disabled; pan and zoom MUST remain.
- **FR-013**: An orthographic projection SHOULD be used so that sibling nodes at
  equal tier render at equal size, which is what makes a chart readable as a
  chart. If perspective is retained for material reasons, tier scaling MUST be
  compensated so equal-tier nodes appear equal.

### Tools / skills disclosure

- **FR-020**: Every member node MUST support expand/collapse to reveal the tools
  (skills) it holds. Collapsed is the default; the chart must be readable as a
  chart before anything is expanded.
- **FR-020a**: Expand and select MUST be **separate gestures**. Click (and tap)
  selects the node and invokes `setDetail()` — unchanged from HUD 1.0.
  Expansion MUST be driven by a dedicated affordance rendered on the node
  (chevron / `+`), never by the click that selects. Consequences:
  inspecting a claw MUST NOT reflow the chart, and expanding one MUST NOT
  change what the right-hand panel is showing.
- **FR-020b**: The expand affordance MUST be visible without hover, so the
  capability is discoverable on first sight and usable on touch. Hover-only
  affordances are not acceptable at the FR-029 node count.
- **FR-021**: An expanded member MUST show its skills from the existing
  `member.skills[]` payload — no new API call and no server change. Members
  already carry both `skills[]` and `specialty_count`.
- **FR-022**: Expansion MUST be non-destructive to the layout: sibling nodes and
  other categories MUST NOT reflow or jump when a node expands. Expansion
  SHOULD claim space that is reserved for it, or overlay, rather than
  re-packing the chart. An operator who expands a node must not lose their place.
- **FR-023**: Multiple members MAY be expanded simultaneously; the design MUST
  NOT assume single-selection. Comparing two claws' toolsets side by side is a
  primary use.
- **FR-024**: A collapsed member SHOULD indicate how many tools it holds, so the
  operator can tell a rich claw from a bare one without expanding it.
- **FR-025**: Skill disclosure MUST work for cold members too. Which tools a
  cold claw *would* bring is exactly what an operator needs when deciding
  whether to warm it.

### Data correctness (defects surfaced by this work)

- **FR-014**: Peers MUST be de-duplicated by identity before rendering. The live
  feed currently returns `Hermes` twice with conflicting states (`severed` and
  `federated`). The existing `deduplicatePeers()` MUST be applied to this feed,
  and where states conflict the more restrictive one MUST win.
- **FR-015**: A node with a null `display_name` MUST fall back to a label
  derived from `member_id`. Both live edge nodes currently have
  `display_name: null` and would otherwise render blank.

### Preservation (explicit non-goals)

- **FR-016**: The chat interface MUST NOT be modified.
- **FR-017**: The right-hand detail/info panel MUST NOT be modified. Its
  `setDetail()` contract MUST be honoured unchanged.
- **FR-018**: All existing detail-panel renderers — `renderRiskSection`,
  `renderFederationSection`, `renderEdgeNodes`, `renderPostureBadge`,
  `renderGaitTrail`, `renderChannelSecurity`, `renderReplicationJobs`,
  `renderRecentPushes` — MUST continue to work against the same data.

### Layout stability

- **FR-034**: Node and category positions MUST be **stable for the lifetime of a
  session**. Position is assigned once, on first layout, and MUST NOT change in
  response to polled state.
- **FR-034a**: Live updates MUST change **appearance only** — health state,
  links, badges, counts. A claw that fails MUST change how it looks, never
  where it is. This is the same principle FR-022 (expansion must not reflow)
  and FR-031a (search dims rather than hides) already enforce; live re-sorting
  would violate it more severely than either, because it happens unprompted.
- **FR-034b**: A member that enrols mid-session MUST be appended within its
  category without displacing existing nodes, preserving the incremental
  behaviour `refreshRiskMembers()` already provides.
- **FR-034c**: *(Optional — MAY; no task required.)* A manual re-sort/re-layout control MAY be offered, so an operator
  can opt into re-ranking after a lot of state churn. If offered it MUST be
  explicit and operator-initiated, never automatic.
- **FR-034d**: A full page reload re-computes order from current heat. Position
  stability is a within-session guarantee, not a persisted one.

### Empty and first-run states

- **FR-033**: The three bands and the trust boundary MUST render even when
  empty. A NetClaw with no risk, no members and no peers is the **normal first
  state for a new operator**, not an edge case, and with FR-030 removing the
  integration and device populations there is nothing else left to draw.
- **FR-033a**: Each empty band MUST carry its own empty state naming what
  belongs there and the action that populates it (no federated peers / no
  members enrolled / no devices paired). The empty chart is the primary
  explanation of NetClaw's trust model for a first-time user, so it MUST read
  as "nothing here yet", never as a failure.
- **FR-033b**: `buildRiskMembers()` currently early-returns unless
  `risk.role === 'border'`. Under FR-033 a non-Border install MUST still render
  the structure rather than an empty scene.
- **FR-033c**: A synthetic/demo topology MUST NOT be rendered **as a substitute
  for real data, or without the operator explicitly asking for it**. In a
  security tool, a fabricated claw that could be mistaken for a real one is a
  hazard. This prohibits filling an empty first-run chart with example claws; it
  does **not** prohibit the explicit, opt-in `?fixture=` developer loader
  (tasks T004), which renders only when deliberately requested and never in
  place of a live feed. Any fixture-sourced view MUST be visibly marked as such.
- **FR-033d**: Loading MUST be distinguishable from empty. The existing
  `setLoading(progress, text)` path MUST cover the interval before the first
  `/api/n2n` response, so a slow poll never looks like an unfederated install.

### Accessibility

- **FR-032**: Every interactive node (peer, Border, member, edge) MUST be
  reachable and operable without a pointer. A WebGL canvas exposes no focusable
  elements, so the chart MUST carry a DOM overlay of focusable, labelled
  elements positioned over the canvas — the standard technique, and the same
  mechanism `CSS2DRenderer` already provides for labels.
- **FR-032a**: Keyboard model: Tab moves between bands/categories, arrow keys
  move between siblings within one, Enter selects (equivalent to click,
  FR-020a), and the expand affordance is separately reachable.
- **FR-032b**: Each focusable node MUST expose an accessible name and its health
  state as text, so a screen-reader user receives what FR-008's visual encoding
  conveys. State MUST NOT be communicated by colour or motion alone.
- **FR-032c**: `prefers-reduced-motion` MUST be honoured. **This interacts with
  FR-009a**: motion is one of the channels distinguishing HOT/WARM/COLD/FAULT,
  so when motion is suppressed the remaining channels (form, colour
  temperature) MUST still satisfy SC-007 on their own. Reduced motion must not
  collapse the health encoding.
- **FR-032d**: *(Scope exclusion — no implementation task.)* Full WCAG 2.1 AA
  conformance is explicitly OUT of scope for this feature.

### Search and navigation

- **FR-031**: The existing `#search` input MUST be retargeted from the removed
  integration/device populations to the org chart, matching against member
  names, category names, and tool (skill) names.
- **FR-031a**: Search MUST match by **highlighting matches and dimming
  non-matches in place**. It MUST NOT hide non-matches or re-pack the layout.
  Hiding would re-flow the chart and destroy the spatial memory the layout
  exists to build — the same reasoning as FR-022.
- **FR-031b**: A search matching a tool MUST make the owning member
  discoverable even while collapsed, so an operator can find which claw holds a
  capability without expanding all of them.
- **FR-031c**: Clearing the search MUST restore the exact prior visual state,
  including which members were expanded.

### Scene scope

- **FR-030**: The 3D scene MUST render the trust org chart and nothing else.
  The integration-cluster population and the device population MUST be removed
  from the scene. This is the largest single readability win available: the
  scene currently draws two unrelated graphs — a trust topology and a
  capability catalogue — over each other.
- **FR-030a**: Integration/skill information MUST reach the operator via member
  tool expansion (FR-020), which already covers it. The integration clusters
  are a second rendering of substantially the same capability data.
- **FR-030b**: Devices MUST remain available in the right-hand detail panel and
  MUST NOT be rendered as scene objects. Devices are managed estate, not
  members of the trust org; drawing them in the chart blurs what the chart means.
- **FR-030c**: The following scene-layer functions MUST be removed, not left
  dormant: `buildIntegrations`, `buildDevices`, `createSkillSprites`,
  `computeDendritePositions`, `createDendriteMaterial`, `lightIntegration`,
  `lightDevice`, and the integration/device branches of `applyFilters`.
- **FR-030d**: Removing these populations MUST NOT break the panel. `/api/graph`
  MUST still be fetched if any retained panel renderer depends on it; only the
  scene-object construction is removed. This MUST be verified rather than
  assumed — `renderSidebar` and `renderMetrics` both consume `graph` today.

### Scale

- **FR-029**: The layout MUST render correctly and remain readable up to
  **~100 members across ~25 categories**, with every node simultaneously
  visible. Virtualisation, level-of-detail, and default-collapsed categories
  are explicitly NOT required at this scale. Beyond it the chart MUST degrade
  gracefully (wrap and shrink) rather than break, overlap, or drop nodes.
- **FR-029a**: Node geometry SHOULD be instanced or otherwise shared so member
  count drives draw calls sub-linearly. At 100 members with tools expanded, the
  scene must not require per-node unique geometry.
- **FR-029b**: The chart MUST sustain **60 fps on a discrete GPU** at the
  FR-029 ceiling (100 members, ~25 categories, 5 members expanded) during pan
  and zoom. If the existing postprocessing chain (bloom/SMAA/afterimage) cannot
  hold that, the postprocessing MUST be reduced rather than the node count
  capped — legibility of the chart outranks the glow.
- **FR-029c**: Regression guard, independent of FR-029b: HUD 2.0 MUST NOT be
  slower than HUD 1.0 on identical data. It draws strictly less (FR-030 removes
  the integration and device populations entirely), so any slowdown indicates a
  defect in the new layout rather than an inherent cost.

  > **Known gap, accepted:** the target is specified against a discrete GPU, so
  > behaviour on integrated graphics — the likelier deployment for an operator
  > laptop — is unspecified and untested by FR-029b. FR-029c partially covers
  > this by preventing regression against HUD 1.0 on whatever hardware is used.
  > If integrated-graphics performance later proves inadequate, the remedy is
  > the FR-029b fallback (reduce postprocessing), not a redesign.

### Migration

- **FR-026**: The orbit layout MUST be replaced outright, not kept behind a
  runtime toggle. `main.js` renders the org chart and only the org chart. The
  feature branch is the rollback mechanism; no in-product fallback is required.
- **FR-027**: Orbit-specific machinery that the org chart does not use MUST be
  removed rather than left dormant — the ring/orbit positioning
  (`CORE_POSITIONS`, `CORE_CENTROID`, `RISK_LAYOUT.tierRadius`, per-core orbit
  speed/animation, the edge "close orbit" slots). Leaving dead layout code in a
  132 KB file is how the next person concludes the orbit is still supported.
- **FR-028**: Machinery that is layout-independent MUST be preserved and reused,
  not rewritten: materials and shaders (`createHolographicMaterial`,
  `createNodeMaterial`, `createDeviceMaterial`, `getSkillMaterial`), link
  geometry (`createRibbonGeometry` / `updateRibbonGeometry` / `createTubeMaterial`),
  labels (`makeLabel`, CSS2D), the postprocessing chain, picking/raycasting, the
  polling and incremental-update path (`refreshRiskMembers`), and every
  `setDetail`/`render*` panel function named in FR-018.

### Security constraint

- **FR-019**: This feature MUST NOT widen the HUD's existing unauthenticated
  API surface, and MUST NOT introduce any new endpoint that returns credential
  values. (See `~/netclaw-reports/SECURITY-hud-credential-exposure.md`: the
  HUD already serves the credential store in plaintext over an unauthenticated,
  CORS-open, `0.0.0.0`-bound API. That defect is out of scope here and is being
  tracked separately, but this work must not compound it.)

## Success Criteria *(mandatory)*

- **SC-001**: An operator who has never seen the HUD can correctly identify
  which claws are external and which are internal, on first view, without
  interacting.
- **SC-002**: The HOT members are identifiable within 2 seconds of load,
  without counting or zooming (4 of 29 on the reference deployment).
- **SC-003**: No camera input can produce a view in which the external band is
  not above the internal band. *(Verified by task T056.)*
- **SC-004**: All 29 members, 4 peers, and 2 edge nodes render without label
  collision or node overlap at default zoom.
- **SC-005**: Chat and the right-hand panel behave identically to HUD 1.0 —
  verified by diffing their behaviour, not by inspection.
- **SC-006**: **Product generality.** The chart renders sensibly for a
  deployment it has never seen, with zero configuration. Verified against at
  least three synthetic Borders: one with 1 member, one with ~30, and one whose
  members match no integration prefix at all (everything "Uncategorised"). No
  member-name string appears anywhere in the layout code.
- **SC-007**: All four health states are distinguishable in a **greyscale**
  screenshot — proving the encoding does not rest on colour alone.
- **SC-007a**: A single FAULT claw placed among 25 COLD ones is located by an
  operator in under 5 seconds, without search.
- **SC-008**: An operator can determine which tools a given claw holds, hot or
  cold, without leaving the chart or opening the detail panel.
- **SC-009**: The entire chart is operable with a keyboard alone — every node
  reachable, selectable, and expandable — and each node's health state is
  announced as text by a screen reader (FR-032).
- **SC-010**: With `prefers-reduced-motion` set, all four health states remain
  distinguishable, and SC-007's greyscale test still passes (FR-032c).
- **SC-011**: Over a 30-minute session in which members change state, no node
  changes position. Verified by comparing node coordinates between the first
  frame and the last (FR-034).
- **SC-012**: A NetClaw with no risk, no members and no peers renders the full
  band structure with empty states, and is never mistaken for a failed load —
  loading and empty are visually distinct (FR-033).
- **SC-013**: HUD 2.0 sustains 60 fps on a discrete GPU at 100 members with 5
  expanded, and is no slower than HUD 1.0 on identical data (FR-029b/029c).

## Assumptions

- Three.js is retained (r0.170, already vendored with `OrbitControls`,
  `CSS2DRenderer`, and the postprocessing chain). No new rendering dependency
  is required. `CSS2DRenderer` is the intended label mechanism — at ~40 nodes
  the DOM cost is immaterial and the crispness matters for a chart.
- No new layout library is required. Bands + row packing within a band is
  sufficient for a depth-2 chart; a general tidy-tree algorithm would be
  over-engineering here.
- The existing `/api/n2n` payload is sufficient. The only additions this spec
  implies are client-side (the category map in FR-006); no server change is
  required, and none should be made to satisfy FR-019.
