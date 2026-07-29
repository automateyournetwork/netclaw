# Quickstart: HUD 2.0

Feature: `072-hud-2-org-chart` · Phase 1

## Run the HUD

```bash
cd ui/netclaw-visual
npm install          # only if node_modules is absent
npm run dev          # express API :3001 + vite :5173
```

> **Security note.** The HUD's API binds `0.0.0.0` and serves credentials
> unauthenticated (Principle XIII violation, pre-existing, out of scope for this
> feature — see plan.md). Do not run `npm run dev` on an untrusted network while
> that remains unfixed.

## Run the tests

```bash
cd ui/netclaw-visual
npm test             # node --test src/   (no browser, no GPU, no new deps)
```

Every module under `src/orgchart/` is pure and dependency-free, so the suite is
fast and runs anywhere Node runs. If a test fails with a three.js or `document`
error, an import has crossed the boundary the contract forbids — that is the
enforcement mechanism, not an accident.

## Work against a fixture instead of the live Border

The live Border has 29 members and can't exercise the 100-member ceiling
(FR-029) or the empty first-run state (FR-033):

```bash
HUD_FIXTURE=specs/072-hud-2-org-chart/fixtures/scale-100.json npm run dev
```

| Fixture | Exercises |
|---|---|
| `empty.json` | FR-033 first-run — bands, boundary, CTAs, no data |
| `single.json` | Degenerate single-member chart |
| `live-29.json` | Snapshot of the real Border (regression baseline) |
| `scale-100.json` | FR-029 ceiling + FR-029b frame rate |
| `uncategorised.json` | FR-006a — every member matches no prefix |

## Verify the perceptual criteria

Pure logic is covered by `npm test`. These need a real browser
(`chrome-devtools-mcp`, already vendored — no install):

| Check | How |
|---|---|
| SC-007 greyscale | Screenshot → greyscale filter → four states still separable |
| SC-007a fault-find | `uncategorised.json` + 1 FAULT among 25 COLD; time to locate < 5 s |
| SC-009 keyboard | Tab/arrows/Enter reach and operate every node, no pointer |
| SC-010 reduced motion | Emulate `prefers-reduced-motion`, re-run SC-007 |
| SC-011 stability | Node coordinates, first frame vs 30 min later — must be identical |
| SC-013 frame rate | Performance trace on `scale-100.json`, 5 expanded, during pan/zoom |

## Definition of done

1. `npm test` green.
2. All five fixtures render without overlap or blank labels.
3. Chat and the right-hand panel behave exactly as on `main` — diff behaviour,
   don't eyeball it (SC-005).
4. `/api/graph` still fetched; `renderSidebar` and `renderMetrics` still work
   (FR-030d — the single most likely way this feature breaks something else).
5. No orbit code remains (FR-027), and no integration/device scene objects
   (FR-030c).
6. `ui/netclaw-visual/README.md` updated (Constitution XI/XII).
7. `git grep` finds no member name hardcoded in layout code (SC-006).
