# Spec 093 — Package-reference verification (and closing R22)

**Status**: implemented
**Branch**: `093-package-reference-check`
**Date**: 2026-08-04

## How this spec came to exist

R22 was queued next: "Diagram MCPs — Excalidraw + draw.io". The operator pushed back —
*"we should have LOTS of visuals already no?"* — so the premise was measured before building.

**They were right.** R22 is closed as already satisfied:

| Already shipped | Covers |
|---|---|
| `drawio-diagram` | native `.drawio` files, CLI export to PNG/SVG/PDF, browser mode via `@drawio/mcp` |
| `uml-diagram` (Kroki) | **27+ types** — Mermaid, D2, Graphviz, C4, BPMN, network, ER, sequence, state |
| `markmap-viz`, `aws-architecture-diagram` | mind maps, live AWS topology |
| `canvas-network-viz`, `threejs-network-viz`, `ue5-network-viz`, `blender-3d-viz` | 2D and 3D |

draw.io is done and Kroki covers 27+ diagram types. Excalidraw appears nowhere in the repo but
adds a hand-drawn **aesthetic**, not a capability. Building it would have been motion, not
progress.

**The audit did find a real defect**, which is what this spec actually delivers. That is the
fourth time a roadmap premise has changed under measurement (R2 rescoped, R10 deferred, R17
resequenced, R22 closed), and the second time an operator's instinct triggered it.

## The defect

`msgraph-files`, `msgraph-teams` and `msgraph-visio` all invoked:

```
npx -y @anthropic-ai/microsoft-graph-mcp
```

**That package 404s on the npm registry.** Between them the three skills documented **17
invocations across 14 distinct `graph_*` tool names**, none of which could ever run.

Nothing caught it, and the reason generalises: `verify-inventory-counts.py` checks that counts
agree, and `check-server-startup.py` launches **registered** servers — but an on-demand `npx`
invocation inside a skill is **neither counted nor registered**. It falls between every existing
surface. Same meta-pattern as 088 and 089: a check comparing declarations to each other cannot
detect a declaration that is uniformly wrong.

Every `npx`/`uvx` reference in every skill was then checked: **16 distinct packages, and this
was the only missing one.** Narrow, not systemic — worth stating, because the alarming version
of this finding would have been "the skills are full of fiction", and that is not true.

## What the real replacement showed

`@softeria/ms-365-mcp-server` (MIT, v0.136.0) exists and is the genuine equivalent. Enumerated
live over stdio — it lists tools **without credentials**:

| | |
|---|---|
| Tools | **188** |
| Manifest | **~224,944 tokens** |
| `instructions` | ~411 |
| **Total vs the 5,000 ceiling** | **~225,355 — 45× over** |

By far the worst offender measured; the previous record was 5,716 (k8s, spec 084). It is
adoptable the same way 084 handled Kubernetes:

```
--read-only --enabled-tools 'drive-item|folder-files'   ->  12 tools, ~4,599 tokens (fits)
```

**Zero of its 188 tools are named `graph_*`**, which confirms the 14 names in the skills were
invented rather than merely misrouted.

### And one capability simply is not there

Filtering on `chat|team|channel|upload-file` **without** `--read-only` returns 8 tools:

```
list-accounts  login  logout  parse-teams-url
remove-account  select-account  upload-file-content  verify-login
```

`parse-teams-url` is the **only** Teams-related tool. No channel listing, no message read, no
message post. So the three skills resolve differently, and honestly:

| Skill | Resolution |
|---|---|
| `msgraph-files` | **rewired** — read-only file tools, real names |
| `msgraph-visio` | **rewired** — needs `upload-file-content`, so `--read-only` is deliberately omitted and the write is CR-gated per Principle III |
| `msgraph-teams` | **removed.** Not satisfiable by this server at any filter setting |

Removing rather than leaving it broken follows spec 088's own principle: *a registered server
nobody can install advertises a capability NetClaw does not have.* A skill documenting five
Teams tools that exist nowhere is the same lie in a different file. Microsoft Graph itself does
support `chatMessage`, so the **capability is not impossible — just unserved by this package.**
Recorded as a gap rather than quietly dropped.

## The permanent guard

`scripts/check-package-references.py`, wired in as reconcile's **seventh** surface.

**Offline by default, and that is the design.** The reconcile gate has no network access by
design (spec 075 SC-013: *"no dependencies, no network access, no credentials, and no installed
NetClaw agent"*), and spec 090 already learned what ignoring that costs — CI failing on a
healthy tree. So the check compares skill text against a **vendored manifest**
(`contracts/verified-packages.json`, 16 entries), exactly the shape spec 089 used for Meraki
capability IDs. `--refresh` is a separate, network-using mode that re-queries npm and PyPI and
rewrites the manifest; a human runs it, CI never does.

Design decisions worth recording:

- **An unverified reference is a finding, not a pass.** An unverified package is
  indistinguishable from a fictional one, and defaulting to "probably fine" is exactly how the
  msgraph 404 survived.
- **A reference marked as broken is history, not an invocation.** The rewritten skills say
  *"until spec 093 this invoked `@anthropic-ai/microsoft-graph-mcp`, which 404s"* — deleting
  that invites someone to reintroduce the bug. Same allowance, and the same reasoning, as the
  meraki-ids surface: punishing the teaching example pushes authors toward vaguer docs.
- **Prose is not a package.** Skills contain `npx with Azure AD credentials:`. A reference must
  be scoped or contain a hyphen/dot to be checked at all; bare words are skipped rather than
  reported, because a check that cries wolf gets ignored.
- **A `@version` suffix is stripped.** Missing this silently dropped
  `chrome-devtools-mcp@latest` out of the manifest entirely — the exact quiet failure the check
  exists to prevent, found while building it.

## Verification

`tests/reconcile/run-tests.sh` — **64 assertions, 0 failures** (52 before, 12 new):

- a verified existing package passes; a known-nonexistent one fails, naming both skill and package
- an **unverified** reference fails, and is distinguished from a nonexistent one
- a `@version` suffix resolves to the same package
- prose after `npx` is not treated as a package
- a reference marked as nonexistent is allowed as history
- `--warn-only` exits 0; a **missing manifest is exit 2**, not a false pass
- the shipped skills are clean

Reconciliation: **PASS on all seven surfaces.** Counts 219→218 skills (`msgraph-teams` removed).
The `packages` surface is in the CI gate, since unlike `startup` it needs no install.

## Out of scope

- **Verifying the rewired M365 calls.** Tool names and manifest cost are measured; no call was
  made. That needs an Entra ID app registration and an M365 tenant this environment does not
  have, and both skills say so under "Not verified" rather than implying they work.
- **Finding a Teams-capable MCP server.** Left as a stated gap; shopping for one is its own
  spec with its own ceiling measurement.
- **Checking package *versions* or contents.** This verifies existence, not that a package
  exposes the tools a skill names. That deeper check is what spec 089 built for Meraki, and it
  needed a vendored operation list to do it.
