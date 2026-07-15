# Feature Specification: NCFED IETF Internet-Draft (`draft-capobianco-ncfed-00`)

**Feature Branch**: `059-ncfed-internet-draft`
**Created**: 2026-07-14
**Status**: Draft
**Input**: Author NCFED as an Experimental IETF Internet-Draft that documents the already-shipped, frozen eN2N (052/053) + iN2N (056/057) wire protocol — no protocol or code changes. Ground truth: `specs/059-ncfed-internet-draft/research.md` and the reference implementation under `mcp-servers/protocol-mcp/bgp/`.

## Context & Background

NCFED (the NetClaw-to-NetClaw Federation Protocol) is live and stable: it multiplexes with BGP-4 on one TCP port, carries JSON-RPC 2.0 (MCP + A2A semantics), and defines two trust models (eN2N mutual consent; iN2N enrollment-token + TOFU). It operates today across a real multi-operator mesh. This feature produces a **standards-quality written specification** — an IETF Internet-Draft — so the protocol is **publicly documented, citable, and reviewable**, and can be socialized at the IETF `agentproto` BoF/forming Working Group (IETF 126).

This is a **documentation deliverable**. The wire is FROZEN: the draft describes exactly what the reference implementation does. All wire facts are already extracted with file:line citations in `research.md`. No open question about protocol behavior remains — the code is the ground truth.

The "users" of this feature are: the **draft author** (John), **IETF reviewers** at agentproto, **implementers** who might build an interoperable NCFED peer from the document, and the **RFC Editor / Datatracker** tooling.

## Clarifications

### Session 2026-07-14

- Q: Which RFC category should `draft-capobianco-ncfed-00` target? → A: **Experimental** for the `-00`, with an explicit Introduction note that the author seeks IETF `agentproto` WG adoption with the goal of a future Standards-Track RFC. Rationale: Standards Track cannot be self-declared (requires WG adoption + consensus + IESG, years); Experimental is immediately submittable and keeps the Independent-Submission fallback open (ISE publishes only Informational/Experimental). Re-target to Standards Track if/when the WG adopts it — no substance changes.
- Q: How should the draft handle a protocol version field, given the wire is frozen? → A: Document **in-band version negotiation at `n2n/hello`** (`proto_version` string + `features`; missing = 052 baseline) as the normative mechanism today, and **RECOMMEND** reserving a handshake version octet for a future hard break — as guidance only, NOT a wire change (preserves the freeze / FR-024).
- Q: What should IANA Considerations request? → A: Register a **service name `ncfed`** (RFC 6335) with **port = operator-configured / none** (no fixed well-known port — NCFED multiplexes on the operator's BGP/mesh port). The `N`+tag magic space (`NCFED`/`NCTUN`) is documented but a registry is NOT requested. Gives citability without claiming a port the design doesn't mandate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A submittable, tool-clean Internet-Draft (Priority: P1) 🎯 MVP

The author compiles the draft source and submits it to the IETF Datatracker without format or nits errors. The document renders to valid text/HTML, passes `idnits`, and is accepted by the submission tool.

**Why this priority**: An I-D that won't compile or fails the Secretariat's automated checks cannot be submitted at all. A clean, submittable document is the minimum viable deliverable — everything else builds on it.

**Independent Test**: Run `kdrfc draft-capobianco-ncfed-00.md` → produces `.xml`/`.txt`/`.html` with no errors; run `idnits draft-capobianco-ncfed-00.txt` → zero errors (warnings triaged/justified); the RFCXML is v3 and would upload cleanly at datatracker.ietf.org/submit.

**Acceptance Scenarios**:

1. **Given** the kramdown-rfc source, **When** compiled with `kdrfc`, **Then** it produces valid RFCXML v3 + text + HTML with no compiler errors.
2. **Given** the compiled text, **When** checked with `idnits`, **Then** there are zero errors and any remaining warnings are documented as acceptable (e.g., pre-RFC-number placeholders).
3. **Given** the front matter, **When** rendered, **Then** it carries the correct docname, Experimental category, author/affiliation, and the required IETF boilerplate (BCP 78/79 status, ISOC copyright).

---

### User Story 2 - Faithful, implementable wire specification (Priority: P1)

A competent implementer who has never seen the NetClaw code can build an interoperable NCFED peer from the document alone: discrimination, handshake, framing, heartbeat, JSON-RPC methods/errors, version negotiation, and both trust models are specified unambiguously and match the running code byte-for-byte.

**Why this priority**: A protocol spec that doesn't let a second party interoperate is not a protocol spec. Fidelity to the frozen wire is the core value — a reader must be able to reproduce it, and it must not contradict the reference implementation.

**Independent Test**: Cross-check every normative wire statement in the draft against `research.md` and the cited code (`constants.py`, `channel.py`, `agent.py`, `internal_channel.py`, `negotiate.py`, `risk.py`): each octet layout, magic, timeout, size limit, flag bit, error code, and state transition matches. A reviewer can trace every MUST/SHOULD to a code fact.

**Acceptance Scenarios**:

1. **Given** the Protocol Discrimination section, **When** compared to `agent.py`, **Then** the `0xFF`→BGP / `N`+4→`NCFED`/`NCTUN` logic, the 30 s/10 s read timeouts, and unknown→close are stated exactly.
2. **Given** the Handshake and Framing sections, **When** compared to `channel.py`, **Then** the 13-octet handshake (big-endian AS, packed-IPv4 router-id, one-way), the `4-byte length + 1-byte flags` frame, bit0=CONTINUATION (others reserved-MUST-be-zero), 64 KiB max, oversize→close, and zero-length-frame heartbeat (30 s / 3-miss / 90 s hold) are stated exactly, with ASCII packet diagrams.
3. **Given** the Semantic Payload section, **When** compared to the code, **Then** the JSON-RPC method families and the eN2N (−32001..−32010, −32601) and iN2N (−32021..−32031) error registries are complete and correct, and in-band version negotiation at `n2n/hello` (proto_version, features, 052 baseline) is specified.
4. **Given** the Trust Establishment section, **When** compared to `risk.py`/`internal_channel.py`, **Then** the eN2N consent state machine and the iN2N `IN2N1`+32-octet-nonce preamble, ECDSA-P256/SHA-256 self-signed TOFU pinning, single-use SHA-256-stored token, member-outbound hub-and-spoke, and auto-quarantine are stated exactly.

---

### User Story 3 - Security Considerations that survives IETF review (Priority: P1)

An IETF security reviewer reads the Security Considerations and finds each hazard they would raise already identified and addressed honestly: BGP port-sharing/parser reachability, TOFU pinning, cleartext-by-default confidentiality, agent-delegation hazards, and DoS.

**Why this priority**: For a protocol that shares a port with BGP, uses TOFU, runs cleartext by default, and lets a remote AI agent invoke tools on live infrastructure, Security Considerations is where the draft lives or dies. It must be substantial and candid — under-selling the risks would get the draft rejected and would be dishonest.

**Independent Test**: A security-minded reviewer maps their top concerns to the section and finds each one named, analyzed, and given a normative mitigation (RECOMMEND/SHOULD) or an explicit honest limitation. No hazard from `research.md` Part 3 is omitted.

**Acceptance Scenarios**:

1. **Given** port multiplexing with BGP, **When** the reviewer checks, **Then** the draft analyzes parser reachability from any host that can reach the BGP port and RECOMMENDs BGP-style TTL-security/ACLs, plus the discrimination read-timeout bounds.
2. **Given** the cleartext-by-default transport, **When** the reviewer checks, **Then** the draft states it plainly and RECOMMENDs (SHOULD) TLS or an encrypted underlay for untrusted paths, noting the iN2N optional-TLS `CERT_NONE` (encryption-only) caveat, framed via Opportunistic Security (RFC 7435).
3. **Given** TOFU enrollment, **When** the reviewer checks, **Then** the draft covers token entropy, transport expectations, the active-attacker-at-enrollment window, and the re-enrollment/quarantine recovery path.
4. **Given** agent delegation, **When** the reviewer checks, **Then** the draft covers per-peer authorization scoping, prompt-injection across the federation boundary, Border audit logging, production-mode guardrails, and a SHOULD-level delegation-depth/loop limit; and DoS covers frame-size limits, a SHOULD-level bound on continuation reassembly, and heartbeat/cold-start exhaustion.

---

### User Story 4 - Positioned and differentiated for agentproto (Priority: P2)

A reader placing NCFED in the 2026 agent-protocol landscape understands what it is (a cross-operator federation/identity/transport layer that *carries* MCP + A2A), how it differs from the closest IETF work (`draft-yan-a2a-device-agent-applicability`), and how the author intends to socialize it.

**Why this priority**: Positioning turns "a single-vendor protocol dump" into "a contribution the WG can situate." Essential for adoption but not for the document's technical validity, so P2.

**Independent Test**: The draft's Prior Art / Design Rationale differentiates NCFED from A2A/MCP (carries, not competes), from ALPN (first-octet vs TLS-layer discrimination), from WebSocket (framing lineage), and from `draft-yan` (single-domain controller→device mTLS vs multi-operator BGP-identity federation). A companion note explains the agentproto socialization path.

**Acceptance Scenarios**:

1. **Given** the back matter, **When** read, **Then** it cites and contrasts ALPN (RFC 7301), WebSocket (RFC 6455), BGP-4 (RFC 4271), and `draft-yan-a2a-device-agent-applicability`.
2. **Given** the companion note, **When** read, **Then** it states the recommended venue (agentproto BoF/forming WG at IETF 126), the ISE fallback, and the differentiation talking points.

---

### Edge Cases

- **Pre-RFC-number placeholders**: the draft references itself as `draft-capobianco-ncfed-00`; RFC-number/date fields are tool-filled — the source must not hardcode them wrongly (idnits would warn).
- **Author email/affiliation**: front matter needs a real author email before submission — a visible fill-in, not a silent placeholder.
- **NCTUN scope**: the sibling data-plane tunnel is referenced (it shares the `N`+magic discrimination space) but MUST be out of scope / "not specified here" — the draft must not under-specify it as if normative.
- **Two protocols, one document**: eN2N and iN2N share framing but differ in transport/trust/port. The document must keep them clearly separated so a reader doesn't conflate consent with TOFU, or the multiplexed port with the separate iN2N listener.
- **Wire vs application version**: eN2N has no binary version field (negotiated at `n2n/hello`); the draft must document this accurately and only *recommend* reserving a wire version octet — not claim one exists.
- **Meeting submission window**: submissions freeze for ~2 weeks around each IETF meeting — the note must flag this so a revision isn't blocked unexpectedly.
- **Encrypted-capture honesty**: the packet capture is taken inside a TLS tunnel, so it is flow-level evidence (ciphertext payload), NOT a plaintext NCFED dissection. The appendix must say so plainly and MUST NOT present it as proof of the plaintext wire; a plaintext capture (loopback/key-owned underlay) is future work.

## Requirements *(mandatory)*

### Functional Requirements

#### Document structure & tooling (US1)

- **FR-001**: The draft MUST be authored in kramdown-rfc Markdown that compiles via `kdrfc` to RFCXML **v3**, text, and HTML with no compiler errors.
- **FR-002**: The compiled text MUST pass `idnits` with zero errors; any residual warnings MUST be documented as acceptable in the submission checklist.
- **FR-003**: The front matter MUST set title, `abbrev: NCFED`, `category: exp`, `docname: draft-capobianco-ncfed-00`, author (John Capobianco / Automate Your Network) with a clearly marked email fill-in, and the project GitHub venue.
- **FR-003a**: The Introduction MUST include a note that this is an individual Experimental submission and that the author seeks adoption by the IETF `agentproto` Working Group with the goal of a future Standards-Track RFC (the `-00` does not assert IETF consensus). The draft's technical substance MUST remain category-neutral so it can be re-targeted to Standards Track on WG adoption without content change.
- **FR-004**: The document MUST contain all mandatory I-D sections: Abstract, Introduction (with Motivation/Applicability), Conventions & Terminology, Security Considerations, IANA Considerations, and References (normative + informative), plus back matter.

#### Faithful wire specification (US2)

- **FR-005**: The draft MUST specify **protocol discrimination** exactly as implemented: single listen port; first octet `0xFF`→BGP-4; `0x4E` (`N`) + 4 octets → `NCFED`/`NCTUN`; 30 s first-octet and 10 s magic read timeouts; unknown octet/magic → close without response.
- **FR-006**: The draft MUST specify the **13-octet NCFED handshake** (`NCFED` magic + 4-octet big-endian AS + 4-octet packed-IPv4 router-id, one-way initiator→acceptor) with an ASCII packet diagram, and state network byte order.
- **FR-007**: The draft MUST specify the **frame format** (4-octet big-endian length + 1-octet flags; bit 0 = CONTINUATION; all other bits reserved, MUST be 0 on send and ignored on receipt; 64 KiB max payload; larger messages chunked; oversize → close) with an ASCII diagram.
- **FR-008**: The draft MUST specify the **heartbeat as a zero-length frame** every 30 s, with a 3-missed-interval / 90 s hold, and that any inbound frame resets liveness.
- **FR-009**: The draft MUST specify the **JSON-RPC 2.0 semantic payload** (UTF-8, request/response/notification, request-id form) and the method families (`n2n/hello`, `n2n/inventory[_get]`, `n2n/tools/call`, `n2n/tasks/{submit,status,result,cancel}`, chat), including the async task-delegation state machine.
- **FR-010**: The draft MUST include the complete **error-code registries**: eN2N (−32001..−32010, −32601) and iN2N (−32021..−32031).
- **FR-011**: The draft MUST specify **in-band version & capability negotiation** at `n2n/hello` (`proto_version` monotonic string, `features` list; a peer sending no descriptor is treated as the 052 baseline).
- **FR-012**: The draft MUST specify the **A2A capability card** contents advertised in the inventory (skills, mcp_servers, badges, and the posture {mode, state, controls} + llm {primary_model, guarded} fields), stating that no secrets and no per-member topology are exposed.

#### Trust models (US2)

- **FR-013**: The draft MUST specify **eN2N trust**: mutual operator consent, identity keyed by AS/router-id verified out-of-band, and the persisted state machine `not_federated → consent_pending_{local,remote} → federated → severed`, surviving restarts and endpoint changes.
- **FR-014**: The draft MUST specify **iN2N trust**: the separate Border listener; the `IN2N1` magic + 32-octet nonce preamble; the member reply (`in2n/hello`/`in2n/enroll`) signing the nonce; ECDSA-P256/SHA-256 self-signed key with TOFU pinning (identity = SHA-256 of the SubjectPublicKeyInfo); single-use enrollment token (`"in2n_"`+urlsafe, SHA-256-stored, optional TTL); member-initiated outbound hub-and-spoke (members never accept inbound); and auto-quarantine after repeated failures.
- **FR-015**: The draft MUST clearly separate eN2N (multiplexed mesh port, consent) from iN2N (separate listener, TOFU) so they are not conflated, and MUST note the `IN2N1` magic already carries a version digit.

#### Security Considerations (US3)

- **FR-016**: Security Considerations MUST analyze **BGP port-sharing** (NCFED parser reachable by anyone who can reach the BGP port) and RECOMMEND applying BGP-style TTL-security/ACLs to the shared port, plus the discrimination read-timeout bounds as MUST-close.
- **FR-017**: Security Considerations MUST state that NCFED is **cleartext by default** and RECOMMEND (SHOULD) TLS or an encrypted underlay for any untrusted path, noting the iN2N optional-TLS `CERT_NONE` (encryption-only; auth = signed nonce), framed via Opportunistic Security (RFC 7435).
- **FR-017a**: Security Considerations MUST address **TOFU**: token entropy, token transport expectations, the active-attacker-at-enrollment window, and the recovery/re-enrollment/quarantine procedure.
- **FR-018**: Security Considerations MUST address **agent-delegation hazards** (per-peer authorization scoping, prompt-injection across the federation boundary, Border audit logging, production-mode guardrails, and a SHOULD-level delegation-depth/loop limit) and **DoS** (frame-size limits, a SHOULD-level bound on continuation reassembly, heartbeat/cold-start exhaustion).

#### IANA, positioning, deliverables (US1/US4)

- **FR-019**: IANA Considerations MUST request registration of the **service name `ncfed`** per RFC 6335 with **no assigned port** (port = operator-configured; NCFED multiplexes on the operator's BGP/mesh port), and MUST document the `N`+tag magic space (`NCFED`/`NCTUN`) while explicitly **not** requesting a registry for it. It MUST NOT request a fixed well-known TCP port (which would misrepresent the multiplexed design).
- **FR-020**: The back matter MUST include Prior Art / Design Rationale differentiating NCFED from ALPN (RFC 7301), WebSocket (RFC 6455), BGP-4 (RFC 4271), and `draft-yan-a2a-device-agent-applicability` (single-domain controller→device mTLS vs multi-operator BGP-identity federation), positioning NCFED as carrying (not competing with) MCP/A2A; plus Acknowledgments to the first three-node mesh operators (AS 65007, AS 65099).
- **FR-021**: The feature MUST deliver: the kramdown-rfc source `draft-capobianco-ncfed-00.md`; the ASCII-art stack + handshake + frame diagrams; a **submission checklist** (kdrfc compile, idnits clean, RFCXML v3, Datatracker submission, BCP 78/79 rights); and a short **agentproto socialization + draft-yan differentiation note**.
- **FR-022**: The draft MUST document that eN2N version is negotiated in-band and RECOMMEND reserving a handshake version octet for a future hard break — as a documented decision, not a claim that such an octet exists today.

#### Fidelity & freeze (cross-cutting)

- **FR-023**: Every normative wire statement MUST match the reference implementation and `research.md`; the draft MUST NOT specify any behavior the code does not implement (recommendations beyond the code MUST be marked SHOULD/RECOMMEND and identified as such).
- **FR-024**: This feature MUST NOT change the eN2N/iN2N wire, framing, trust models, or any code path; it is documentation only. NCTUN is referenced but explicitly out of scope.

#### Running-code evidence (US2)

- **FR-025**: The draft MUST include an **RFC 7942 "Implementation Status"** appendix (marked for removal before RFC publication) documenting the deployed NetClaw implementation and citing the live packet capture (`docs/ietf/captures/ncfed-johns-risk-nick-20260714.pcap`, AS 65001 ↔ AS 65007). It MUST report the capture accurately (single established TCP conversation; 24 packets / 3141 octets; no SYN/FIN/RST, zero retransmissions/dup-ACKs; the observed segment sizes) AND MUST state the **honest scope limitation**: the capture is taken inside the peer's TLS-terminated tunnel, so payload octets are ciphertext — it is first-hand evidence of the NCFED *channel* (endpoints, persistence, TCP health, request/response shape) but NOT a plaintext frame dissection; a plaintext frame-level capture requires app-layer/loopback or a key-owned underlay (future work). The appendix MUST NOT overstate the capture as proof of the plaintext wire.

### Key Entities

- **Internet-Draft document**: the `draft-capobianco-ncfed-00` source + renderings; the primary deliverable.
- **Wire-fact ↔ code citation map**: the correspondence between each normative statement and its `research.md`/code source (the fidelity guarantee).
- **Error-code registries**: eN2N and iN2N JSON-RPC error tables.
- **Trust models**: eN2N consent state machine; iN2N enrollment/TOFU/quarantine.
- **Submission checklist**: the gate list for a clean Datatracker submission.
- **Positioning note**: agentproto venue + differentiation from `draft-yan` and MCP/A2A.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `kdrfc` compiles the source to RFCXML v3 + text + HTML with **zero errors**.
- **SC-002**: `idnits` reports **zero errors**; 100% of remaining warnings are enumerated with justification in the submission checklist.
- **SC-003**: **100%** of the normative wire statements (discrimination, handshake, framing, heartbeat, methods, error codes, version negotiation, both trust models) match the reference implementation, verified against `research.md` citations — **zero contradictions**.
- **SC-004**: Every hazard listed in `research.md` Part 3 appears in Security Considerations with a stated mitigation or honest limitation (**0 omissions**).
- **SC-005**: An implementer can locate, for each of the ~14 core wire facts, an unambiguous normative statement + a diagram where applicable (spec-completeness review passes).
- **SC-006**: The document contains all IETF-mandatory sections and correct Experimental-category boilerplate (Secretariat automated-check equivalent passes).
- **SC-007**: The draft differentiates NCFED from `draft-yan-a2a-device-agent-applicability` and from MCP/A2A in a way a WG reviewer can restate in one sentence (positioning review passes).
- **SC-008**: The Implementation Status appendix's capture figures **exactly match** `capinfos`/`tshark` on the committed pcap (24 pkts, 3141 octets, endpoints, 0 SYN/FIN/RST, 0 retransmits, the segment-size set), and the honest-scope limitation (ciphertext/flow-level, not plaintext frames) is stated — **0 overclaims**.

## Assumptions

- **Frozen wire**: the eN2N/iN2N protocol is stable and will not change to suit the draft; the draft documents what exists (branch `main` after feature 057).
- **Ground truth is the code + research.md**: no protocol behavior is invented; `research.md` already resolved all wire facts with citations.
- **Tooling available**: `kramdown-rfc`/`kdrfc` and `idnits` are used to build/validate; the author has (or will add) a real email before submission.
- **Category Experimental (with Standards-Track ambition)**: the `-00` is Experimental — immediately submittable and ISE-fallback-compatible — with an Introduction note seeking `agentproto` WG adoption toward a future Standards-Track RFC (re-target on adoption; no substance change). Standards Track cannot be self-declared on an individual draft.
- **Out of scope**: any wire/code change; a full NCTUN specification (referenced only); implementing the two SHOULD-level hardening items in code (they are Security Considerations recommendations here, tracked separately if pursued).
- **No live-system dependency**: authoring the draft does not require the running mesh; correctness is verified against source, not a live capture (a live packet capture is a nice-to-have, not required).
