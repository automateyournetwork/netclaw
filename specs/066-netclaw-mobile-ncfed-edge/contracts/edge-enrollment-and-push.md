# Contract: Edge Node Enrollment (QR) + Border-to-Phone Push

Two wire surfaces, both reusing existing NCFED primitives: enrollment reuses the existing
member-enrollment protocol over a new transport binding; push is a new, dedicated method
addressed via the already-bidirectional channel dispatch (no new method family).

## 1. Enrollment QR payload (presentation layer, not itself a wire method)

Rendered by the enrollment CLI (`scripts/netclaw ... --edge`), scanned by the app:

```json
{
  "border_host": "netclaw.automateyournetwork.ca",
  "border_port": 8443,
  "claw_domain": "netclaw.automateyournetwork.ca",
  "enrollment_token": "in2n_9f8c3a...redacted"
}
```

**Rules**
- `claw_domain` is compared by the app against the TLS-certified hostname of the connection
  it is about to trust — a mismatch aborts before any enrollment attempt (D7).
- `enrollment_token` is single-use — the existing `enrollment_token` table's semantics apply
  unchanged; a second enrollment attempt with the same token is refused exactly as it is for
  any other member type today.

## 2. Enrollment handshake (over the new WebSocket transport, existing method names)

Identical wire methods to today's iN2N member enrollment (`in2n/enroll` and the existing
possession-proof exchange) — only the *transport* is new (WebSocket-over-TLS instead of raw
TCP-over-optional-TLS). The request/response shapes are unchanged from the existing
enrollment protocol; this contract does not redefine them.

**New field on success**: the Border's `member` row for this enrollment is created with
`node_type: "edge"` (vs. the existing default `"agent"`) — this is a server-side effect, not
a new wire field the app needs to send; `node_type` is inferred by the Border from which
listener (raw-TCP agent listener vs. new WS edge listener) the connection arrived on.

**Transport-level addendum (new, WS-specific)**: raw-TCP iN2N members receive their
Border-issued possession-proof nonce as bytes preceding the JSON-RPC channel
(`IN2N_MAGIC` + 32-byte nonce). A WebSocket connection has no such pre-protocol byte
channel, so immediately after accepting the connection the Border sends one JSON-RPC
*notification* carrying the same nonce:

```json
{ "jsonrpc": "2.0", "method": "n2n/edge/challenge", "params": { "nonce": "<64-hex-chars>" } }
```

The app signs this nonce (hex-decoded) exactly as the existing possession-proof signature
already requires, and includes it in its `in2n/enroll` / `in2n/hello` request. This is a
transport-preamble equivalent, not a new trust mechanism.

## 3. `n2n/edge/message` — Border pushes content to a connected edge node

**Request** (Border → phone, over the existing connection — the Border calls `.call()` on
`self.edge_channels[member_id]`, mirroring `delegate_to_member()`'s existing call-out shape):

```json
{
  "content_type": "text",
  "content": "Toronto branch WAN outage detected — 14 locations affected.",
  "designated_by": "agent",
  "pushed_at": "2026-07-22T21:40:00Z"
}
```

`content_type` is one of `"text"`, `"voice"`, `"image"`. For `voice`/`image`, `content` is the
media payload (base64 or binary, subject to the same chunked framing any large NCFED message
already uses — no new size policy here; a photo/short clip fits comfortably, this method
carries the same kind of content 067/068's attachments do, just Border-to-phone instead of
phone-to-Border).

**Result** (phone → Border, acknowledgment):

```json
{ "received": true }
```

**Rules**
- Sent only for content the Border has explicitly designated for phone delivery (FR-008) —
  never a blanket mirror of channel traffic, and never a request for the phone to create new
  content (that boundary is enforced by this method's shape: it carries content *to* render,
  not a capability to invoke — Border-requested capture is spec 068's `n2n/edge/capture`,
  a different method, not this one).
- If the edge node is not currently connected, the Border does not attempt this call — it
  routes to the platform push-notification path (FR-011) instead.

## 4. Built-in heartbeat / self-status (BASE_FLOOR equivalent, D5)

Two new built-in methods every edge client implements natively (no skill delivery):

- `n2n/edge/heartbeat` — Border-initiated, periodic; phone responds with a trivial
  acknowledgment. Updates the `member` row's `health` column, exactly as
  `member_heartbeat` (the skill-delivered equivalent for agent members) already does.
- `n2n/edge/self_status` — Border-initiated, on demand; phone responds with basic
  connection/battery/app-version info (the edge-node analogue of `member_report_audit`,
  scoped to what's meaningful for a device rather than a process).

## 5. Operator/agent-facing trigger: `n2n_notify_phone` (n2n-mcp tool)

```
n2n_notify_phone(peer: str, content: str, kind: str = "text") -> str
```

Reachable identically from Slack, the TUI, the HUD, or the agent's own reasoning (they share
one agent and its MCP tools) — internally calls `POST /n2n/edge/push` on the daemon, which
calls `FederationService.push_to_edge(peer, {content_type: kind, content, ...})` (D8),
resulting in the `n2n/edge/message` call above if the edge node is connected, or a
push-notification fallback if not.
