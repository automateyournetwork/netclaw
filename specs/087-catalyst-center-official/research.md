# Phase 0 Research — Catalyst Center official MCP (reconstruction)

**Date of work**: 2026-08-04 | **Reconstructed**: 2026-08-05 | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Assembled after merge from `spec.md`, `VERIFICATION.md` and the merged code.
> No `research.md` existed during the build. Findings below were measured then; only the write-up
> is retrospective.

---

## R1 — Is the existing coverage worth keeping?

**Decision**: Replace it.

The installed `catalyst-center-mcp` measured:

| Property | Value |
|---|---|
| Tools | 7 |
| Dependency pin | **`fastmcp>=0.1.0`, unbounded** — resolves 3.x, the conflict that blocked spec 083 |
| Version control | **untracked**, 0 files |
| Registration | **absent from `config/openclaw.json`** — on disk, never wired up |
| Licence | UNLICENSE |

An integration that is unregistered, untracked and carries the known dependency hazard is not a
baseline. Replacement, not augmentation.

---

## R2 — The candidate, and the 515-tool problem

**Decision**: Adopt Cisco's `cisco-en-programmability/catc-mcp-oss` — but not as-is.

Genuine first-party, **Apache-2.0** (licence-identical to NetClaw, so none of R11's vendoring
question), actively developed (pushed 2026-08-03, the day before the spec).

| Configuration | Tools | Manifest | vs 5,000 ceiling |
|---|---|---|---|
| Default bundle | **515** | **64,420** | **12.9× over** |
| Curated directory | 10 | 2,827 | pass |

For scale, this project had previously rejected candidates at 53, 111, 237 and 313 tools. **515 is
the largest surface ever evaluated here.** At ~283 tokens/tool the ceiling supports roughly 15 tools
with headroom — so the set must be *chosen*, never accumulated.

---

## R3 — Does a curation mechanism exist, or must upstream be patched?

**Decision**: It exists. No patching.

Verified by reading the source and running the loader: `config.py:108` reads
`CATALYST_CENTER_BUNDLED_TOOLS_DIR`, and `tool_loader.load_tools(root)` accepts an arbitrary
directory.

```
load_tools()          → 515 tools · 64,420 tokens
load_tools(curated/)  →  10 tools ·  2,827 tokens
```

The vendored tree is never modified — NetClaw supplies a directory and points the env var at it.
Preserves the adopt-unmodified posture spec 083 established.

---

## R4 — Curated tools versus dispatchers

**Decision**: Dispatchers. **This decision was made during implementation and supersedes the spec.**

| Approach | Tools | Manifest | API coverage |
|---|---|---|---|
| Upstream default | 515 | 64,420 | all — 12.9× over |
| Spec's original curation | ~15 | ~4,200 | **~3%** |
| **Delivered: 8 dispatchers + find + describe** | **10** | **1,821** | **all 514 read ops** |

Hand-curation fit the ceiling but bought almost nothing: ~3% of the API. Grouped dispatchers plus a
discovery tool (`catc_find`) and a schema tool (`catc_describe_operation`) reach everything for less
than half the tokens.

---

## R5 — Adopt the runtime or the catalogue?

**Decision**: The catalogue.

The upstream runtime carries an unbounded `fastmcp>=2.0.0` pin (collides with five NetClaw servers
pinning `<3`), an HTTP transport on port 7001, and a container requirement. Its *value* is the
maintained operation list, and that is consumable without any of the hazards.

---

## R6 — Read-only, verified by counting

**Decision**: 514 GET operations exposed; the single POST excluded.

Of 515 upstream tools, **513 are GET**. Only two mutate — one is `getApplicationPolicy`, misleadingly
named. Read-only is therefore enforceable by construction rather than by instruction.

---

## R7 — Which sandbox, and the finding that came with it

**Decision**: Cisco DevNet sandbox — and **the obvious host is the wrong one**.

`sandboxdnac` and `sandboxdnac2` share credentials, and **one has zero devices**. A test run against
the wrong host returns an empty inventory that looks exactly like a working query against a quiet
network.

**Consequence for design**: every response is stamped at a chokepoint with *which appliance answered*
and *when* (`observed_at`). Not cosmetic — it is the only way to tell a real empty from the wrong
box. Both cases were later exercised live: same call, same credentials, `outcome=ok data=4` versus
`outcome=empty` plus caveat, naming different hosts.

---

## R8 — The distinctions this feature must protect

1. **An empty inventory is not an empty network.** Catalyst Center reports what it *manages*.
2. **"Catalyst Center says" is not "the device is."** Controller state can be stale or wrong.
3. **Unreachable ≠ empty ≠ auth-failed.** Three different states, three different messages: a dead
   endpoint returns `unreachable` with "NOT AN EMPTY RESULT"; bad credentials return `auth_failed`
   with "state is UNKNOWN, not empty".
