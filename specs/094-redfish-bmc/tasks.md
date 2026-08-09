# Tasks — Redfish BMC out-of-band visibility (reconstruction)

**Branch**: `094-redfish-bmc` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Written after merge from the spec, the delivered server and its tests. All
> items `[X]`, ordered by dependency rather than chronology.

---

## Phase 1 — Adopt-or-build decision (BLOCKING)

- [X] **T001** Evaluate `carlosedp/redfish-mcp-server` — **no licence at all**, unvendorable
- [X] **T002** Evaluate `fredriksknese/mcp-redfish` — `NOASSERTION`, not a recognised OSS licence
- [X] **T003** Decide **build**: Redfish is a stable self-describing DMTF standard, so the client is
      a thin HTTP layer, not a vendor SDK

## Phase 2 — Characterise the distinction (this is the whole spec)

- [X] **T004** Establish that the trap is **symmetric** — unreachable BMC ⇏ host down;
      `PowerState: On` ⇏ healthy
- [X] **T005** Establish the one reading that **is** a fact: reachable + `Off` ⇒ the host is off
- [X] **T006** Establish that an auth rejection (401/403) proves the BMC **answered** — a live BMC
      with a credential problem, never "unreachable"

## Phase 3 — Enforce it in code, not documentation

- [X] **T007** `verdict.host_verdict()` **raises** when asked to derive host state from an
      unreachable BMC (FR-003)
- [X] **T008** `verdict.emit()` **raises** if a response carries a host claim with no verdict (FR-002)
- [X] **T009** Unrecognised `PowerState` becomes `POWER_STATE_UNREPORTED` rather than being guessed
- [X] **T010** A hardware fault is reported as **independent of OS state**

## Phase 4 — Read-only at the transport

- [X] **T011** `client.py` implements **`get()` and nothing else** (FR-001)
- [X] **T012** Do not implement `#ComputerSystem.Reset` — a power cycle on the wrong box is an
      outage, and the safer answer is not to build it
- [X] **T013** Assert by scanning source for `.post(`/`.put(`/`.patch(`/`.delete(` and any reset path

## Phase 5 — Safety of configuration

- [X] **T014** Refuse an unset `REDFISH_URL` — probing an unknown BMC risks querying **someone
      else's hardware** (FR-005)
- [X] **T015** TLS verification defaults off (BMCs ship self-signed certs) but is **disclosed in
      every response** — a silent downgrade is unacceptable, a visible one is workable (FR-006)
- [X] **T016** Report empty SEL, empty firmware inventory and absent Thermal/Power as **coverage
      gaps**, never "no problem" (FR-007)

## Phase 6 — Verification without hardware

- [X] **T017** Stand up the DMTF Redfish mockup (Redfish 1.15.0)
- [X] **T018** Live read: Contoso 3500, `PowerState: On`, health `OK`, 2×8 cores, 96 GiB, 3 temp
      sensors, 2 fans, 344 W of 800 W — with `verdict: POWERED_ON`
- [X] **T019** Point the same tool at a dead port → `host_state: UNKNOWN`, `bmc_reachable: false`
- [X] **T020** `tests/redfish/run-tests.sh` — **15 assertions, 0 failures**; verdict and read-only
      assertions pure stdlib so they always run, live ones skip without `httpx`/mockup (CI-safe)
- [X] **T021** Fix the bug found during verification: `httpx` INFO logging on **stdout** can corrupt
      the JSON-RPC stream on a stdio transport — silenced at the logger and asserted clean (FR-008)
- [X] **T022** State the mockup's limits honestly in the skill — vendor quirks unverified
- [X] **T023** Reconciliation PASS on all seven surfaces; counts 160→161 MCP, 218→219 skills

---

## Dependencies

```
T001–T003 gate implementation
T004–T006 → T007–T010   (the distinction must be characterised before it can be enforced)
T011 → T013             (assertions scan the source, so the source must exist first)
T017 → T018 → T019      (both directions must be exercised against the same tool)
T021 discovered during T018 — logging corruption is invisible until parsing fails
```

## Deliberately not done

Power control of any kind — **not a limitation to lift later**; vendor OEM extensions (`Oem`
subtrees are reported by `redfish_status` but not parsed, so an operator can see what is being left
on the table); verification against real Dell/HPE hardware; BMC credential storage (the skill points
at Vault); Cisco UCS/Intersight — a cloud API, not Redfish, so it stays R7.
