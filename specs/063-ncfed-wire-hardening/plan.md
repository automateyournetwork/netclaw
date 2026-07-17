# Implementation Plan: NCFED Post-060 Wire-Confidentiality & Metadata Hardening

**Branch**: `063-ncfed-wire-hardening` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/063-ncfed-wire-hardening/spec.md`

## Summary

Four hardening items from the 2026-07-17 live capture. **P1 (endpoint persistence)** is a confirmed bug — persist a peer's endpoint on a *successful* connect / peer announcement so the reconnect supervisor stops using the stale address; small, isolated, ship first. **P2 (mesh in-protocol TLS)** brings the BGP mesh/keepalive session under 060's TLS+auth via the same STARTTLS-after-discrimination pattern, behind the enforcement flag — the heavy, flag-day slice, ship last. **P3 (metadata)** and **P4 (PQ)** are **gated by the crypto stack**: the reference host is Python 3.10 / OpenSSL 3.0.2, which has no ECH, no PQ hybrid (X25519MLKEM768), and no group control/readout — so P3 documents the SNI residual + adds an ECH-ready no-op seam, and P4 adds the posture knob + honest visibility (cipher/TLS-version now, group when the stack exposes it) that activates real PQ automatically on OpenSSL ≥ 3.5 / Python ≥ 3.15 (corrected from "3.13" — group control/readout landed in 3.15; see research R0-addendum).

## Technical Context

**Language/Version**: Python 3.10+ (daemon + `bgp/*`, `bgp/federation/*`); Bash (none new); Node/ES2022 (HUD posture render only)
**Primary Dependencies**: existing `bgp-daemon-v2.py`, `bgp/agent.py`, `bgp/session.py`, `bgp/federation/{tls,service,manager,channel,inventory,posture}.py`; stdlib `ssl`/`asyncio`/`sqlite3`. **No new third-party packages.**
**Storage**: extend existing SQLite `~/.openclaw/n2n/federation.db` (reuse `federation_peer.endpoint_host/endpoint_port/endpoint_updated_at`); reuse keys under `~/.openclaw/n2n/keys/`. No new stores.
**Testing**: pytest under `tests/n2n/` (unit: endpoint persistence, posture knob, KEX-visibility degradation; integration: two-node loopback mesh TLS mirroring 060's `test_secured_federation_060`)
**Target Platform**: Linux + systemd --user (matches 060/057)
**Crypto stack (decisive — see research R0)**: Python 3.10.12 / **OpenSSL 3.0.2** at plan time. TLS 1.3 ✅. `set_groups` ❌, group readout ❌, `X25519MLKEM768` ❌, ECH ❌ — group control/readout require OpenSSL ≥ 3.5 / Python ≥ 3.15. *2026-07-17 host upgrade (research R0-addendum): now Python 3.14.4 / OpenSSL 3.5.5 — the OpenSSL side negotiates X25519MLKEM768 by default, but the Python `ssl` group APIs remain absent until 3.15, so `pq_available` stays honestly false.*
**Performance Goals**: one extra TLS handshake per mesh session at establishment (long-lived — negligible); endpoint write is one row update on connect success
**Constraints**: NCFED preamble MUST still discriminate the shared port; mesh TLS is a coordinated flag-day gated by the enforcement flag; ECH/PQ mechanisms MUST degrade cleanly (never break connectivity) on a stack that lacks them
**Scale/Scope**: small-N mesh (≤10 external peers); correctness + honesty over throughput

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I/II/VIII Safety, verify | PASS | No managed-device changes; mesh TLS verified by two-node loopback before/after |
| IV Immutable audit (GAIT) | PASS | Endpoint changes + mesh-auth refusals routed through the existing audit trail |
| V MCP-native | PASS | Operator surface stays in existing daemon HTTP routes + `n2n-mcp` |
| IX Security by default | PASS | This *is* hardening; PQ `require` fails-closed-loudly, never silent |
| X Observability | PASS | KEX/PQ + endpoint freshness surface in the existing posture/HUD view (FR-014) |
| XI Full-stack artifact coherence | PASS (planned) | `.env.example` (N2N_PQ_MODE), README/docs, posture/HUD, tests are tasks |
| XV Backwards compatibility | PASS w/ justification | P1/P3/P4 fully back-compatible; **P2 mesh TLS is an intentional coordinated flag-day** for mesh peers, gated behind the enforcement flag with a documented migration (same pattern the constitution accepted for 060). See Complexity Tracking |
| XVI Spec-driven | PASS | spec + clarifications (4 Qs) on branch `063-ncfed-wire-hardening` |
| XVII Milestone blog | NOTED | Draft after implement |

**Honesty gate (new, self-imposed):** P3/P4 must not *claim* capabilities the stack lacks. The plan explicitly scopes them to documentation + degrade-clean scaffolding on the current stack — recorded, not hidden.

## Project Structure

### Documentation (this feature)

```text
specs/063-ncfed-wire-hardening/
├── plan.md          # this file
├── research.md      # R0 stack reality + R1–R5 decisions
├── data-model.md    # endpoint fields + KEX/PQ visibility fields (reused stores)
├── quickstart.md    # verify each of P1–P4 (incl. stack-gated behavior)
├── contracts/       # daemon route + posture-field + mesh-handshake deltas
└── tasks.md         # /speckit.tasks (not this command)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/
├── bgp-daemon-v2.py          # /n2n/connect persists endpoint on success; /n2n/certs+posture expose kex/pq
└── bgp/
    ├── agent.py              # P2: after 0xFF discrimination + OPEN identify, TLS-upgrade the mesh session
    ├── session.py            # P2: mesh session runs its FSM over the upgraded (TLS) reader/writer
    └── federation/
        ├── service.py        # P1: open_channel persists endpoint on success; _on_endpoint_update persists
        ├── manager.py        # P1: endpoint upsert on the success path (columns already exist)
        ├── tls.py            # P4: pq_available() probe + kex/pq readout helpers (degrade on 3.10); reused by P2
        └── posture.py        # P4: channel_security gains kex group + pq: available|unavailable

scripts/ , docs/ , .env.example   # N2N_PQ_MODE, mesh-TLS enable note, trust-boundary doc, peer guide update
tests/n2n/                         # test_endpoint_persistence_063, test_pq_posture_063, test_mesh_tls_063
```

**Structure Decision**: extend the existing `bgp/` + `bgp/federation/` packages in place (same as 060). No new modules except test files; `tls.py` gains small PQ/KEX helpers. P2 is the only change touching the BGP mesh core (`agent.py`/`session.py`).

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|-----------|------------|--------------------------------------|
| P2: mesh-session TLS is a flag-day wire change for mesh peers (Principle XV) | Operator chose in-protocol mesh encryption (Clarify Q1) over documented-underlay; the routing layer is genuinely cleartext on untrusted paths | Documented-underlay-only was the simpler option and was explicitly rejected at clarify; mitigated by gating behind the enforcement flag + staged rollout like 060 |
| P3/P4 shipped as documentation + degrade-clean scaffolding rather than working ECH/PQ | The reference crypto stack (OpenSSL 3.0.2 / Python 3.10) cannot do ECH or PQ at all (research R0) | Building real ECH/PQ now would require vendoring a newer OpenSSL+Python — rejected (heavy, out of "no new deps", separate infra call); the seam activates them automatically on a capable stack |
