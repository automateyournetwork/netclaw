# Research: NCFED as an IETF Internet-Draft (`draft-capobianco-ncfed`)

**Purpose:** resolve every `TODO:` in the draft skeleton with **ground truth from the
running code** (file:line citations), and capture the **external IETF landscape** so
the spec/draft is accurate on first submission. Nothing here is guessed — wire facts
are read from the implementation.

---

## Part 1 — Internal ground truth (resolves the skeleton's TODOs)

### 1.1 Protocol discrimination (single mesh port) — `bgp/agent.py:275-328`, `constants.py:187-200`

An NCFED node listens on one configured TCP port (live: **1179**; `BGP_PORT`=179 is the
protocol default). On accept, it reads the **first octet** (`readexactly(1)`, timeout
**30 s**):

- `0xFF` → BGP-4 (the 16-octet all-ones marker, `BGP_MARKER = b'\xff'*16`). The byte is
  replayed into the BGP parser.
- `0x4E` (`'N'`) → read **4 more octets** (timeout **10 s**), forming a 5-octet magic:
  - `NCFED` (`b'NCFED'`) → federation channel → `read_handshake`.
  - `NCTUN` (`b'NCTUN'`) → data-plane tunnel (out of scope for the draft).
  - anything else → **close, no response**.
- any other first octet → **close, no response** (`agent.py:325`).

**Resolves:** the discrimination read-timeout TODO (30 s first octet / 10 s magic).
**Correction to skeleton:** magics are the full **5-octet** `NCFED`/`NCTUN`, not `'N'`+4;
BGP is `0xFF` (a full 16-octet marker follows).

### 1.2 Federation handshake (13 octets) — `channel.py:248-264`

`build_handshake(local_as, router_id)` = `NCFED` (5B) + `struct.pack("!I", local_as)`
(4B AS) + `IPv4Address(router_id).packed` (4B). **Total 13 octets.**

- **Byte order: network (big-endian)** — `struct` `!` prefix. *(Resolves the byte-order TODO.)*
- **Router-id is a 4-octet IPv4 address** (packed), not an arbitrary id — `read_handshake`
  decodes it with `ipaddress.IPv4Address`.
- **Handshake is one-way** (initiator → acceptor); the acceptor does **not** echo a binary
  handshake. Mutual identity + capability/version exchange happens at the JSON-RPC layer
  via `n2n/hello` (see 1.5). `read_handshake` timeout **10 s**.
- **No version field in the binary handshake.** *(Resolves the version-field TODO — but see
  the recommendation in Part 3: version is negotiated in-band; the draft should document
  that and MAY reserve a wire version for future hard breaks.)*

### 1.3 Message framing — `channel.py:48-61,128-153`, `constants.py:196-200`

Frame = `struct.pack("!IB", length, flags)` + payload:

- **Length:** unsigned **32-bit, big-endian**, payload octets only.
- **Flags:** 1 octet. **Bit 0 (`0x01`) = CONTINUATION** (payload is a chunk; concatenate
  until a frame with the bit clear). **No other flag bits are defined.**
- **Max payload = 65536 (64 KiB)** (`NCFED_MAX_PAYLOAD`); larger messages are chunked with
  CONTINUATION. A received `length > 65536` → **close** (`channel.py:134`).
- **Heartbeat is a ZERO-LENGTH frame** (`struct.pack("!IB", 0, 0)`), **not a flag bit**
  (`channel.py:168`). An empty reassembled buffer is treated as a heartbeat and not
  delivered to the app layer (`channel.py:143`).

**Correction to skeleton:** there is **no HEARTBEAT flag bit** — the skeleton's "bit 1
HEARTBEAT" is wrong. Heartbeat = empty frame. Only bit 0 (CONTINUATION) exists; all other
bits are currently unused (the draft SHOULD say "MUST be 0 on send, ignored on receipt").

### 1.4 Heartbeat & hold timer — `channel.py:155-178`, `constants.py:199-200`

- Heartbeat every **30 s** of channel idleness (`NCFED_HEARTBEAT_INTERVAL`).
- **Hold = 3 missed intervals** (`NCFED_HEARTBEAT_MISS_LIMIT`) → **90 s** → close → the
  `on_close` hook fires the reconnect supervisor. *(Resolves the hold-timer TODO; note it
  mirrors BGP's 90 s hold / 30 s keepalive in `constants.py:48-49`.)*
- **Any inbound frame (including a heartbeat) resets the miss counter** (`channel.py:132`).
- Reconnect/backoff is handled by the service supervisor (053 reliability work).

### 1.5 Semantic payload — JSON-RPC 2.0 — `channel.py:182-245`

UTF-8 JSON-RPC 2.0. `{"jsonrpc":"2.0","id":<id>,"method":...,"params":...}`. Request id =
`"{local_identity}:{monotonic counter}"` (`channel.py:231`). A message with `method` is a
request/notification; with only `id` is a response. **Only `n2n/hello` is accepted before
federation is established** (`channel.py:202`).

**eN2N JSON-RPC error codes** (`channel.py:27-36`) — the draft's error registry:

| Code | Name | Code | Name |
|---|---|---|---|
| -32001 | NOT_ALLOWLISTED | -32006 | EXECUTION_TIMEOUT |
| -32002 | APPROVAL_PENDING | -32007 | SEVERED |
| -32003 | APPROVAL_EXPIRED | -32008 | GUARDRAIL_BLOCKED |
| -32004 | BUDGET_EXHAUSTED | -32010 | NOT_FEDERATED |
| -32005 | RATE_LIMITED | -32601 | METHOD_NOT_FOUND (JSON-RPC std) |

**Method families** (from inventory/invocation/chat/tasks modules):
- `n2n/hello` — mutual identity + **capability descriptor** (version negotiation, 1.6).
- `n2n/inventory`, `n2n/inventory_get` — capability-card push/pull (the A2A card; now
  carries `posture` + `llm`, feature 057).
- `n2n/tools/call` — MCP-style remote tool invocation (authorization-gated).
- `n2n/tasks/submit|status|result|cancel` — async delegation (053).
- chat methods (US3).

### 1.6 Version / capability negotiation — `negotiate.py:17-62`

**In-band at `n2n/hello`**, not a wire field. Descriptor:
`{proto_version:"053", features:[async_tasks, endpoint_reannounce, negotiate], agent_invoke, reply_shapes}`.
A peer that sends **no** descriptor is treated as `proto_version:"052"` baseline (graceful
degrade). Feature negotiation is by presence in `features`. *(Resolves the version-negotiation
TODO: NCFED versions at the application layer via a monotonic `proto_version` string +
feature list — clean and extensible.)*

### 1.7 iN2N transport — SEPARATE listener, not multiplexed — `internal_channel.py`, `constants.py:213-221`

**Correction to skeleton:** iN2N does **not** ride the 1179 discrimination path. It is a
**separate Border listener** on `N2N_IN2N_PORT` (live: **11790**). Members dial it outbound
(hub-and-spoke; members never accept inbound — `internal_channel.py:6-8`).

Transport preamble (`internal_channel.py:92-111`):
- **Border → member:** `IN2N_MAGIC` (`b'IN2N1'`, 5B — **note the trailing `1` is a
  version digit**) + **32-octet nonce** (`os.urandom(32)`, `IN2N_NONCE_SIZE`).
- **member → Border:** JSON-RPC `in2n/hello` or `in2n/enroll` (over the *same NCFED
  framing*), **signing the nonce** to prove possession of its pinned key.
- Then the standard NCFED JSON-RPC channel runs (`InternalChannel` subclasses
  `FederationChannel`, reusing framing/heartbeat/dispatch; replaces the `is_federated` gate
  with a `trusted` flag set after signed-nonce verification — `internal_channel.py:59-70`).
- **Pre-trust methods:** only `in2n/hello`, `in2n/enroll`.

**iN2N error codes** (`constants.py:224-229`): -32021 ENROLL_TOKEN_INVALID, -32022
MEMBER_ID_TAKEN, -32023 MEMBER_NOT_TRUSTED, -32024 NOT_A_BORDER, -32030 NO_CAPABLE_MEMBER,
-32031 OUT_OF_SCOPE. *(Resolves the IN2N signed-nonce TODO: `IN2N1` magic + 32B nonce +
ECDSA-P256 signature; and the iN2N magic already carries a version digit.)*

### 1.8 Trust models & crypto — `risk.py:79-171,241-311`

- **eN2N (external):** mutual operator **consent**, out-of-band identity check of
  AS/router-id. Consent persists in SQLite (`manager.py` `PeerState`:
  `not_federated → consent_pending_{local,remote} → federated → severed`; `consent_record`
  rows `local_grant|remote_grant`). Consent survives restarts and endpoint churn (FR-028).
- **iN2N (internal):** single-use **enrollment token** + **TOFU key pinning**.
  - Token: `"in2n_" + secrets.token_urlsafe(24)` (≈144 bits entropy); **only its SHA-256 is
    stored**; single-use (`spent_at`); optional TTL (`risk.py:241-256`).
  - Member generates its **own** keypair at runtime: **ECDSA on SECP256R1 (NIST P-256),
    SHA-256**, self-signed X.509, 10-year validity (`risk.py:96-119`).
  - Border **pins** the member's key on first contact (TOFU); identity = SHA-256 of the
    cert's `SubjectPublicKeyInfo` DER (`risk.py:154-163`).
  - Reconnect proof: ECDSA signature over the 32-octet Border nonce
    (`sign_challenge`/`verify_possession`, `risk.py:132-152`).
  - Removal unpins; **auto-quarantine** after `N2N_QUARANTINE_THRESHOLD` (default 5)
    consecutive auth/health failures (`risk.py`, `constants.py:232`).

### 1.9 Confidentiality — **cleartext by default** — `internal_channel.py:114-125`

- **eN2N:** the `FederationChannel` uses the raw TCP reader/writer; no TLS in the eN2N path
  — it runs **in cleartext** over the (ngrok/overlay/private) transport. Integrity/authenticity
  of the *peer identity* rests on the out-of-band consent check, **not** on transport crypto.
- **iN2N:** **plaintext by default** (loopback). Optional TLS wrapper
  (`build_ssl_contexts`) for distributed members — but **`verify_mode = CERT_NONE`**: TLS
  provides **encryption only**; the authentication guarantee is the app-layer signed nonce.

**This is the single most important Security Considerations input** (Part 3).

### 1.10 Routing determinism (iN2N) — `router.py`

Border selects the owning member deterministically: most-specific specialist wins; ties
break lexicographically by member id. A Border MUST NOT advertise a capability it can't
route (`IN2N_ERR_NO_CAPABLE_MEMBER` if none). Base-floor capabilities are excluded from the
specificity tie-break.

### 1.11 Ports (for IANA Considerations)

- Mesh/BGP-shared listener: **1179** live (protocol default BGP 179). NCFED has **no
  registered port** today — it reuses the operator's configured mesh port.
- iN2N listener: **`N2N_IN2N_PORT`** (live 11790), operator-configured.
- DefenseClaw guardrail proxy: 4000 (out of scope).

---

## Part 2 — External landscape (IETF, 2026)

### 2.1 The process (confirmed current)

1. **Write an Internet-Draft**, RFCXML **v3** preferred; author via kramdown-rfc/mmark →
   `kdrfc`, or authors.ietf.org tooling; run **idnits** before submitting.
2. **Submit via the Datatracker** submission tool (RFCXML preferred; it renders TXT/HTML and
   runs xml2rfc + idnits). Email verification unless logged in as a listed author. Submitting
   grants rights under **BCP 78/79**.
3. **I-Ds expire after ~6 months**; they confer **no status** — they exist to drive
   discussion. Socialize on the relevant list / at a meeting.
4. **Two routes to an RFC number:** IETF stream (WG adopts → consensus → IESG → Standards
   Track/Informational), or **Independent Submission Stream** (ISE → Informational/Experimental,
   RFC 4846), with an IESG conflict review (RFC 5742).
5. **Meeting cadence caveat:** the I-D submission window closes ~2 weeks around each IETF
   meeting (e.g., closed 2026-07-06, reopened 2026-07-18) — plan revisions around it.

### 2.2 The venue that changes the strategy — the `agentproto` BoF (IETF 126, Vienna)

There is now an **`agentproto` Birds-of-a-Feather** at IETF 126, building on an IETF 124
side meeting and framework/use-case/requirements work by **Jonathan Rosenberg & Cullen
Jennings**, explicitly aiming to **charter a Working Group** for agent-to-agent and
agent-to-tool communication (MCP, A2A, ACP, ANP, and related I-Ds are in scope). **This is
the natural home for NCFED** — socialize there rather than going straight to the ISE.

### 2.3 Closest prior art — `draft-yan-a2a-device-agent-applicability`

"Applicability of A2A Protocol for Network Management Agents." Deploys AI agents on network
devices (DA) talking to Controller Agents (CA) over **A2A** with **mutual TLS**, HTTP+JSON /
WebSocket, and **Agent Cards** for discovery. **Crucially, it is single administrative
domain, hierarchical (controller→device), and does NOT federate independently-operated
agents.** NCFED must cite and differentiate from it.

### 2.4 NCFED's positioning (differentiation)

NCFED is **not a competitor to MCP or A2A** — it *carries* them. It is a **cross-operator
federation + identity + transport layer**:

- **eN2N**: federation between **independently-operated** agents (different trust domains),
  keyed by **BGP-style AS/router-id identity** + **mutual consent** — the multi-operator
  case the yan draft explicitly does not address.
- **iN2N**: intra-operator hub-and-spoke via **enrollment-token + TOFU self-signed pinning**
  (member-initiated outbound), a lighter alternative to the yan draft's mTLS-PKI
  controller→device model.
- **Novel wire trick**: **port multiplexing with BGP-4** (first-octet discrimination) on the
  operator's existing mesh port — no prior agent protocol does this.
- **Payload**: JSON-RPC 2.0 carrying MCP (`tools/*`) + A2A-style capability cards and async
  tasks — so NCFED could be framed as *a federation binding that transports A2A/MCP between
  operators.*

### 2.5 RFC references to cite

- **Normative:** RFC 2119 + 8174 (keywords), RFC 4271 (BGP-4), RFC 8259 (JSON), JSON-RPC 2.0.
- **Informative / prior art:** RFC 7301 (ALPN — the analogous but TLS-layer discrimination),
  RFC 6455 (WebSocket — framing/handshake lineage), RFC 7435 (Opportunistic Security — frames
  the cleartext/TOFU stance honestly), RFC 6335 (service-name/port registration procedures,
  for IANA), RFC 8126 (IANA Considerations guidance), `draft-yan-a2a-device-agent-applicability`,
  MCP + A2A specs, and the `agentproto` framework/requirements drafts once published.

---

## Part 3 — Decisions the draft must make (genuine gaps, not code bugs)

These are places where the code has a concrete behavior but an RFC should **specify a
requirement** the current single implementation leaves implicit:

1. **Version wire-reservation.** eN2N has no binary version field (negotiated at `n2n/hello`);
   iN2N encodes `1` in `IN2N1`. **Recommend:** document in-band negotiation as normative AND
   reserve a handshake version octet for future hard breaks before `-01`.
2. **Confidentiality.** State plainly that NCFED is cleartext by default and **RECOMMEND**
   (SHOULD) TLS or an encrypted underlay (NCTUN/WireGuard/overlay) for any path crossing an
   untrusted network; frame with RFC 7435. For iN2N, note optional TLS is `CERT_NONE`
   (encryption only; auth = signed nonce).
3. **Discrimination hardening.** Specify the read timeouts (30 s / 10 s) as MUST-close bounds,
   and RECOMMEND operators apply the same TTL-security/ACL protections used for the BGP peer
   to the shared port (since the NCFED parser is reachable by anyone who can reach the BGP port).
4. **Flag bits.** Define bit 0 = CONTINUATION; **"all other bits MUST be 0 on send and ignored
   on receipt"** (forward-compat).
5. **Max frame + reassembly bounds.** 64 KiB/frame is fixed; specify a **max reassembled
   message size** and DoS bounds on the continuation buffer (the code concatenates unbounded
   today — a real hardening item to add + spec).
6. **Delegation-loop prevention.** Add and specify a **delegation-depth counter / TTL** in the
   task envelope (not present today) — reviewers will demand it for agent-to-agent.
7. **TOFU recovery.** Specify token entropy (≥128 bits — currently ~144), token transport
   expectations, and the re-enrollment/quarantine recovery procedure if enrollment is
   suspected compromised.
8. **IANA.** Decide: request a registered service name/port for NCFED (RFC 6335) **or** state
   operators reuse a locally configured port; and whether the `N`+tag magic space
   (`NCFED`/`NCTUN`) warrants a registry if third parties extend it.

---

## Part 4 — Recommended path for NetClaw

1. **Draft now** as `draft-capobianco-ncfed-00`, **Experimental**, in kramdown-rfc, filling
   every section above from ground truth (this doc supplies all of it).
2. **Socialize at `agentproto`** (side meeting / list) rather than ISE-first — the forming WG
   is the correct venue and the ISE would defer to it under RFC 5742 anyway.
3. Position explicitly as **federation transport that carries A2A/MCP**, differentiated from
   `draft-yan-a2a-device-agent-applicability` (multi-operator + BGP identity + consent/TOFU +
   port multiplexing).
4. Harden items #5 and #6 (reassembly bound, delegation-depth) **in code** as part of the same
   spec, so the draft specifies what the implementation actually enforces.

---

*All wire facts cite the running implementation under
`mcp-servers/protocol-mcp/bgp/` as of feature 057 (branch merged to `main`). External items
sourced from authors.ietf.org, datatracker.ietf.org, rfc-editor.org, and the IETF 126
agentproto BoF announcement (2026).*
