# Phase 0 Research: NCFED Edge Node Foundation + Border-to-Phone Push Channel

No `NEEDS CLARIFICATION` markers remain in the spec (resolved across two `/speckit.clarify`
sessions). This document records the implementation-approach decisions needed to turn the
clarified spec into a design, each grounded in what already exists in the codebase.

## D1: Where does the domain-verified certificate (for phone→Border verification) come from?

- **Decision**: Reuse `FederationService.host_credential()` (`service.py:382-406`) +
  `tls.server_context()` (`tls.py:46-60`) exactly as they exist today. `host_credential()`
  already returns the ACME/domain-verified cert (`N2N_CLAW_DOMAIN` + `keys/acme/...`) when
  configured, falling back to the self-signed host cert otherwise — the new edge WebSocket
  listener calls the same two functions the existing `_secure_accept` (`service.py:445-452`)
  already calls for eN2N TLS.
- **Rationale**: This is the exact plumbing feature 060 built; both functions are already
  decoupled from any specific listener (they take/return PEM material, not a bound socket),
  so a second listener consuming the same credential is a direct reuse, not new cert logic.
- **Correction to an earlier assumption**: `internal_channel.build_ssl_contexts`
  (`internal_channel.py:114-125`), which iN2N members currently use, does *not* use the
  domain-verified cert — it's a separate, older code path for the risk-CA/self-signed model.
  The edge listener must call `host_credential()`/`tls.server_context()` directly, not go
  through `internal_channel`.

## D2: What WebSocket library does the Border-side listener use?

- **Decision**: `websockets` (declared explicitly in `protocol-mcp/requirements.txt`).
- **Rationale**: Verified in this environment: `websockets`, `aiohttp`, `starlette`, and
  `uvicorn` are all importable today despite none being declared in `protocol-mcp`'s own
  requirements (likely pulled in transitively by another already-installed tool). `websockets`
  is the minimal choice — a single-purpose async WS library, not a full ASGI framework —
  matching this repo's general preference for the smallest dependency that does the job
  (e.g., `fastmcp`/`mcp` over a heavier framework elsewhere in the codebase).
- **Alternatives considered**: `aiohttp`/`starlette`+`uvicorn` were rejected as pulling in an
  entire HTTP framework for a single WS accept loop the existing `asyncio`-based daemon
  already knows how to structure (mirroring `accept_internal`'s shape, `service.py:792-803`).

## D3: How does a member row become an edge node?

- **Decision**: Add a `node_type` column to the existing `member` table (`manager.py:150-164`)
  — `agent` (default, matches every existing row), `service`, or `edge` — via an additive
  migration. Reuse the table's existing `pinned_key`/`key_fingerprint` columns as-is for the
  edge node's TOFU-pinned key; no new column is needed for key storage.
- **Rationale**: The `member` table already has exactly the columns an edge node needs
  (`pinned_key`, `key_fingerprint`, `state`, `health`); the only real gap is a way to say
  "this member has no agent runtime," which `node_type` closes directly.

## D4: How is member-side reconnect supervision actually built — and what's genuinely new?

- **Decision**: Port the *pattern* already proven for agent members
  (`_in2n_member_dialer`, `bgp-daemon-v2.py:824-847` — a permanent loop, exponential backoff
  5s→60s cap, automatic redial on drop) into a Dart implementation inside the mobile app's
  own WebSocket client. No new Python infrastructure is built.
- **Correction to the clarification session's premise**: Investigation during specification
  reported member-side reconnect supervision as "thinner than assumed... not clearly present
  for iN2N members," leading to a clarification answer to "build proper member-side reconnect
  supervision as part of this feature." Deeper research during planning found this premise
  was wrong: `_in2n_member_dialer` already exists, is a permanent loop with real exponential
  backoff, and already runs for every agent member today. The clarification's *resolution*
  (edge nodes need robust, tested reconnect behavior, not a bare client-side afterthought)
  remains correct and drives this spec's requirements (FR-007/SC-003) — what changes is the
  *work*: there is no missing Python capability to build; the work is a Dart port of an
  already-working pattern, because Dart and Python code cannot literally be shared. This is
  recorded here so a future reader doesn't go looking for "the general iN2N improvement" in
  `service.py` and wonder why it's missing — it isn't missing, it's the existing dialer, and
  it was never broken.

## D5: How does an edge node satisfy `BASE_FLOOR` without running skills?

- **Decision**: `risk.py`'s `BASE_FLOOR` enforcement (`risk.py:41-46`) gains a `node_type`
  branch: for `edge`, the mandate is satisfied by the edge node responding to two new
  built-in NCFED methods (heartbeat and self-status) rather than by having delivered the
  `n2n-member-runtime` skill and its `member_heartbeat`/`member_report_audit` tools. The
  Border's health tracking (the existing `health` column) is updated from these same
  responses, not from skill-delivered tool calls.
- **Rationale**: `BASE_FLOOR` exists to keep every member trustable/monitorable — the
  mechanism (skill-delivered tools) is what a skill-less device can't do; the *guarantee*
  (the Border can tell if a member is healthy) is preserved by requiring the equivalent
  signal through a different, protocol-native mechanism, exactly as the spec's first
  clarification resolved.

## D6: How is the enrollment QR code generated and what does it encode?

- **Decision**: A new `qrcode` (pure-Python) dependency renders a QR encoding a small JSON
  payload: `{border_host, border_port, claw_domain, enrollment_token}` — reusing the existing
  `RiskManager.issue_token()` (`risk.py:355-370`) for the token itself. `scripts/netclaw`'s
  existing enrollment CLI (`risk_add`, currently prints the token as plain text) gains a
  `--edge` flag that renders this as a QR code (terminal ASCII art, matching how CLI tools
  commonly render QR codes for scanning) instead of a bare token string.
- **Rationale**: No QR generator exists anywhere in this repo today (confirmed by exhaustive
  search during specification) — this is genuinely new, small, and isolated to the
  enrollment-issuing side; the *token* itself is unchanged, only its presentation is new.

## D7: How does the phone verify the Border's certificate — does it need custom TLS code?

- **Decision**: No custom certificate-verification code is needed on the phone. Since feature
  060's domain-verified certificate is a real, publicly-trusted certificate (issued via ACME),
  any standard TLS client — including Dart's built-in `WebSocket`/`HttpClient` — already
  performs standard hostname verification against the public CA trust store automatically
  when connecting to `wss://<claw-domain>:<port>`. The QR payload's `claw_domain` field is
  used only to confirm the connection target matches what the operator intended (comparing
  the domain the app is about to connect to against the domain encoded in the QR, before
  dialing) — the actual cryptographic verification is standard TLS, not bespoke logic.
- **Rationale**: This dramatically simplifies FR-003's "the edge node MUST verify the Border's
  public, domain-verified certificate" — it's not a new crypto implementation, it's "connect
  over standard TLS to the right hostname," which every mobile TLS stack already does
  correctly by default.

## D9: Are `consume_token`/`verify_possession`/`_pin_key_file` actually transport-agnostic? — CONFIRMED

- **Decision**: Yes, fully confirmed by reading the real signatures (resolved during
  `/speckit.analyze` remediation, finding U1). `verify_possession(cert_pem, nonce, signature,
  binding=b"")` (`risk.py:222-223`) is a `@staticmethod` over plain PEM/bytes — no channel
  object. `consume_token(raw_token, member_id, cert_pem, scope=None, runtime_kind="process",
  display_name=None, transport_binding="loopback")` (`risk.py:377-380`) likewise takes only
  strings/bytes and does the actual `INSERT INTO member` / `UPDATE member` (`risk.py:405-412`)
  — no `FederationChannel` dependency anywhere. `EdgeChannel` can call all three directly,
  exactly as planned, with zero adaptation needed.
- **Correction to I1 (`/speckit.analyze` finding)**: the plan's original claim that
  `RiskManager.add_member()` gains a `node_type='edge'` path was based on a mistaken
  attribution. `add_member()` (Border-side, mints the token when an operator runs `netclaw
  risk add`) never touches the `member` row directly. `consume_token()` is the function that
  actually creates/updates that row — it is the one that needs a new `node_type: str =
  "agent"` parameter, added to both its `INSERT INTO member` and `UPDATE member` statements
  (`risk.py:405-412`), not `add_member()`. `edge.py`'s WS enrollment handler calls
  `consume_token(..., node_type="edge")` directly; no other function needs to change.

## D8: How does the Border push a message to a connected edge node?

- **Decision**: `FederationService` gains `self.edge_channels: Dict[str, EdgeChannel]`
  (mirroring the existing `self.member_channels`) and a `push_to_edge(member_id, content)`
  method that calls `ch.call("n2n/edge/message", {...})` on the connected edge node's
  channel — directly mirroring how `delegate_to_member()` (`service.py:1081-1135`) already
  calls out to a connected agent member. No new method family or dispatch model is needed;
  this is the same bidirectional call-out pattern already proven for task delegation.
- **Trigger surface**: A new `n2n_notify_phone(peer, text, kind)` tool in `n2n-mcp/server.py`
  is the operator/agent-facing entry point (FR-008) — reachable identically whether the
  operator is in Slack, the TUI, or the HUD, since all three route through the same
  underlying agent and its MCP tools; no per-channel-specific code is needed.
