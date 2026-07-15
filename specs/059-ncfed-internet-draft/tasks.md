---
description: "Task list for the NCFED IETF Internet-Draft (draft-capobianco-ncfed-00)"
---

# Tasks: NCFED IETF Internet-Draft (`draft-capobianco-ncfed-00`)

**Input**: Design documents from `/specs/059-ncfed-internet-draft/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/{draft-outline,ascii-diagrams}.md, quickstart.md

**Tests**: This is a documentation deliverable — "tests" are the IETF toolchain + fidelity checks (`kdrfc` compile, `idnits`, and the 14-row wire-fact ↔ code cross-check). They are included as explicit verification tasks (the spec's Independent Tests / SC-001..007), not code tests.

**Freeze rule**: NO change to the eN2N/iN2N wire or any code (FR-024). Every normative statement traces to `research.md`/`data-model.md §3` (file:line). If the draft and code disagree, the draft is wrong — never "fix" the code.

**⚠️ Same-file constraint**: the draft is ONE file (`docs/ietf/draft-capobianco-ncfed-00.md`). Section tasks that edit it are **sequential** (not `[P]`). Only genuinely separate files (checklist, positioning note, `.gitignore`) are `[P]`.

Repo root: `/home/johncapobianco/netclaw`. Draft home: `docs/ietf/`.

---

## Phase 1: Setup (tooling + skeleton file)

- [X] T001 [P] Install authoring tooling and record versions: `gem install kramdown-rfc` (provides `kdrfc`) and `pip install idnits`; capture `kdrfc --version` / `idnits --version` into `docs/ietf/SUBMISSION-CHECKLIST.md` (create the file with a "Tooling" section).
- [X] T002 [P] Add build outputs to `.gitignore`: `docs/ietf/*.xml`, `docs/ietf/*.txt`, `docs/ietf/*.html` (keep the `.md` source tracked).
- [X] T003 Create `docs/ietf/draft-capobianco-ncfed-00.md` with the kramdown-rfc **front matter** exactly per `contracts/draft-outline.md` (title, `abbrev: NCFED`, `category: exp`, `docname`, `submissiontype: independent`, `v: 3`, keyword, venue github, author with `email: TODO@example.com` fill-in) and the normative + informative **reference stanzas** (RFC 2119/8174/4271/8259 + JSON-RPC 2.0; RFC 7301/6455/7435/6335/8126 + MCP/A2A/draft-yan).

**Checkpoint**: the file exists and front matter + references are in place.

---

## Phase 2: Foundational (skeleton that compiles + the three figures)

**⚠️ Blocks all content stories** — the section skeleton and figures must exist before prose is filled.

- [X] T004 Add all mandatory section headers (Abstract; §1 Introduction; §2 Conventions & Terminology; §3 Protocol Stack Overview; §4 Discrimination; §5 Handshake; §6 Framing; §7 Heartbeat; §8 Semantic Payload; §9 Version Negotiation; §10 Capability Cards; §11 Trust Establishment; §12 Operational Considerations; §13 Security Considerations; §14 IANA; back: Prior Art & Rationale, Acknowledgments) as empty stubs in `docs/ietf/draft-capobianco-ncfed-00.md`, in the order fixed by `data-model.md §2`.
- [X] T005 Insert the RFC boilerplate + `{::boilerplate bcp14-tagged}` (RFC 2119/8174 keywords) in §2, and the terminology list (NetClaw, risk, Border, member, eN2N, iN2N, peer AS/router-id) per `contracts/draft-outline.md §2`.
- [X] T006 Embed the three pre-drawn figures from `contracts/ascii-diagrams.md` into their sections as kramdown-rfc `~~~` artwork blocks with anchors/titles: Fig 1 `fig-stack` (§3), Fig 2 `fig-handshake` + Fig 2b `fig-in2n-preamble` (§5/§11), Fig 3 `fig-frame` (§6). Verify each is ≤72 cols and ASCII-only.

**Checkpoint**: `kdrfc` compiles the skeleton (headers + figures + refs) with no errors — a submittable shell exists.

---

## Phase 3: User Story 1 — Submittable, tool-clean I-D (Priority: P1) 🎯 MVP

**Goal**: The draft compiles via `kdrfc` and passes `idnits` with zero errors — a submittable document (even before every wire detail is filled), with correct Experimental boilerplate and the WG-ambition note.

**Independent Test**: `kdrfc draft-capobianco-ncfed-00.md` → clean `.xml`/`.txt`/`.html`; `idnits draft-capobianco-ncfed-00.txt` → zero errors; RFCXML is v3.

- [X] T007 [US1] Write the **Abstract** (≤~20 lines: NCFED = cross-operator federation transport carrying MCP+A2A; multiplexes with BGP; two trust models) in `docs/ietf/draft-capobianco-ncfed-00.md`.
- [X] T008 [US1] Write **§1 Introduction + Motivation/Applicability**: 3-operator mesh + monolith→risk; long-lived mutually-known peers, NOT anonymous federation; and the FR-003a note (individual Experimental submission; author seeks `agentproto` WG adoption toward Standards Track; `-00` asserts no consensus; substance category-neutral).
- [X] T009 [US1] Write **§12 Operational Considerations** (hybrid hot/cold runtime; least-privilege secrets; standalone = a risk-of-one) — low-risk prose that rounds out the shell.
- [X] T010 [US1] Build + nits gate: run `kdrfc` then `idnits`; record results + triage every warning (expected: no-date/no-RFC-number) into `docs/ietf/SUBMISSION-CHECKLIST.md`. **Fix until zero errors** (SC-001, SC-002). *(RESOLVED 2026-07-14: Ruby+kramdown-rfc+xml2rfc installed; draft **compiles clean to RFCXML v3** and renders `.txt` with 0 over-length lines (fixed a cert-store symlink + duplicate-ref + wide-figure warnings). `idnits` not installable locally → Datatracker runs it server-side (authoritative, A1). See SUBMISSION-CHECKLIST.md for the working recipe.)*

**Checkpoint**: US1 independently done — a clean, submittable Experimental I-D shell.

---

## Phase 4: User Story 2 — Faithful, implementable wire specification (Priority: P1)

**Goal**: The wire sections specify NCFED exactly as implemented, so an implementer can build an interoperable peer; every statement matches `data-model.md §3` / the code.

**Independent Test**: cross-check all 14 wire-fact rows against the cited code — zero contradictions; each has an unambiguous normative statement (+ diagram where applicable).

- [X] T011 [US2] Write **§4 Protocol Discrimination** per `contracts/draft-outline.md §4` (0xFF→BGP; `N`+4→`NCFED`/`NCTUN`; 30 s/10 s MUST-close timeouts; unknown→close). Cite fidelity rows 1–2.
- [X] T012 [US2] Write **§5 Federation Handshake** (13 octets; `NCFED`+AS[4, network byte order]+router-id[4, packed IPv4]; one-way initiator→acceptor; reference `{{fig-handshake}}`). Fidelity row 3.
- [X] T013 [US2] Write **§6 Message Framing** (length[4,BE] + flags[1]; bit0 CONTINUATION; bits 1–7 RESERVED MUST-be-0/ignored; 64 KiB max; oversize→close; chunking; `{{fig-frame}}`). Fidelity rows 4–6.
- [X] T014 [US2] Write **§7 Heartbeat & Liveness** (zero-length frame; 30 s / 3-miss / 90 s hold; any inbound resets). Fidelity row 7.
- [X] T015 [US2] Write **§8 Semantic Payload** (JSON-RPC 2.0; request/response/notification; request-id form; only `n2n/hello` pre-federation; method families incl. `n2n/tools/call` and `n2n/tasks/*`; async task state machine submitted→working→{completed|failed|cancelled}) and embed **both error registries verbatim** from `data-model.md §4`. Fidelity rows 8–10.
- [X] T016 [US2] Write **§9 Version & Capability Negotiation** (in-band at `n2n/hello`: `proto_version` + `features`; missing = 052 baseline; RECOMMEND a future handshake version octet phrased as guidance, not an existing field — FR-022). Fidelity row 11.
- [X] T017 [US2] Write **§10 Capability Cards** (advertised `skills`/`mcp_servers`/`badges` + `posture{mode,state,controls}` + `llm{primary_model,guarded}`; MUST state no secrets, no per-member topology). Fidelity row 12.
- [X] T018 [US2] Write **§11 Trust Establishment**: eN2N consent SM (`not_federated→consent_pending_{local,remote}→federated→severed`, persists across restart/endpoint change) AND iN2N (separate Border listener; `{{fig-in2n-preamble}}`; ECDSA-P256/SHA-256 signed-nonce over `IN2N1`+32B; TOFU pin = SHA-256 of SubjectPublicKeyInfo; single-use `"in2n_"`+urlsafe token, SHA-256-stored, optional TTL; members outbound-only MUST NOT accept inbound; auto-quarantine ≥5). Keep eN2N/iN2N distinct; note `IN2N1` version digit. Fidelity rows 13–14.
- [X] T019 [US2] **Fidelity cross-check** (SC-003): walk all 14 rows of `data-model.md §3` against the cited code; correct any drift in the draft. Record the 14/14 pass in `docs/ietf/SUBMISSION-CHECKLIST.md`.

**Checkpoint**: US2 independently done — the normative wire spec is complete and provably faithful.

---

## Phase 5: User Story 3 — Security Considerations that survives review (Priority: P1)

**Goal**: §13 addresses every hazard a reviewer will raise, honestly, with SHOULD/RECOMMEND mitigations; §14 IANA is decided.

**Independent Test**: each of the 5 `data-model.md §5` parts is present with a stated mitigation/limitation — 0 omissions (SC-004).

- [X] T020 [US3] Write **§13 Security Considerations** with all five parts per `data-model.md §5`: (1) BGP port-sharing/parser-reachability + RECOMMEND TTL-security/ACLs + read-timeout MUST-close; (2) cleartext-by-default + SHOULD TLS/encrypted underlay + iN2N `CERT_NONE` caveat, framed via RFC 7435; (3) TOFU token entropy/transport/attacker-window/recovery; (4) agent-delegation hazards (per-peer authz, prompt-injection across boundary, Border audit, production guardrails, SHOULD delegation-depth/loop limit); (5) DoS (64 KiB cap, SHOULD bound continuation reassembly, heartbeat/cold-start exhaustion). (FR-016/017/017a/018)
- [X] T021 [US3] Write **§14 IANA Considerations** (FR-019): request service name `ncfed` (RFC 6335), **no assigned port** (operator-configured; multiplexes on BGP/mesh port); document the `N`+tag magic space but **do not** request a registry; **do not** request a fixed well-known port.

**Checkpoint**: US3 independently done — the section reviewers scrutinize first is complete and candid.

---

## Phase 6: User Story 4 — Positioned & differentiated for agentproto (Priority: P2)

**Goal**: A reader/WG can place NCFED and restate its differentiation in one sentence; the author has a socialization plan.

**Independent Test**: back matter contrasts ALPN/WebSocket/BGP + draft-yan; positioning note states venue + fallback + talking points (SC-007).

- [X] T022 [US4] Write the **Prior Art & Design Rationale** back-matter (FR-020): contrast ALPN (RFC 7301, TLS-layer vs first-octet), WebSocket (RFC 6455, framing lineage), BGP-4 (RFC 4271, identity); differentiate from `draft-yan-a2a-device-agent-applicability` (single-domain controller→device mTLS, no cross-operator federation) — NCFED federates independently-operated agents and CARRIES A2A/MCP. Add **Acknowledgments** (Nick AS 65007, Byrn AS 65099).
- [X] T023 [P] [US4] Write `docs/ietf/AGENTPROTO-POSITIONING.md`: recommended venue (agentproto BoF/forming WG at IETF 126), ISE Experimental fallback, the one-line differentiation, and the meeting-submission-window caveat.

**Checkpoint**: US4 done — the draft is situated and has a socialization path.

---

## Phase 4b: Running-code evidence (US2) — packet capture

- [X] T028 [US2] Store the live capture as a committed artifact: `docs/ietf/captures/ncfed-johns-risk-nick-20260714.pcap` (AS 65001 ↔ AS 65007). Confirm it is NOT gitignored.
- [X] T029 [US2] Verify the capture stats with `capinfos`/`tshark` (24 pkts, 3141 octets, single established conv, 0 SYN/FIN/RST, 0 retransmits/dup-acks, segment-size set) — the figures the appendix must match (SC-008).
- [X] T030 [US2] Write the **RFC 7942 Implementation Status** appendix in `docs/ietf/draft-capobianco-ncfed-00.md` (`{:removeinrfc="true"}`; add `RFC7942` informative ref): report the verified capture figures AND the honest scope limitation (TLS-tunnel/ciphertext = channel evidence, NOT plaintext frame dissection; plaintext capture = future work via loopback/key-owned underlay). MUST NOT overclaim (FR-025, SC-008).

## Phase 7: Polish & submission readiness

- [X] T024 Final **build + nits** pass: `kdrfc` clean + `idnits` clean on the complete document; update `docs/ietf/SUBMISSION-CHECKLIST.md` (compile ✓, idnits ✓ with warning triage, RFCXML v3 ✓, Datatracker steps, BCP 78/79 acknowledgment).
- [X] T025 Full **completeness review** against Success Criteria: SC-004 (5/5 security parts), SC-005 (14 wire facts + diagrams), SC-006 (all mandatory sections + Experimental boilerplate), and **SC-007** (the NCFED-vs-`draft-yan`/MCP/A2A differentiation is present and restatable in one sentence). Record in the checklist.
- [X] T026 [P] Add a **pointer** to the draft from `README.md` and `docs/N2N-RISK.md` (Constitution XI doc coherence): "NCFED is documented as an IETF Internet-Draft — `docs/ietf/draft-capobianco-ncfed-00.md`."
- [X] T027 [P] Draft a short **milestone note** (Constitution XVII) for a future blog: "NCFED written up as an IETF I-D" — 1 paragraph, saved under `docs/ietf/` or noted for the WordPress flow (present to John before publishing).

---

## Dependencies & Execution Order

- **Setup (T001–T003)** → **Foundational (T004–T006)** block everything. T003 (front matter) precedes T004 (headers), which precedes all prose. T006 (figures) before the sections that reference them (T012/T013/T018).
- **US1 (T007–T010)** is the MVP — a compiling, idnits-clean shell — and should complete first among content, because T010's gate proves the toolchain works before heavy prose.
- **US2 (T011–T019)**: all edit the same draft file → **sequential**; T019 (fidelity) after T011–T018.
- **US3 (T020–T021)**: same file; after the sections they reference exist (can follow US2, but independent of US2 content correctness).
- **US4 (T022 same-file; T023 [P] separate file)**.
- **Polish (T024–T027)**: T024/T025 last (final gates); T026/T027 are `[P]` (separate files).

**Story order (priority)**: US1 → US2 → US3 → US4. US1/US2/US3 are all P1 (a submittable, faithful, security-complete draft); US4 (P2) situates it.

## Parallel Execution Examples

- Setup: T001, T002 are `[P]` (tooling install + `.gitignore`, different targets).
- Within US2/US3/US4 the draft-file section tasks are **NOT** `[P]` (one file, edited in sequence).
- Cross-file `[P]`: T023 (positioning note), T026 (README/guide pointer), T027 (blog note) — separate files, once their inputs exist.

## Implementation Strategy

**MVP = US1 (T001–T010)**: a clean, `idnits`-passing Experimental I-D shell — already submittable (thin but valid). Immediately demonstrates the toolchain and reserves the draft name.

**Increment 2 (US2)**: fill the faithful wire spec — the technical heart; gated by the 14-row fidelity check.

**Increment 3 (US3)**: the Security Considerations + IANA — what review hinges on.

**Increment 4 (US4 + polish)**: positioning, differentiation, final gates, doc pointers, milestone note → ready to upload at datatracker.ietf.org/submit and socialize at agentproto.
