# Phase 1 Data Model: NCFED Internet-Draft

The "entities" of a documentation feature are the **document's structural units** and
the **fidelity relationships** that keep every normative statement tied to ground
truth. No runtime data model. This drives `tasks.md` and the fidelity cross-check.

## 1. Draft document (the deliverable)

| Field | Value |
|-------|-------|
| docname | `draft-capobianco-ncfed-00` |
| category | `exp` (Experimental) + Introduction note seeking `agentproto` WG adoption → Standards-Track ambition (FR-003a) |
| abbrev | `NCFED` |
| author | John Capobianco / Automate Your Network (email = explicit fill-in `TODO@…`) |
| source format | kramdown-rfc Markdown → RFCXML v3 |
| venue | github `automateyournetwork/netclaw` |

## 2. Section model (order is normative for an I-D)

| # | Section | Contract (what it must contain) | FRs |
|---|---------|--------------------------------|-----|
| — | Front matter | title/abbrev/category/docname/author/venue + boilerplate | FR-003, FR-003a |
| — | Abstract | ≤ ~20 lines; what NCFED is (federation transport carrying MCP+A2A) | FR-004 |
| 1 | Introduction + Motivation/Applicability | 3-operator mesh + monolith→risk; long-lived known peers, NOT anonymous; the WG-ambition note | FR-004, FR-003a |
| 2 | Conventions & Terminology | RFC 2119/8174; NetClaw, risk, Border, member, eN2N, iN2N, peer AS/router-id | FR-004 |
| 3 | Protocol Stack Overview | ASCII stack diagram | FR-004 (+ diagram) |
| 4 | Protocol Discrimination | 0xFF→BGP; N+4→NCFED/NCTUN; 30s/10s; unknown→close | FR-005 |
| 5 | Federation Handshake | 13-octet layout + ASCII packet diagram; big-endian; one-way | FR-006 |
| 6 | Message Framing | 4B len + 1B flags; bit0 CONTINUATION, rest reserved; 64 KiB; oversize→close; ASCII diagram | FR-007 |
| 7 | Heartbeat & Liveness | zero-length frame; 30s/3-miss/90s hold; inbound resets | FR-008 |
| 8 | Semantic Payload | JSON-RPC 2.0; method families; task state machine; error registries | FR-009, FR-010 |
| 9 | Version & Capability Negotiation | in-band `n2n/hello` (proto_version/features/052 baseline); RECOMMEND future version octet | FR-011, FR-022 |
| 10 | Capability Cards (A2A) | skills/mcp_servers/badges + posture{…} + llm{…}; no secrets/topology | FR-012 |
| 11 | Trust Establishment | eN2N consent SM; iN2N IN2N1+nonce+TOFU; member outbound-only; quarantine | FR-013, FR-014, FR-015 |
| 12 | Operational Considerations | hot/cold hybrid; least privilege; standalone = risk-of-one | (context) |
| 13 | Security Considerations | 5 parts (see §5 below) — MANDATORY, substantial | FR-016..018 |
| 14 | IANA Considerations | service name `ncfed`, no port; magic space documented, no registry | FR-019 |
| — | Back: Prior Art & Rationale | ALPN/WebSocket/BGP + draft-yan differentiation; NCFED carries MCP/A2A | FR-020 |
| — | Back: Acknowledgments | Nick AS65007, Byrn AS65099 | FR-020 |
| — | References | normative + informative (see §6) | FR-004 |

## 3. Wire-fact ↔ code fidelity map (the correctness spine)

Every row MUST appear as an unambiguous normative statement in the cited section, and
MUST match the code. (Full detail + line numbers in `research.md`.)

| # | Wire fact | Draft § | Code source |
|---|-----------|---------|-------------|
| 1 | First-octet discrimination 0xFF/`N`, 30s/10s timeouts, unknown→close | 4 | `agent.py:275-328` |
| 2 | Magics: `NCFED`/`NCTUN` (5 octets) | 4 | `constants.py:187,195` |
| 3 | 13-octet handshake, big-endian AS, packed-IPv4 router-id, one-way | 5 | `channel.py:248-264` |
| 4 | Frame = `!IB` (4B BE len + 1B flags), bit0 CONTINUATION | 6 | `channel.py:48-61,133` |
| 5 | 64 KiB max payload; oversize→close; chunking | 6 | `constants.py:197`, `channel.py:134` |
| 6 | Reserved flag bits MUST be 0 / ignored | 6 | (only bit0 defined — `constants.py:198`) |
| 7 | Heartbeat = zero-length frame; 30s/3-miss/90s | 7 | `channel.py:155-178`, `constants.py:199-200` |
| 8 | JSON-RPC 2.0; request-id `"{identity}:{n}"`; only hello pre-federation | 8 | `channel.py:182-245,202,231` |
| 9 | eN2N error codes −32001..−32010, −32601 | 8 | `channel.py:27-36` |
| 10 | iN2N error codes −32021..−32031 | 8/11 | `constants.py:224-229` |
| 11 | In-band negotiation proto_version/features; missing=052 | 9 | `negotiate.py:17-62` |
| 12 | Capability card fields incl. posture + llm | 10 | `inventory.py` (057) |
| 13 | eN2N consent SM not_fed→pending_{l,r}→federated→severed | 11 | `manager.py` PeerState |
| 14 | iN2N IN2N1(5B)+nonce(32B); ECDSA-P256/SHA-256 TOFU; token urlsafe(24) sha256 single-use; outbound-only; quarantine≥5 | 11 | `internal_channel.py:92-111`, `risk.py:79-311`, `constants.py:220-232` |

## 4. Error-code registries (verbatim into §8)

**eN2N** (`channel.py:27-36`): −32001 NOT_ALLOWLISTED · −32002 APPROVAL_PENDING · −32003
APPROVAL_EXPIRED · −32004 BUDGET_EXHAUSTED · −32005 RATE_LIMITED · −32006
EXECUTION_TIMEOUT · −32007 SEVERED · −32008 GUARDRAIL_BLOCKED · −32010 NOT_FEDERATED ·
−32601 METHOD_NOT_FOUND (JSON-RPC standard).

**iN2N** (`constants.py:224-229`): −32021 ENROLL_TOKEN_INVALID · −32022 MEMBER_ID_TAKEN ·
−32023 MEMBER_NOT_TRUSTED · −32024 NOT_A_BORDER · −32030 NO_CAPABLE_MEMBER · −32031
OUT_OF_SCOPE.

## 5. Security Considerations structure (§13 — five mandatory parts)

1. **Port-sharing with BGP** — parser reachable by anyone who can reach the BGP port; RECOMMEND BGP-style TTL-security/ACLs; read-timeout MUST-close. (FR-016)
2. **Confidentiality** — cleartext by default; SHOULD TLS / encrypted underlay; iN2N optional TLS is CERT_NONE (encryption-only); framed via RFC 7435. (FR-017)
3. **TOFU** — token entropy (~144 bits), transport, active-attacker-at-enrollment window, recovery/quarantine. (FR-017a)
4. **Agent-delegation hazards** — per-peer authz scoping, prompt-injection across boundary, Border audit, production guardrails, SHOULD delegation-depth/loop limit. (FR-018)
5. **DoS** — 64 KiB frame cap, SHOULD bound continuation reassembly, heartbeat/cold-start exhaustion. (FR-018)

## 6. References model

- **Normative:** RFC 2119, RFC 8174, RFC 4271, RFC 8259, JSON-RPC 2.0.
- **Informative:** RFC 7301 (ALPN), RFC 6455 (WebSocket), RFC 7435 (Opportunistic Security), RFC 6335 (service-name/port), RFC 8126 (IANA guidance), MCP, A2A, `draft-yan-a2a-device-agent-applicability`.

## 7. Genuine fill-ins (author actions, not spec gaps)

- Author email in front matter (`TODO@…` → real address before submission).
- `date:` left blank (tool-filled at submission).
- RFC-number self-references stay as `draft-capobianco-ncfed-00` (no RFC number yet).
