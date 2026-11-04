# Protected device operations v1

Authenticated enrollment/hello returns `border.installation_id` and `border.capabilities.protected_operations`:

`{schema:1,installation_id,origin,methods:["n2n/edge/operations/catalog","n2n/edge/operations/prepare","n2n/edge/operations/status","n2n/edge/operations/decision","n2n/edge/operations/reconcile"],principal:{issuer:"device-key",subject:<UUID>,display_name:<bounded label>,roles:["device-operator"]}}`.

Origin is exact trusted HTTPS origin associated with this installation. Descriptor only appears on a protected Border and derives principal from authenticated member/key/enrollment state. Client validates schema/installation/origin/method list/principal role before showing operations. Protected legacy text/voice/attachment/capture/watch/background capabilities remain unavailable; calls fail closed.

Each RPC uses the existing protected HTTPS field contract plus `installation_id`; only transport authentication differs. `auth_context` and caller-supplied principal are refused. Backend constructs an unforgeable internal device authority and invokes the existing catalog/prepare/status/decision/reconcile implementation. No revoke or general admin route is advertised by this feature.

Existing review digests, revisions, signatures, nonce retention, approval consumption and result delivery ACK stay authoritative. Every device request/lookup/reconcile is scoped to installation and authenticated device principal. Existing owner/open-lab history is unchanged; widening principal validation must not widen device record visibility.

Mobile reuses full immutable review/decision/result UI through authenticated WSS transport, with device storage namespace separate from historical owner screen. Persist operation nonce/reference and decision intent before sends. Lost prepare/decision retains uncertainty; explicit status/reconcile never repeats prepare or approval. Startup/background recovery uses same references only. Complete signed result and durable ACK must be shown; unknown remains unknown.
