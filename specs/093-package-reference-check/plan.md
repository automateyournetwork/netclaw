# Implementation Plan: Package-reference verification (and closing R22)

**Branch**: `093-package-reference-check` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

> ## ⚠ This is a reconstruction
>
> Written **2026-08-05** after merge, from `spec.md`, `FINDINGS.md`, `contracts/` and the delivered
> change. No `plan.md` existed during the build — a breach of Principle XVI, part of the 087–096
> drift.

## Summary

R22 ("Diagram MCPs — Excalidraw + draw.io") was queued next. The operator pushed back —
*"we should have LOTS of visuals already no?"* — so the premise was measured before building.

**They were right.** R22 closes as already satisfied: `drawio-diagram` ships native `.drawio` with
CLI export, `uml-diagram` covers **27+ types via Kroki**, plus `markmap-viz`,
`aws-architecture-diagram`, `canvas-network-viz`, `threejs-network-viz`, `ue5-network-viz`,
`blender-3d-viz`. Excalidraw adds a hand-drawn **aesthetic**, not a capability.

**The audit found a real defect, and that is what this spec delivers**: three skills invoking an npm
package that does not exist, plus a seventh reconcile surface so it cannot recur.

## Technical Context

**Language/Version**: Python 3.10+, stdlib only
**Primary Dependencies**: None. `--refresh` mode queries npm and PyPI over the network; the default
mode does not
**Storage**: A vendored manifest, `contracts/verified-packages.json` (16 entries)
**Testing**: Offline assertions against the vendored manifest
**Target Platform**: Linux, and CI
**Project Type**: Repository tooling — a reconcile surface — plus three skill corrections
**Constraints**: **The reconcile gate has no network access by design** (spec 075 SC-013)
**Scale/Scope**: 16 distinct packages referenced across all skills

## Constitution Check

| Principle | Gate | Status |
|---|---|---|
| **III. ITSM-Gated Changes** | Any write path must be CR-gated | **PASS** — `msgraph-visio` needs `upload-file-content`, so `--read-only` is deliberately omitted and the write is CR-gated |
| **VIII. Verify After Every Change** | Claims must be checkable | **PASS** — this adds the check |
| **XII. Documentation-as-Code** | A skill must not document what cannot run | **PASS** — `msgraph-teams` removed rather than left broken |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED** — see Complexity Tracking |

## The defect

`msgraph-files`, `msgraph-teams` and `msgraph-visio` all invoked
`npx -y @anthropic-ai/microsoft-graph-mcp`. **That package 404s on npm.** Between them the three
skills documented **17 invocations across 14 distinct `graph_*` tool names**, none of which could
ever run.

Nothing caught it, and the reason generalises: `verify-inventory-counts.py` checks counts agree, and
`check-server-startup.py` launches **registered** servers — but an on-demand `npx` invocation inside
a skill is **neither counted nor registered**. It falls between every existing surface.

Same meta-pattern as 088 and 089: **a check comparing declarations to each other cannot detect a
declaration that is uniformly wrong.**

Every `npx`/`uvx` reference in every skill was then checked: **16 distinct packages, and this was
the only missing one.** Narrow, not systemic — worth stating, because the alarming version of this
finding would have been "the skills are full of fiction", and that is not true.

## Project Structure

```text
scripts/check-package-references.py               # the seventh surface
specs/093-package-reference-check/contracts/verified-packages.json   # vendored manifest, 16 entries
workspace/skills/msgraph-files/     # rewired
workspace/skills/msgraph-visio/     # rewired, write CR-gated
workspace/skills/msgraph-teams/     # REMOVED
```

**Structure Decision**: Offline check against a vendored manifest — the same shape spec 089 used for
Meraki capability IDs. `--refresh` is a separate, network-using mode that re-queries npm and PyPI
and rewrites the manifest; **a human runs it, CI never does.**

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached** | Nothing justified it; part of the 087–096 drift | Remedied by this reconstruction plus a recurrence gate |
| **Offline-by-default with a vendored manifest** rather than live registry queries | The reconcile gate has **no network access by design** (spec 075 SC-013), and spec 090 already learned what ignoring that costs — CI failing on a healthy tree | Live queries would make CI depend on npm/PyPI availability, turning an outage into a build failure |
| **Removing `msgraph-teams` rather than fixing it** | The replacement package's Teams surface is `parse-teams-url` and nothing else — no channel listing, no message read, no post. Not satisfiable at any filter setting | Leaving it would keep advertising a capability NetClaw does not have. Graph itself supports `chatMessage`, so the capability is **not impossible — just unserved by this package**; recorded as a gap rather than quietly dropped |
