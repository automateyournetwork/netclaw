# Spec 093 — findings so far (research complete, implementation not started)

**Status**: research banked, parked mid-flight 2026-08-04
**Branch**: `093-package-reference-check`

Parked to handle a federation peering request. Everything below is measured, so the
implementation can start from facts rather than repeating the audit.

## Why this spec exists instead of R22

R22 was "Diagram MCPs — Excalidraw + draw.io". The operator pushed back that NetClaw already
has plenty of visual capability, and **they were right**. Measured:

| Existing | Covers |
|---|---|
| `drawio-diagram` skill | native `.drawio` files, CLI export to PNG/SVG/PDF, browser mode via `@drawio/mcp` |
| `uml-diagram` (Kroki, `uml-mcp`) | **27+ types** — Mermaid, D2, Graphviz, C4, BPMN, network, ER, sequence, state |
| `markmap-viz`, `aws-architecture-diagram`, `msgraph-visio` | mind maps, AWS topology, Visio |
| `canvas-network-viz`, `threejs-network-viz`, `ue5-network-viz`, `blender-3d-viz` | 2D canvas and 3D |

**draw.io is already done, and Kroki covers 27+ diagram types.** Excalidraw appears nowhere in
the repo, but it adds a *hand-drawn aesthetic*, not a capability. **Recommendation: close R22 as
largely satisfied** rather than build it.

The audit did, however, turn up something real.

## Finding 1 — three skills invoke an npm package that does not exist

`msgraph-files`, `msgraph-teams` and `msgraph-visio` all invoke:

```
npx -y @anthropic-ai/microsoft-graph-mcp
```

**That package 404s on the npm registry.** Between them the three skills document **17
invocations across 14 distinct `graph_*` tool names**, none of which can ever run. This is the
same defect class as spec 089's Meraki finding (54 of 80 documented method names did not
exist) — documentation that reads as capability.

Every other package a skill invokes was checked: **17 distinct npx/uvx references, and this is
the only missing one.** So the problem is narrow, not systemic.

## Finding 2 — the real replacement busts the ceiling by 45×

`@softeria/ms-365-mcp-server` (MIT, v0.136.0) exists and is the genuine equivalent. Measured
live by enumerating it over stdio — it lists tools **without credentials**:

| | |
|---|---|
| Tools | **188** |
| Tool manifest | **~224,944 tokens** |
| `instructions` | ~411 tokens |
| **Total vs the 5,000 ceiling** | **~225,355 — 45× over** |

By far the worst offender measured to date (previous record: k8s at 5,716, spec 084).

**Zero of its 188 tools are named `graph_*`**, which confirms the 14 tool names in the skills
are invented, not merely misrouted.

It does support filtering, so it is adoptable the way spec 084 handled Kubernetes:

```
--read-only --enabled-tools 'drive-item|folder-files|upload-file|chat|team'
    -> 12 tools, ~4,599 tokens  (FITS, just)
```

## Finding 3 — but Teams messaging is not there at all

Filtering without `--read-only` on `chat|team|channel|upload-file` returns **8 tools**:

```
list-accounts  login  logout  parse-teams-url
remove-account  select-account  upload-file-content  verify-login
```

`parse-teams-url` is the **only** Teams-related tool. There is no channel listing, no message
read, no message post. So:

- **`msgraph-files`** → satisfiable with real read-only file tools (`get-drive-item`,
  `list-folder-files`, `list-drive-item-versions`, …)
- **`msgraph-visio`** → needs `upload-file-content`, which `--read-only` strips; satisfiable
  only with writes enabled
- **`msgraph-teams`** → **not satisfiable by this server at all.** No amount of filtering
  produces Teams messaging.

## What remains to be built

1. **A permanent check**: every `npx`/`uvx` package a skill invokes must exist in its registry.
   Must be **offline and CI-safe** — the reconcile gate has no network by design (spec 075
   SC-013), so this needs the spec 089 shape: a vendored manifest of verified references
   checked offline, plus a `--refresh` mode that hits the registries. Do **not** make it a
   network-dependent CI gate; that is the mistake spec 090 made with the startup surface.
2. **Honest resolution of the three skills.** Rewiring needs an Azure app registration and M365
   tenant the operator has not provided, so the end state cannot be verified here. Options, in
   preference order:
   - rewire `msgraph-files` to real tool names, mark it unverified-pending-credentials
   - rewire `msgraph-visio` with writes enabled, same caveat
   - **mark `msgraph-teams` unavailable** and say why — the capability does not exist upstream
3. Close R22 in `docs/COVERAGE-ROADMAP.md` with the audit above as the reason.

## Blocked on the operator

An M365 tenant + Azure app registration (client ID/secret, delegated Graph scopes) to verify
any rewiring. Without it the skills can be made *honest* but not *verified*.
