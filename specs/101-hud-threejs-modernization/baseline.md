# Performance Baselines & Runtime Evidence (FR-044, FR-047)

**Feature**: 101-hud-threejs-modernization
**Captured**: 2026-08-07, host `DESKTOP` (WSL2), via headless Chrome over CDP

## How this was captured, and one process failure worth recording

Spec 101 assumed `chrome-devtools-mcp` (feature 048) was installed and usable. **It was
not** — 048 merged as an installable component (PR #97) but had never been enabled: no npm
package, no profile directory, not registered in either config, and no Chrome binary on the
host. `scripts/chrome-devtools-enable.sh` was run to provision it (Chrome
**151.0.7922.77** at `~/.cache/chrome-devtools-mcp/browsers/`, both MCP variants registered
with OpenClaw).

The registered MCP serves the *live OpenClaw agent*, not this implementation session, so
measurements were taken by driving the same Chrome binary directly over CDP
(`hud-probe.mjs`): console/exception capture, median frame time over a sustained window with
the camera idle, scene composition, and a full-page screenshot.

**Process failure**: T001 required the pre-bump baseline *before* the bump, and the bump was
landed first. The baseline was recovered by temporarily reinstalling `three@0.170.0`,
restarting the HUD, measuring, then restoring `0.185.1` — same machine, browser, scene and
quality mode, so the comparison holds. It should not have needed recovering, and the task
ordering existed precisely to prevent this.

## Environment (identical across all runs)

| | |
|---|---|
Host | WSL2, no discrete GPU |
Browser | Chrome 151.0.7922.77, `--headless=new`, 1920×1080 |
WebGL | WebGL 2 via **ANGLE / SwiftShader** (software rasterization) |
Scene | 42 CSS2D labels rendered; `/api/n2n`, `/api/graph`, `/api/bgp` all 200 |
Post-processing | all seven passes active |
Settle | 15 s before sampling; 400 frames sampled, first 60 discarded |

## Measurements

| Run | three.js | Median frame | p95 |
|---|---|---|---|
Pre-bump | `0.170.0` | **700.0 ms** | 883.3 ms |
Post-bump run 1 | `0.185.1` | **766.7 ms** | 900.0 ms |
Post-bump run 2 | `0.185.1` | **750.0 ms** | — |

Post-bump mean ≈ **758 ms**. Delta vs pre-bump: **+8.3%** (run 1 alone: +9.5%).

### FR-047 verdict: PASS, but marginal and not representative

Within the 10% budget, and the delta (+8.3%) exceeds the observed run-to-run spread
(766.7 → 750.0, ≈2.2%), so it is probably a real cost rather than noise. Two caveats stated
plainly rather than buried:

1. **Only one pre-bump sample.** The budget is nearly consumed and a second sample could move
   the verdict either way.
2. **A 700 ms median is ~1.4 fps — software rasterization, not a real operator machine.**
   Frame time here is dominated by SwiftShader, so a 10% budget on 700 ms is a different
   proposition from 10% on 16 ms, and nothing about *perceived* performance transfers. The
   numbers that decide FR-021/FR-047 in practice are the ones from the operator's real GPU.

This is exactly why SC-005 requires the numbers be recorded rather than a verdict asserted.

## Console errors (FR-024, SC-004)

One error, at **both** versions:

```
Failed to load resource: the server responded with a status of 404 (Not Found)
```

Traced to **`/favicon.ico`** (`/logos/netclawvisualhud.png` and all three API routes return
200). It is cosmetic, pre-existing, and unrelated to three.js — but it does mean **FR-024's
"zero console errors" is not currently met**, for a reason this feature did not introduce.
Recorded rather than waved away; fixing it is a one-line addition and a judgement call about
whether it belongs in this feature's scope.

Zero uncaught exceptions at either version, which is the substantive half of SC-004.

## Screenshots

`/tmp/.../scratchpad/hud-evidence/hud-{pre-bump-0.170.0,post-bump-0.185.1*}.png`

These are the artifacts for the **human** half of verification. SC-002 (selection legible) and
SC-003 (six peer states mutually distinct) are deliberately not self-graded — the declared
channels in `contracts/visual-contract.md` §3 are what a reviewer checks the screenshot
against.

## Status against the acceptance criteria

| Criterion | State |
|---|---|
SC-004 (runs on 0.185.1, no visual regression) | **Partial** — renders, 42 labels, zero exceptions; the pre-existing favicon 404 blocks the "zero console errors" clause |
SC-005 / FR-047 (frame time ≤110%) | **PASS, marginal** — +8.3%, software-rendering regime |
SC-007 (bundle ≤10%) | **PASS** — 753.22 → 798.80 kB, +6.05% |
SC-001 (7/7 peers inspectable) | **Not yet verified** — needs a click-through per peer |
SC-002, SC-003, SC-010 | **Not yet evidenced** — US2/US3 not implemented |
