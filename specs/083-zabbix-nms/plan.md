# Implementation Plan: SNMP-poller NMS coverage (Zabbix)

**Branch**: `083-zabbix-nms` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)
**Roadmap**: R11, Tier 2

## Summary

NetClaw has **no SNMP-poller NMS** and therefore **no polled history anywhere** — it receives syslog, traps
and flows, all of which arrive when something happens, and can answer nothing about what a thing was doing
over time. This adds that layer.

**Approach: adopt, don't build** — the first time this roadmap has landed there. `mpeirone/zabbix-mcp-server`
collapses the whole Zabbix API into three tools and measures **589 tokens, 11.8% of the ceiling**. It is
vendored unmodified, GPL-3.0 intact, invoked over stdio as a separate program, and run **from a dedicated
virtualenv** because it needs fastmcp 3.x while five servers here pin `<3`.

The NetClaw-authored deliverable is therefore **the skills**, not a server. That is where the entire value
of this feature lives, because the two silent-wrong-answer traps are enforced by guidance — a deliberate
departure from 080/081/082, recorded as such.

**Everything claimed here was measured against a live Zabbix 7.0.29** stood up for the purpose. Both traps
reproduce; a third retention state was discovered that the spec had not modelled.

## Technical Context

**Language/Version**: Python 3.10+. The vendored server runs from **its own virtualenv**; NetClaw authors no
Python for this feature.

**Primary Dependencies** — all inside the dedicated venv, none touching the system interpreter:

| Package | Resolved | Note |
|---|---|---|
| `fastmcp` | **3.4.5** | **The reason for the venv.** Five repo servers pin `<3` |
| `mcp` | 1.29.0 | |
| `zabbix_utils` | 2.0.4 | Zabbix LLC's own library — **not** `pyzabbix` (research D3) |
| `beautifulsoup4`, `requests`, `python-dotenv` | 4.15.0 / 2.34.2 / — | |

**Storage**: none. The NMS holds the history.

**Testing**: `tests/zabbix/run-tests.sh` — plain Python, stdlib only, following `tests/bgp-intel/`. Because
the guarantees live in the skill rather than in code, the suites split into two kinds: **static** checks on
the skill and configuration (does read-only get forced? does the skill contain a followable procedure?) and
**live** checks against the lab (does following the procedure produce the right answer?).

**Target Platform**: Linux, stdio MCP invoked by OpenClaw from a dedicated venv.

**Project Type**: Vendored third-party server + NetClaw-authored skills. Closest precedent:
`multivendor-cli-mcp` (spec 076) for the venv, `chrome-devtools-mcp` (spec 048) for the adoption posture.

**Performance Goals**: not latency-sensitive. Bounds on result size, stated in the response.

**Constraints**: manifest ≤ 5,000 tokens (**measured 589**); strictly read-only; no credential in any output;
no system-interpreter dependency movement.

**Scale/Scope**: 3 upstream tools, 3–4 skills, 1 vendored dir, ~5 test suites.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 below.*

| Principle | Status | How |
|---|---|---|
| **I. Safety-First (NON-NEGOTIABLE)** | ✅ | Strictly read-only (FR-021). Read-only **forced by NetClaw** rather than inherited, because the upstream launcher's default is inverted (measured, D10). Destructive-method deny-list as a second layer. |
| **II. Read-Before-Write** | ✅ n/a | There is no write. |
| **III. ITSM-Gated Changes** | ✅ n/a | No changes exist to gate. Recorded as a scope decision (FR-022); FR-023 requires that any future write arrive with both gates *and* a NetClaw-owned layer, so it cannot be enabled by flipping a flag. |
| **IV. Immutable Audit Trail** | ⚠️ **partial, knowingly** | No per-call GAIT: adopting as-is puts no NetClaw code in the call path, and there is no platform-level MCP audit (measured — two files, both NetClaw-authored servers). This is the inherited posture of every external integration. Principle IV bites on actions and configuration changes; this performs neither. FR-038a–c. See Complexity Tracking. |
| **V. MCP-Native Integration** | ✅ | stdio, registered with repo-relative paths. |
| **VI. Multi-Vendor Neutrality** | ✅ | Zabbix is itself vendor-neutral — it polls whatever speaks SNMP. |
| **VII. Skill Modularity** | ✅ | Five boundaries (FR-045–049) against Prometheus/Grafana, the trap receiver, the flow receiver, the SaaS monitors, and the device-reading skills. |
| **VIII. Verify After Every Change** | ✅ | Every capability exercised against a live NMS polling real devices; FR-050–052 require stating what was not. |
| **IX. Security by Default** | ✅ | TLS on by default (FR-029); no credential in output (FR-028); read-only forced; deny-list. |
| **X. Observability** | ✅ | The feature *is* observability. FR-011/012 make its own answers auditable — source, window actually served, and the NMS's own clock. |
| **XI. Artifact Coherence (NON-NEGOTIABLE)** | ✅ | FR-040–044, both HUD entries, curated profile membership, SOUL capability section. |
| **XII. Documentation-as-Code** | ✅ | spec, research, data-model, contracts, quickstart, skills, server README, TOOLS.md, VERIFICATION.md. |
| **XIII. Credential Safety** | ✅ | Token in `.env` only; FR-028 forbids it appearing anywhere. |
| **XIV. Human-in-the-Loop for External Comms** | ✅ | Reads only; sends nothing. |
| **XV. Backwards Compatibility** | ✅ | **The venv exists to guarantee this.** FR-037c requires proving the five `<3`-pinned servers still resolve after installation. |
| **XVI. Spec-Driven Development** | ✅ | specify → clarify (3 Q + 1 conflict raised) → plan → tasks → analyze → implement. |
| **XVII. Milestone Documentation** | ⏭️ **waived** | Standing operator decision. |

### Artifact Coherence Checklist — mapped

| Item | Target |
|---|---|
| README.md | MCP table row, skill rows, 4 count sites → 156 / 209+N |
| `catalog.sh` | `zabbix\|Observability\|Zabbix NMS\|…` + `PROFILE_OBSERVABILITY` |
| `install-steps.sh` | `component_install_zabbix()` — **venv-based**, `uv venv` / helper, never bare `python3 -m venv` |
| `verify-catalog-coverage.py` | passes (vendored dir needs a recorded state) |
| `ui/netclaw-visual/server.js` | **two** entries |
| SOUL.md | capability section + 2 count sites |
| skills | `zabbix-metrics-history`, `zabbix-problem-review`, `zabbix-availability` |
| `.env.example` | `ZABBIX_URL`, `ZABBIX_TOKEN`, `READ_ONLY`, `VERIFY_SSL`, deny-list, `ZABBIX_MCP_CMD` |
| TOOLS.md | `## Zabbix NMS (vendored, third-party GPL-3.0)` |
| `config/openclaw.json` | `zabbix-mcp` pointing at the **venv interpreter** |
| `mcp-servers/zabbix-mcp/README.md` | NetClaw-authored README beside the vendored tree |
| `.gitignore` | negation for the vendored dir |
| GAIT session log | recorded |
| Blog | waived |

## Project Structure

### Documentation

```text
specs/083-zabbix-nms/
├── plan.md · spec.md · research.md · data-model.md · quickstart.md
├── contracts/mcp-tools.md
├── checklists/requirements.md
├── VERIFICATION.md
└── tasks.md
```

### Source

```text
mcp-servers/zabbix-mcp/
├── vendor/zabbix-mcp-server/     # GPL-3.0, UNMODIFIED, pinned 0722f48, LICENSE verbatim
├── requirements.txt              # what the dedicated venv installs
├── NOTICE.md                     # third-party licence notice (FR-034a)
└── README.md                     # NetClaw-authored: limits, boundaries, the two traps

workspace/skills/
├── zabbix-metrics-history/SKILL.md    # US1 — THE critical artifact; both traps live here
├── zabbix-problem-review/SKILL.md     # US2
└── zabbix-availability/SKILL.md       # US3 + US4 (inventory is the enabler, not a story)

tests/zabbix/
├── run-tests.sh
├── test_readonly_forced.py     # static: NetClaw forces it; deny-list present; launcher default NOT trusted
├── test_venv_isolation.py      # static: five <3-pinned servers unaffected  (FR-037c)
├── test_skill_procedure.py     # static: the skill contains a FOLLOWABLE procedure, not just warnings
├── test_live_traps.py          # LIVE: both traps + the five absences against the lab
└── test_manifest_size.py       # measured ≤ 5,000

# Modified
config/openclaw.json · scripts/lib/catalog.sh · scripts/lib/install-steps.sh
ui/netclaw-visual/server.js · README.md · SOUL.md · TOOLS.md · .env.example · .gitignore
docs/COVERAGE-ROADMAP.md      # R11 status + correct the Netdata "Cloud MCP" claim
```

**Structure Decision**: vendored-unmodified third-party server in a dedicated venv, with NetClaw-authored
skills as the actual deliverable. Four servers or a wrapper were both rejected in clarification.

## Implementation Phases

| Phase | Content | Gate |
|---|---|---|
| **A. Vendor + isolate** | Vendor at the pinned rev with LICENSE and NOTICE; `requirements.txt`; venv install path; force read-only; deny-list | Server answers live Zabbix from the venv; five `<3` servers still resolve (FR-037c) |
| **B. US1 skill (P1)** | `zabbix-metrics-history` — the value-type procedure, the retention router, the **five** absences | An agent following it gets right answers on float items and beyond-retention windows |
| **C. US2 skill (P1)** | `zabbix-problem-review` | A real problem raised in the lab is reported correctly; empty ≠ unreachable |
| **D. US3+US4 skill (P2/P3)** | `zabbix-availability` — the "poller says" discipline + inventory | Stopping an FRR container produces a transition; wording never says "the device is down" |
| **E. Tests** | 5 suites, static + live | `run-tests.sh` exit 0 |
| **F. Artifacts** | All Principle XI surfaces + roadmap corrections | `reconcile-mcp.py` exit 0; counts updated |
| **G. Honest verification** | `VERIFICATION.md`; report both upstream defects | Per-capability table; trends marked unverified if the window has not elapsed |

Phase A is blocking. B, C and D are independent. **Trend verification must be started early** (D8: trends
need hours) — the lab should be polling from Phase A onward so Phase G has real aggregates.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle IV only partially met** — no per-call GAIT | Adopt-as-is puts no NetClaw code in the call path, and there is no platform-level MCP audit. Confirmed inherited posture of every external integration. | A wrapper would provide audit **and** the two gates **and** the structural routing — and was explicitly declined in clarification in favour of the smallest surface. Mitigated: read-only means no operation to audit (FR-038b); FR-038c blocks a future write path from arriving without audit. |
| **The three distinctions enforced by guidance, not structure** | Same clarification decision. A generic passthrough has no chokepoint. | Every alternative (wrapper, build) was declined. Mitigated by FR-006a — the skill must contain a *followable procedure*, not warnings — and by live tests that exercise the procedure end-to-end rather than asserting on skill text. **Recorded as a first for NetClaw (FR-033a), and the corresponding checklist lesson is left deliberately unticked.** |
| **A dedicated virtualenv** | Not optional: the candidate needs fastmcp 3.x and **five servers pin `<3`**. Measured. | Installing into the shared interpreter breaks five servers — spec 076's `cryptography` incident verbatim. Precedent already exists (`multivendor-cli-mcp`). |
| **Vendoring GPL-3.0 into an Apache-2.0 repo** | Adoption was chosen; this is the candidate. | Not a permission question — stdio invocation is not linkage. Mitigated by FR-034a: unmodified, licence verbatim, marked third-party, changes go upstream. |

## Post-Design Constitution Re-Check

Re-evaluated after Phase 0. **No new violations, and one downgrade caught early.**

1. **Principle XV moved from "assumed fine" to "actively guaranteed."** Phase 0 found the fastmcp conflict
   *before* anything was installed, which is precisely what FR-032's test-before-adopting exists for. The
   venv is now a requirement (FR-037a–c) with a proof obligation attached, rather than a discovery made
   after breaking five servers.

2. **Principle I gained a concrete threat.** The upstream launcher defaults read-only to **False** while the
   library defaults it to **True**. Neither the spec nor the prior research anticipated that. Read-only is
   now forced by NetClaw and backed by a deny-list, because depending on which upstream default wins is not
   a security posture.

3. **Two of my own prior claims were wrong and are corrected in place** — the `pyzabbix` dependency (it is
   `zabbix_utils`) and the auth-removal version (7.2+, not 7.0). Both came from research I repeated without
   verifying. They are corrected in the spec with the correction visible, not silently overwritten, because
   a reader who saw the earlier reasoning deserves to know it changed.

## Artifacts Generated

| File | Phase |
|---|---|
| `research.md` | 0 — 14 findings, all measured against live Zabbix 7.0.29 |
| `data-model.md` | 1 — the entities the skills reason about |
| `contracts/mcp-tools.md` | 1 — the upstream surface, documented as adopted |
| `quickstart.md` | 1 — lab setup (operator-local), the traps, the boundaries |
| `plan.md` | this file |

**Next**: `/speckit.tasks`.
