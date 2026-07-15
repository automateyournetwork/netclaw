# Implementation Plan: iN2N — Internal NetClaw Federation (a "risk" of claws)

**Branch**: `056-in2n-internal-federation` | **Date**: 2026-07-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/056-in2n-internal-federation/spec.md`

## Summary

Add **internal federation (iN2N)**: a single operator runs a named group of focused NetClaws — a **"risk"** — coordinated by one **Border Claw**, with the other claws as tightly-scoped **Members**. The operator only ever talks to the Border; the Border routes each request to the Member that owns the capability and returns the result. Members are standalone OpenClaw runtimes (process/container) that **dial outbound** to the Border over a network-capable **internal transport** (loopback when co-located, private-network/overlay/tunnel when distributed across hosts/clouds/datacenters) — no inbound ports, no ngrok, no BGP mesh, no per-peer mutual consent. Trust within a risk is owner-implicit but still authenticated: a member enrolls once with a **single-use enrollment token** and its own **self-signed key**, which the Border **pins (trust-on-first-use)**; every later channel is authenticated by that pinned key. The Border can `remove` a member (unpin) and **auto-quarantines** a member that repeatedly fails health/auth.

The whole thing is a **new transport binding + trust profile over the existing NCFED semantics** — it reuses spec 052's JSON-RPC 2.0 framing, capability inventory, and spec 053's async task delegation, **without changing the frozen eN2N core** (external wire framing, mutual consent, default-deny, no-secrets guard). Two roles collapse cleanly onto the existing daemon: a standalone NetClaw is "a risk of one that is its own Border," and eN2N/iN2N/both is a Border-side setting, not a third role. Installer work adds the risk/role/profile selection and provisions members from catalog-derived profiles.

## Technical Context

**Language/Version**: Python 3.10+ (daemon federation layer + `n2n-mcp`, matching 052/053), Node.js 18+/ES2022 (HUD), Bash (installer), no new languages
**Primary Dependencies**: Existing `bgp-daemon-v2.py` + `bgp/federation/*` (manager, channel, service, inventory, authorization, invocation, chat, gateway, negotiate, tasks, audit), FastMCP (`n2n-mcp`), Python stdlib `json`/`sqlite3`/`asyncio`/`ssl`/`socket`; `cryptography` (already a repo dependency, spec 003) for self-signed key generation and pinned-key verification. No new third-party packages.
**Storage**: Extend the existing SQLite at `~/.openclaw/n2n/federation.db` with iN2N tables: `risk` (name/description/role/enabled-stacks), `member` (risk-local id, pinned key, transport binding, scope, health, state), `enrollment_token` (single-use). Reuse `delegated_task` for internal delegation; internal delegations are recorded in the existing `remote_invocation_record` audit table with a `channel_kind` discriminator. Pinned keys and the risk's own key stored under `~/.openclaw/n2n/keys/`.
**Testing**: pytest — unit tests for enrollment/pin/unpin/quarantine state machine, member registry, hub-and-spoke routing + deterministic tie-break, scope enforcement, and an in-memory internal-transport channel-pair harness (extending the 052/053 two-service loopback harness) for Border↔Member submit/status/result over iN2N. Regression tests asserting eN2N (052/053) behavior is unchanged.
**Target Platform**: Linux/WSL2 NetClaw hosts (unchanged); Members may additionally run in other hosts/clouds/datacenters reachable over the operator's private transport.
**Project Type**: Extension of the existing multi-component repo (daemon + `n2n-mcp` + HUD + modular installer).
**Performance Goals**: Stand up a working risk (Border + 1 Member) and route a specialty task in < 15 min from fresh install (SC-001); a Member carries only its profile's skills (SC-002); long internal delegations complete as background tasks, matching 053 reliability (SC-006); removed/quarantined member refused on next connect 100% (SC-010).
**Constraints**: Members MUST NOT join the public mesh or open inbound ports (SC-003/SC-011) — outbound-dial only; internal channel MUST be authenticated/encrypted (pinned self-signed key, no CA — FR-013a); hub-and-spoke, no iBGP/mesh (FR-007a); eN2N core frozen (FR-018); no secrets cross any claw boundary (FR-026); Border is the single audit/GAIT/gateway point and the sole external identity (FR-016/FR-024).
**Scale/Scope**: A handful of Members per risk (single-digit to low-double-digit); one Border per risk; a few concurrent internal delegations. Live testbed: John's risk with a Border + a CML Member + a pyATS Member, one co-located and one in a second location.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Safety-First Operations | PASS | No new device write path; Members run their own tools under their own local policies; delegation is observe/route, not a new write primitive |
| II | Read-Before-Write | PASS | Unchanged; scoping refuses out-of-scope work rather than acting blind |
| IV | Immutable Audit Trail | PASS | Border is the single audit/GAIT point (FR-024); every internal delegation + enrollment/removal/quarantine event is recorded; extends existing `remote_invocation_record` |
| V | MCP-Native Integration | PASS | Operator surface stays the `n2n-mcp` FastMCP server; new tools follow the proxy pattern; iN2N is a peer transport binding, not a bespoke tool integration; reuses NCFED JSON-RPC lifecycle |
| VI | Multi-Vendor Neutrality | PASS | No vendor logic added; Members are scoped bundles of existing vendor MCP servers/skills |
| VII | Skill Modularity | PASS | Extends the single `n2n-federation` skill with iN2N verbs; no duplication |
| IX | Security by Default | PASS | Least privilege is the whole point (scoped Members, small blast radius); authenticated pinned-key channel; single-use enrollment token; operator revoke + auto-quarantine; no new inbound exposure; Border is the only external face |
| X | Observability | PASS | Border surfaces member health/scope + in-flight internal tasks; HUD gains a risk/member view (US4/US5) |
| XI | Full-Stack Artifact Coherence | PASS (planned) | Touches README, `catalog.sh` (risk/role/profile install options under existing `n2n` component), `install-steps.sh`, `verify-catalog-coverage.py`, HUD, SOUL.md, `n2n-federation/SKILL.md`, `n2n-mcp/README.md`, `.env.example` (new `N2N_RISK_*` / member tunables), TOOLS.md, `config/openclaw.json`; enumerated in tasks |
| XII | Documentation-as-Code | PASS (planned) | Contracts for the iN2N enrollment + internal-transport + routing; SKILL/README same PR |
| XIII | Credential Safety | PASS | Enrollment token + keys in `~/.openclaw/n2n/keys/` (gitignored path, runtime-generated, never in repo); no secrets in config; no-secrets-cross-boundary guard reused (FR-026) |
| XIV | Human-in-the-Loop | PASS | Operator approves member removal/re-pin; external (eN2N) approval gate frozen; no autonomous external action added |
| XV | Backwards Compatibility | PASS | Standalone NetClaw behaves exactly as today (FR-004, SC-008); eN2N unchanged and regression-tested (FR-018, SC-009); additive SQLite tables + migrations |
| XVI | Spec-Driven Development | PASS | This SDD flow |
| XVII | Milestone Blog | NOTED | Draft at implement completion (iN2N is a major architectural addition) |

**Initial gate: PASS** — no violations; Complexity Tracking not required. The feature is additive: a new transport binding + trust profile + installer flow over frozen 052/053 primitives, plus one clean role model.

**Post-design re-check (after Phase 1): PASS** — data-model adds `risk`/`member`/`enrollment_token` tables and reuses `delegated_task` + `remote_invocation_record`; contracts add an iN2N handshake/enrollment path and internal-transport dial that live *alongside* the frozen eN2N `n2n/hello`, not replacing it; no new ports beyond the Border's existing reachable endpoint; no new languages or external trust paths. Standalone and eN2N paths untouched.

## Project Structure

### Documentation (this feature)

```text
specs/056-in2n-internal-federation/
├── spec.md
├── plan.md                          # this file
├── research.md                      # Phase 0 — decisions (transport, enrollment/pin, identity, routing, roles, installer, member runtime)
├── data-model.md                    # Phase 1 — Risk, Member, EnrollmentToken, MemberDelegation, entity states
├── quickstart.md                    # Phase 1 — stand-up-a-risk + route-to-CML-member walkthrough (co-located + cross-cloud)
├── contracts/
│   ├── in2n-enrollment.md           # token issue + member enroll (self-signed key) + pin/unpin/quarantine
│   ├── in2n-internal-transport.md   # member outbound dial, NCFED-over-internal-channel handshake variant, framing reuse
│   ├── in2n-routing.md              # Border capability match → member select (deterministic tie-break), submit/status/result reuse
│   └── in2n-daemon-api-delta.md     # new /n2n/risk, /n2n/members, /n2n/enroll* HTTP routes; n2n-mcp tool delta
└── tasks.md                         # Phase 2 (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/bgp/federation/
├── risk.py               # NEW: Risk + Member + EnrollmentToken models, RiskManager (SQLite),
│                         #   role (border|member|standalone), enabled-stacks, token issue/verify,
│                         #   key pinning/unpin, quarantine state machine
├── internal_channel.py   # NEW: iN2N transport binding — member-initiated outbound dial to Border,
│                         #   self-signed-key TLS/auth, NCFED framing reuse (encode_frames/decode),
│                         #   in2n/hello handshake variant (member_id + token/pinned-key, not AS/router-id)
├── router.py             # NEW: Border-side capability→member routing (uses reused inventory),
│                         #   deterministic tie-break, scope-enforcement check, "no member can do this"
├── manager.py            # + risk/member/enrollment_token tables + migrations; channel_kind on audit
├── service.py            # + iN2N supervisor: accept member dial-ins on Border, register/health/quarantine
│                         #   members; on Member role, dial supervisor to the Border (reuse 053 backoff)
├── invocation.py         # + internal delegation path (reuse delegated_task + async submit) over internal_channel
├── inventory.py          # + member-scope enforcement (advertised == allowed; refuse out-of-scope)
└── audit.py              # + internal-delegation + enroll/remove/quarantine audit events

mcp-servers/protocol-mcp/bgp/constants.py
                          # + NCFED_ROLE markers / in2n handshake constants (reuse magic + framing)

mcp-servers/protocol-mcp/bgp-daemon-v2.py
                          # + /n2n/risk (get/set), /n2n/members (list/remove), /n2n/enroll (issue/consume),
                          #   /n2n/route (operator ask → route to member); wire iN2N supervisor on start

mcp-servers/n2n-mcp/server.py
                          # + n2n_risk_status, n2n_member_list, n2n_member_add (profile|custom),
                          #   n2n_member_remove, n2n_enroll_token, n2n_route (ask the Border to route),
                          #   n2n_member_health; standalone/border/member aware

ui/netclaw-visual/
├── server.js             # + /api/n2n risk/member aggregation (border shows its members)
└── src/main.js           # risk view: Border node + member spokes, per-member scope/health/in-flight tasks

scripts/lib/
├── catalog.sh            # + risk/role/profile install metadata under the existing `n2n` component
├── install-steps.sh      # + component_install_n2n: risk/role prompts via tui.sh primitives; member provisioning from profiles
└── tui.sh                # REUSED AS-IS (Nick #96/#115/#117): tui_menu / tui_checklist / tui_yesno — no new prompt style

scripts/
├── netclaw               # + risk_menu (mirrors peering_menu) + `netclaw risk [status|members|add|remove|token|route]`
│                         #   subcommands (mirrors `netclaw peering …`); reuses TUI_CHOICE dispatch, palette, api_get/api_post
├── in2n-profiles.py      # NEW: derive claw profiles (CML/pyATS/security/…) from the installed skill catalog; Custom via tui_checklist;
│                         #   layers the chosen specialty on top of the mandatory base floor (FR-021a), tagging base vs specialty
└── verify-catalog-coverage.py   # unchanged logic; confirm coverage still passes

workspace/skills/n2n-federation/SKILL.md
                          # + iN2N section: risk/roles, ask-the-Border-to-route, member mgmt, enrollment

tests/n2n/
├── test_risk.py                 # role model, standalone=risk-of-one, single-Border enforcement
├── test_enrollment.py           # token issue/single-use, self-signed key pin/re-pin, reject invalid/spent
├── test_internal_transport.py   # member outbound dial, in2n/hello, NCFED framing reuse, encrypted channel
├── test_routing.py              # capability match, deterministic tie-break, "no member can do this"
├── test_scope_enforcement.py    # out-of-scope refused; advertised == allowed; base floor present + non-removable (FR-021a); base excluded from specificity (FR-021b)
├── test_quarantine.py           # remove unpins + refuses reconnect; auto-quarantine on repeated failure
├── test_member_delegation.py    # long internal task submit/status/result over iN2N (reuse 053 semantics)
└── test_en2n_regression.py      # 052/053 eN2N behaviors unchanged (frozen-core guard)
```

**Structure Decision**: Pure extension of the 052/053 `bgp/federation/` package plus the modular installer. Three new modules keep the new concerns cohesive — `risk.py` (risk/member/enrollment state), `internal_channel.py` (the iN2N transport binding that reuses NCFED framing over a member-initiated dial), and `router.py` (Border-side hub routing). Everything else is additive edits. The `n2n-mcp` operator surface and HUD extend their established proxy/polling patterns; the installer extends the existing catalog/`install-steps` model (spec 049). No restructuring, no repo split (out of scope).

## Complexity Tracking

No constitution violations — table not required.
