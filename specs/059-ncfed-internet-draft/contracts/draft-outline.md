# Contract: draft section outline + per-section normative statements

This is the **authoring contract** — the exact normative statements each section MUST
make (so the implement phase writes prose *around* a fixed skeleton, and the fidelity
cross-check has a definite checklist). Keyword casing per RFC 2119/8174.

## Front matter (kramdown-rfc YAML)

```yaml
title: "The NetClaw-to-NetClaw Federation Protocol (NCFED)"
abbrev: "NCFED"
category: exp
docname: draft-capobianco-ncfed-00
submissiontype: IETF               # individual submission to the IETF stream, seeking agentproto WG adoption; ISE is the fallback only
number:
date:
v: 3
keyword: [federation, ai-agents, mcp, a2a, bgp, multiplexing]
venue: { github: "automateyournetwork/netclaw" }
author:
  - { fullname: "John Capobianco", organization: "Automate Your Network", email: "TODO@example.com" }
```

## §1 Introduction — MUST state

- NCFED lets independently-operated AI network agents discover/invoke/delegate over
  long-lived TCP sessions; it **carries** MCP + A2A, it does not replace them.
- Applicability: a small set of **mutually known** peers; **NOT** anonymous open federation.
- This is an individual **Experimental** submission; the author **seeks `agentproto` WG
  adoption toward a Standards-Track RFC**; the `-00` asserts no IETF consensus (FR-003a).

## §2 Conventions & Terminology — MUST define

RFC 2119/8174 boilerplate; terms: NetClaw, risk, Border, member, eN2N, iN2N, peer
AS/router-id.

## §4 Protocol Discrimination — MUST specify (FR-005)

- One listen port. First octet read (MUST close if not received within 30 s).
- `0xFF` → BGP-4. `0x4E` ('N') → read 4 more octets (MUST close if not within 10 s):
  `NCFED` → this protocol; `NCTUN` → data plane (out of scope, §ref only); else close.
- Any other first octet → close without response.

## §5 Federation Handshake — MUST specify (FR-006)

- 13 octets: `NCFED`(5) + AS(4, **network byte order**) + router-id(4, packed IPv4).
- Sent by the **initiator** only; acceptor does not echo. `{{fig-handshake}}`.

## §6 Message Framing — MUST specify (FR-007)

- Frame = length(4, unsigned, BE, payload octets only) + flags(1) + payload. `{{fig-frame}}`.
- flags bit 0 = CONTINUATION; bits 1..7 RESERVED, MUST be 0 on send, ignored on receipt.
- Max payload 65536 octets; larger messages MUST be chunked with CONTINUATION; a
  received length > 65536 → receiver MUST close.

## §7 Heartbeat & Liveness — MUST specify (FR-008)

- A **zero-length frame** (length 0, flags 0) is a heartbeat; MUST NOT be delivered to
  the application. Sent after 30 s idle. Any inbound frame proves liveness.
- 3 consecutive missed intervals (≈90 s) → the connection is dead → close.

## §8 Semantic Payload — MUST specify (FR-009, FR-010)

- UTF-8 JSON-RPC 2.0; requests carry `method`; responses carry `id`; request-id form
  `"{local-identity}:{monotonic}"`. Only `n2n/hello` is accepted before federation.
- Method families: `n2n/hello`, `n2n/inventory[_get]`, `n2n/tools/call`,
  `n2n/tasks/{submit,status,result,cancel}`, chat.
- Async task state machine: `submitted → working → {completed | failed | cancelled}`.
- Include **both** error registries verbatim (data-model §4).

## §9 Version & Capability Negotiation — MUST specify (FR-011, FR-022)

- At `n2n/hello`, peers exchange `{proto_version, features[], …}`; a peer sending no
  descriptor is treated as the `052` baseline. Feature use is gated by presence.
- The draft RECOMMENDs reserving a handshake **version octet** for a future hard break
  (guidance; the current wire has none) — MUST be phrased as future guidance, not an
  existing field.

## §10 Capability Cards — MUST specify (FR-012)

- Inventory advertises `skills`, `mcp_servers`, `badges`, plus `posture{mode,state,controls}`
  and `llm{primary_model,guarded}`. MUST state: no secrets, no per-member topology.

## §11 Trust Establishment — MUST specify (FR-013/014/015)

- **eN2N**: mutual out-of-band consent keyed by AS/router-id; SM
  `not_federated → consent_pending_{local,remote} → federated → severed`; persists across
  restart + endpoint change.
- **iN2N**: separate Border listener; `{{fig-in2n-preamble}}`; member signs the 32-octet
  nonce (ECDSA P-256/SHA-256) proving possession of its pinned self-signed key; identity
  = SHA-256 of SubjectPublicKeyInfo; single-use token `"in2n_"+urlsafe`, SHA-256-stored,
  optional TTL; **members dial outbound only** (MUST NOT accept inbound); auto-quarantine
  after ≥5 consecutive auth/health failures.
- MUST keep eN2N (multiplexed port, consent) and iN2N (separate listener, TOFU) distinct;
  note `IN2N1` already carries a version digit.

## §13 Security Considerations — MUST cover all 5 (data-model §5; FR-016/017/017a/018)

Port-sharing; confidentiality (cleartext default + SHOULD TLS, RFC 7435); TOFU; agent-
delegation hazards (+ SHOULD delegation-depth limit); DoS (+ SHOULD reassembly bound).

## §14 IANA Considerations — MUST state (FR-019)

- Request service name **`ncfed`** (RFC 6335), **no assigned port** (operator-configured;
  multiplexes on the BGP/mesh port). Document the `N`+tag magic space; **do not** request
  a registry for it. **Do not** request a fixed well-known port.

## Back matter — MUST include (FR-020)

- Prior Art & Design Rationale: contrast ALPN (RFC 7301, TLS-layer vs first-octet),
  WebSocket (RFC 6455, framing lineage), BGP-4 (RFC 4271, identity); differentiate from
  `draft-yan-a2a-device-agent-applicability` (single-domain controller→device mTLS, no
  cross-operator federation) — NCFED federates independently-operated agents and carries
  A2A/MCP. Acknowledgments: Nick (AS 65007), Byrn (AS 65099).
