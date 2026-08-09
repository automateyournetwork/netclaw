# Tasks — Cisco Meraki official MCP (reconstruction)

**Branch**: `089-meraki-official` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Written after merge from the spec, `VERIFICATION.md`, `contracts/` and the
> delivered change. All items `[X]` — a record of completed work, ordered by dependency.

---

## Phase 1 — Measure the endpoint (BLOCKING)

- [X] **T001** `initialize` against `https://mcp.meraki.com/mcp` → `network-platform-cloud-mcp` 0.11.0
- [X] **T002** Measure the manifest: 2 tools, ~1,357 tokens
- [X] **T003** Measure `instructions` separately (~204 tokens) and count it — the R10 lesson
- [X] **T004** Total vs ceiling: **~1,561 / 5,000** — pass
- [X] **T005** Enumerate reachable capabilities: **494** non-deprecated GET operations

## Phase 2 — Prove read-only is structural, not advisory

- [X] **T006** Attempt 10 mutating verbs spanning every shape — all `Capability not found`
- [X] **T007** Ask `semantic_search` directly for firewall changes and a reboot — five results,
      **all `get*`**
- [X] **T008** Confirm the mechanism in source: `providers/openapi.py` collects non-deprecated GET
      operations only; 431 mutating operations absent from the catalogue
- [X] **T009** Record that the `instructions`' read-only request is **not** the control

## Phase 3 — Adopt and retire

- [X] **T010** Register the remote endpoint in `config/openclaw.json` (url + headers)
- [X] **T011** Record the self-host fallback (`CiscoDevNet/cisco-meraki-mcp-official`, Apache-2.0)
- [X] **T012** Retire `meraki-magic-mcp` — dead since spec 088 (missing `meraki` SDK)
- [X] **T013** Migrate skills to the official capability names in the same change (no orphans)
- [X] **T014** Confirm spec 088's startup findings drop **7 → 6**

## Phase 4 — The audit that grew a surface

- [X] **T015** Audit every Meraki method name cited in skills against the live catalogue
- [X] **T016** Finding: **54 of 80 documented method names do not exist**
- [X] **T017** Correct the 54
- [X] **T018** Add `scripts/verify-meraki-ids.py` as a **sixth reconcile surface** so the drift
      cannot recur silently

## Phase 5 — Coherence and credentials

- [X] **T019** Artifact coherence: catalog, install step, docs, counts
- [X] **T020** Verify the sandbox key appears in **no** repository file (direct unpiped grep)
- [X] **T021** `reconcile-mcp.py` exits 0

---

## Dependencies

```
T002–T004 gate adoption      (over ceiling ⇒ reconsider, as 087 and 095 had to)
T006–T008 gate registration  (advisory read-only is not a control)
T012 ↔ T013                  (retire and migrate together or callers orphan)
T015 → T016 → T017 → T018    (the surface exists because the audit found fiction)
```

## Deliberately not done

Self-hosting the fallback (unnecessary while the remote endpoint serves), any write path, and
reconciling Meraki's view against live device state — that boundary belongs to the device-plane
skills.
