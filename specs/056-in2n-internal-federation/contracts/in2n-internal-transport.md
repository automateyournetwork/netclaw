# Contract: iN2N Internal Transport (member-initiated dial, NCFED framing reuse)

The Border↔Member channel. Reuses the **frozen NCFED wire framing** from spec 052 (`channel.py`) over a **member-initiated outbound connection**; adds an `in2n/hello` handshake variant. Hub-and-spoke — members connect only to the Border (research R2; FR-007/FR-007a).

## Framing — REUSED UNCHANGED (frozen)

Identical to eN2N (`contracts/n2n-wire-protocol.md`, spec 052):
```
[4-byte big-endian length][1-byte flags][UTF-8 JSON-RPC 2.0 payload]
flags bit0 = continuation (chunk of a larger message)
```
`encode_frames()` / decode, chunking > 64 KB, heartbeats (`NCFED_HEARTBEAT_INTERVAL` / `NCFED_HEARTBEAT_MISS_LIMIT`) all reused. No framing change (FR-018).

## Connection establishment

1. **Member dials outbound** to `risk.border_endpoint` (host:port). Endpoint may be loopback (co-located), a private-network address, or an overlay/VPN/tunnel address (distributed). The member opens **no inbound port**.
2. **Channel security**: TLS using the member's runtime-generated **self-signed key**; the Border presents its own self-signed key. The Border authenticates the member by comparing the presented key against the **pinned** key (enrollment contract §3). The member authenticates the Border by pinning the Border key it was given at provisioning (`border_endpoint` + Border key fingerprint).
3. **Discrimination**: on the Border's listener, a connection is classified by its first bytes — existing eN2N/BGP/tunnel discrimination is unchanged; iN2N connections are identified by the `in2n/hello`|`in2n/enroll` first method after the secure channel is up. (If iN2N uses a distinct listener port `N2N_IN2N_PORT`, discrimination is by port; see research R2 — either is acceptable, both keep eN2N framing frozen.)

## Handshake: `in2n/hello` (variant of eN2N `n2n/hello`)

Unlike eN2N's `n2n/hello` (which carries `as`/`router_id` BGP identity + capability descriptor), `in2n/hello` carries the **risk-local member id + pinned-key proof** (no AS, members aren't mesh peers):
```json
{ "jsonrpc":"2.0","id":1,"method":"in2n/hello",
  "params": {
    "member_id": "johns-risk/cml",
    "key_fingerprint": "sha256:…",
    "capabilities": { "protocol_version": "054.1", "async_tasks": true }
  } }
```
Border response includes the risk context and confirms trust:
```json
{ "jsonrpc":"2.0","id":1,"result":{ "risk":"johns-risk","trusted":true,"member_state":"active" } }
```
The eN2N `n2n/hello` path is **untouched**; `in2n/hello` is a sibling handler.

## Post-handshake dispatch

Once `active`, the same JSON-RPC method set eN2N uses is available over the internal channel, gated to the member's scope:
- `n2n/inventory/*` — member advertises its (scoped) capabilities to the Border.
- `n2n/tasks/submit|status|result|cancel` — internal delegation (reused 053 async lifecycle; see routing contract).
- Heartbeats keep the channel alive; a miss marks the member `unreachable` and increments failure count.

## Reconnect / self-heal (reused 053 pattern)

- **Member side**: a dial supervisor re-dials `border_endpoint` with bounded backoff (5s→60s) if the channel drops — the same supervisor logic as eN2N's reconnect (spec 053), pointed at the Border.
- **Border side**: `on_close` deregisters the member channel (no zombies); the member re-dials and re-authenticates on its pinned key. No operator action needed for a normal restart.
- Distributed members surviving a transient network partition rejoin automatically when the private transport recovers.

## Invariants (test assertions)

- A member opens zero inbound listening ports (SC-011).
- Framing bytes on an iN2N channel are byte-identical to eN2N framing (frozen-core guard).
- Members cannot address each other — only the Border is dialable in a risk (hub-and-spoke, FR-007a).
- A dropped internal channel re-establishes from the member side automatically (bounded backoff), result-bearing tasks survive per 053 persistence.
- eN2N `n2n/hello` and channel behavior are unchanged by the presence of `in2n/hello` (`test_en2n_regression.py`).
