# Tasks — Juniper Mist (R5)

**Branch**: `095-juniper-mist` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> Written after `spec.md` in the same session, before merge — closing the Principle XVI gap that
> 087–096 all shared. T001–T017 are complete; T018 onward are the **gated build**, deliberately not
> started.

---

## Phase 0 — Access (BLOCKING)

- [X] **T001** Operator creates a Mist org and an API token; region identified as `ac5` from the
      `manage.ac5.mist.com` URL
- [X] **T002** Store `MIST_API_HOST`, `MIST_ORG_ID`, `MIST_API_TOKEN` in `~/.openclaw/.env`; confirm
      the token value reaches no repository file

## Phase 1 — Establish the connection contract

- [X] **T003** `GET /api/v1/self` on `api.ac5.mist.com` → 200, org `NetClaw`, **`role: admin`**
- [X] **T004** Find the auth scheme: **`Bearer` only** — the REST API's `Token` scheme is refused
- [X] **T005** Find the region mechanism: `X-Mist-Base-URL`; without it a valid `ac5` token 401s
      against the default `api.mist.com`
- [X] **T006** Record that a wrong region and a bad token are **indistinguishable** — both 401

## Phase 2 — The ceiling gate (decides the feature)

- [X] **T007** `initialize` + `tools/list` → 7 tools, `instructions` 170 chars
- [X] **T008** Estimate by chars/4: ~10,052
- [X] **T009** **Count exactly** via `count_tokens`: **11,783 — 2.36× over**
- [X] **T010** Record that chars/4 **under-reported by 17%** — estimation is unsafe near the ceiling
- [X] **T011** Check for a tool-filtering mechanism across all 101 registered servers — **none
      exists**; a subset cannot be loaded
- [X] **T012** **Decision: reject adoption**

## Phase 3 — Characterise what the org can and cannot prove

- [X] **T013** Inventory the org: 1 site, 0 devices, 0 inventory, 0 alarms, 0 licences
- [X] **T014** Exercise every reachable tool; only `get_mist_constants` (284 device models) returns
      real data, and it is a static catalogue
- [X] **T015** Reproduce the trap: `sites_sle` returns `count: 1` with **no metrics** — *no
      telemetry* and *no problems* share a shape
- [X] **T016** Find and reproduce two schema defects: `get_mist_insights` requires an undeclared
      `query_type` (silently dropped at top level, must nest in `params`); `X-Mist-Org-ID` does not
      populate `org_id`

## Phase 4 — Make the decision durable

- [X] **T017** Commit `scripts/probe-mist-mcp.py` so the rejection is **re-checkable**, flagging any
      drift >500 tokens from 11,783
- [X] **T018** `.env.example` — three variable names, with the region and Observer-role warnings
- [X] **T019** `docs/COVERAGE-ROADMAP.md` — R5 → `BLOCKED — measured`, with the number
- [X] **T020** `reconcile-mcp.py` exits 0 (nothing registered, so no catalog/install/external entry
      is due)
- [X] **T021** Verify no credential in the repository (direct unpiped grep)

---

## Phase 5 — The gated build (NOT STARTED — blocked on external access)

> **Gate**: proceed only when a Mist org with at least one live AP or switch is reachable, **or**
> the operator accepts on the record that assurance tools ship unverified, as R3's manager and
> analyzer planes did.

- [ ] **T022** Obtain a populated org — Juniper SE demo org, or hardware (`trial_enabled: true`)
- [ ] **T023** Create an **Observer-role** org token and replace the admin token
- [ ] **T024** Build the GET-only client — no HTTP verb but `GET`, following 094's transport
      discipline
- [ ] **T025** Four dispatchers: `mist_inventory`, `mist_stats`, `mist_assurance`, `mist_search`
- [ ] **T026** Manifest ≤ 1,500 tokens, **counted** with `count_tokens`, never estimated
- [ ] **T027** Structural emptiness distinction: zero devices in scope ⇒ assurance answers report
      "no telemetry — cannot characterise health", never a health verdict. Enforced at a chokepoint
      that raises, following 091/094
- [ ] **T028** Exercise the trap against real telemetry — a healthy site and an empty site must
      produce different answers
- [ ] **T029** Skills: wireless assurance, client troubleshooting, Marvis query, SLE review
- [ ] **T030** Full `docs/ADDING-AN-MCP.md` pass: registration, catalog, install step, profile,
      docs, counts, HUD's two entries

---

## Dependencies

```
T003 → T004 → T005      (each connection failure had to be resolved to reach the next)
T007 → T009 → T012      (the count, not the estimate, is what rejects adoption)
T011 → T012             (a filterable manifest would have changed the decision)
T013 → T015             (the trap is only visible in an empty org — the one thing it IS good for)
T022 gates T024–T029    (the central failure mode cannot be tested without telemetry)
T023 gates T024         (build against least privilege, not admin)
```

## Out of scope

Apstra (stays with R6, paired per the roadmap); any write path; and adopting the remote server at a
later date **unless** `probe-mist-mcp.py` shows Juniper has materially shrunk the manifest.
