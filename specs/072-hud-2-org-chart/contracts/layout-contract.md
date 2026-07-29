# Contract: `orgchart/` pure-layout modules

Feature: `072-hud-2-org-chart` · Phase 1

The HUD exposes no public API to other systems, so the meaningful contract here
is the **internal boundary between pure layout logic and three.js rendering**.
That boundary is what makes the feature testable (research R1), so it is
specified rather than left to emerge.

## Invariants (binding on every module in `orgchart/`)

1. **No three.js.** No module in `orgchart/` may import `three`, any
   `three/addons/*`, or touch `window`, `document`, or a WebGL context. Each
   must be importable in bare Node.
2. **Pure.** Same input → same output. No I/O, no clocks, no randomness, no
   module-level mutable state. Anything time-dependent (heartbeat age) is passed
   in, never read from `Date.now()` inside.
3. **Non-mutating.** Input payloads are treated as frozen; modules return new
   objects.
4. **Total.** Never throw on malformed input. Missing/null fields resolve to a
   documented default (`Uncategorised`, `COLD`, `member_id` fallback label).

Invariant 1 is enforced by construction: the tests run under `node --test` with
no DOM, so a stray three.js import fails the suite rather than passing quietly.

---

## `categorize.js`

```js
categorizeMembers(members, integrationCatalog) -> Map<categoryName, Member[]>
categorizeMember(member, integrationCatalog)   -> string   // category name
```

- Catalog is an **argument, never an import** — this is what makes Constitution
  Principle VI (multi-vendor neutrality) testable: the same code must produce
  different correct charts for different catalogs.
- Matching: `skill.startsWith(prefix)` for each `integration.prefixes[]`.
- A member's category is the **most frequent** among its skills; ties broken by
  first catalog order for determinism.
- No match, no skills, or empty catalog → `"Uncategorised"`. Never dropped, never
  thrown (FR-006a).

**Required tests:** the live 29 (expect 25 categorised); empty catalog (all
`Uncategorised`); a member with zero skills; a synthetic alternate catalog
producing a different-but-correct chart (Principle VI).

---

## `health.js`

```js
WARM_THRESHOLD_S = 900                        // single named constant (FR-008a)
classifyHealth(member, nowEpochS) -> 'HOT' | 'WARM' | 'COLD' | 'FAULT'
```

- Evaluated strictly in precedence order: HOT → FAULT → WARM → COLD.
- `nowEpochS` is **injected**, never read internally — otherwise the WARM/FAULT
  boundary is untestable.
- `live === true` ⇒ HOT, regardless of every other field.
- `state ∈ {unreachable, quarantined}` ⇒ FAULT, regardless of heartbeat age.
- `heartbeat_age_s` null/absent and not otherwise FAULT ⇒ COLD (never seen).

**Required tests:** all four states; boundary at exactly 900 s; `active` but
`!live` (the real 5-vs-4 disagreement); `unreachable` with a *fresh* heartbeat
still FAULT; null heartbeat ⇒ COLD not FAULT. **The COLD/FAULT distinction is
the highest-value assertion in the suite** — conflating them is the specific
failure this design exists to prevent.

---

## `normalize.js`

```js
dedupePeers(peers)     -> Peer[]     // by identity; most restrictive state wins
resolveLabel(entity)   -> string     // never empty
```

- State restrictiveness: `severed` > `unreachable` > `reconnecting` > `federated`.
- Label precedence: `display_name` → tail of `member_id` after `/` →
  `identity` → `"unknown"`.

**Required tests:** the real duplicated-`Hermes` payload collapses to one peer
in `severed`; both real edge nodes (`display_name: null`) resolve to non-empty
labels (FR-015).

---

## `ordering.js`

```js
orderCategories(categories) -> Category[]   // heat desc, then size desc, then name
```

- `Uncategorised` always sorts last regardless of heat.
- Deterministic: name is the final tiebreak, so two runs over equal input give
  identical order.
- **Called once per session.** The contract does not forbid re-invocation, but
  `main.js` must not call it from the poll path (FR-034).

**Required tests:** hot-before-cold; equal-heat falls back to size; equal both
falls back to name; `Uncategorised` last even when it contains a HOT member (it
does, on the live data — `ipfabric`).

---

## `layout.js`

```js
computeLayout(chartModel, viewport) -> { nodes: ChartNode[], bands: Band[] }
appendMember(layout, member)        -> ChartNode   // no existing node moves
```

- Assigns `{x, y, z}` once. Three bands plus the edge lane always present, even
  when empty (FR-033).
- Internal band: category columns left→right, wrapping on viewport width;
  members stack vertically within a column.
- Edge nodes are routed to the edge lane and never appear in a category column
  (FR-007). More edges than lane slots wrap — they must never overlap, which is
  the bug in the current three-slot implementation.
- `appendMember` is the FR-034b path: a member enrolling mid-session gets a
  position **without any existing node changing** its own.

**Required tests:** all five fixtures (0, 1, 29, 100, uncategorised); no two
nodes share a position; `appendMember` leaves every prior coordinate byte-identical;
edge nodes never receive a member-column position; bands exist at zero members.

---

## Consumer contract (`orgchart-render/`)

Render modules **consume** this output and may not re-derive it. Specifically
they must not classify health, choose categories, or compute positions — those
answers come from `orgchart/` only. This keeps the render layer swappable and
keeps every falsifiable rule inside the tested half.
