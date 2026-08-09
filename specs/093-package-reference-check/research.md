# Phase 0 Research — Package-reference verification (reconstruction)

**Date of work**: 2026-08-04 | **Reconstructed**: 2026-08-05 | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Assembled after merge from `spec.md`, `FINDINGS.md` and `contracts/`.

---

## R1 — Is R22 worth building?

**Decision**: **No. Close it as already satisfied.**

The operator questioned the premise before any work began, and measurement agreed:

| Already shipped | Covers |
|---|---|
| `drawio-diagram` | native `.drawio`, CLI export to PNG/SVG/PDF, browser mode via `@drawio/mcp` |
| `uml-diagram` (Kroki) | **27+ types** — Mermaid, D2, Graphviz, C4, BPMN, network, ER, sequence, state |
| `markmap-viz`, `aws-architecture-diagram` | mind maps, live AWS topology |
| `canvas-network-viz`, `threejs-network-viz`, `ue5-network-viz`, `blender-3d-viz` | 2D and 3D |

Excalidraw appears nowhere in the repo, but adds a hand-drawn **aesthetic**, not a capability.
Building it would have been motion, not progress.

**Fourth time a roadmap premise changed under measurement** (R2 rescoped, R10 deferred, R17
resequenced, R22 closed) and the **second** time an operator's instinct triggered it.

---

## R2 — The defect the audit found instead

**Finding**: `msgraph-files`, `msgraph-teams` and `msgraph-visio` all invoked
`npx -y @anthropic-ai/microsoft-graph-mcp`. **That package 404s on the npm registry.**

Between them: **17 invocations across 14 distinct `graph_*` tool names**, none of which could ever
run.

**Why nothing caught it**: `verify-inventory-counts.py` checks counts agree;
`check-server-startup.py` launches *registered* servers. An on-demand `npx` invocation inside a
skill is **neither counted nor registered** — it falls between every existing surface.

---

## R3 — Is this systemic?

**Decision**: No. Narrow.

Every `npx`/`uvx` reference in every skill was checked: **16 distinct packages, and this was the
only missing one.**

Worth stating explicitly, because the alarming version of this finding would have been "the skills
are full of fiction" — and that is not true.

---

## R4 — Is there a real replacement?

**Decision**: Yes for files and Visio; **no for Teams.**

`@softeria/ms-365-mcp-server` (MIT, v0.136.0) is the genuine equivalent. Enumerated live over stdio
— it lists tools **without credentials**:

| | |
|---|---|
| Tools | **188** |
| Manifest | **~224,944 tokens** |
| `instructions` | ~411 |
| **Total vs 5,000 ceiling** | **~225,355 — 45× over** |

**By far the worst offender measured** — the previous record was 5,716 (k8s, spec 084). Adoptable
the same way 084 handled Kubernetes:

```
--read-only --enabled-tools 'drive-item|folder-files'   →  12 tools, ~4,599 tokens (fits)
```

**Zero of its 188 tools are named `graph_*`**, which confirms the 14 names in the skills were
**invented**, not merely misrouted.

---

## R5 — What about Teams?

**Decision**: The capability is not there. Remove the skill.

Filtering on `chat|team|channel|upload-file` **without** `--read-only` returns 8 tools:

```
list-accounts  login  logout  parse-teams-url
remove-account  select-account  upload-file-content  verify-login
```

`parse-teams-url` is the **only** Teams-related tool — no channel listing, no message read, no post.

| Skill | Resolution |
|---|---|
| `msgraph-files` | **rewired** — read-only file tools, real names |
| `msgraph-visio` | **rewired** — needs `upload-file-content`, so `--read-only` is deliberately omitted and the write is CR-gated per Principle III |
| `msgraph-teams` | **removed** — not satisfiable at any filter setting |

Removing rather than leaving it broken follows spec 088's own principle: *a registered server nobody
can install advertises a capability NetClaw does not have.* A skill documenting five Teams tools
that exist nowhere is the same lie in a different file.

Microsoft Graph itself supports `chatMessage`, so the **capability is not impossible — just unserved
by this package.** Recorded as a gap rather than quietly dropped.

---

## R6 — How should the permanent guard work?

**Decision**: Offline by default, against a vendored manifest. `--refresh` is a separate,
human-run, network-using mode.

The reconcile gate has **no network access by design** (spec 075 SC-013: *"no dependencies, no
network access, no credentials, and no installed NetClaw agent"*), and spec 090 already learned what
ignoring that costs — CI failing on a healthy tree.

So the check compares skill text against `contracts/verified-packages.json` (16 entries) — the same
shape spec 089 used for Meraki capability IDs.

**An unverified reference is a finding, not a pass.** An unverified package is exactly the state the
404 package was in; treating unknown as acceptable would reproduce the defect.
