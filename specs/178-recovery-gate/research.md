# Research and clarification disposition

## Evidence reuse

R03 proves actual four-device signed read/ACK and lost-ACK-result recovery. R04
proves same-identity member restart. R05 proves actual provider uncertainty/latch
recovery and client no-replay. R06 proves external caller-loss, cloud restart and
native browser/editor/Mobile recovery. Credit exact assertions/source/platform;
none proves every internal-member/revocation/cancel/endpoint combination.

## Demonstrated gaps

Two actual strict-TLS socket cases fail on merged R06: an awaited inbound handler
delivers after enrollment revocation, and an awaited outbound call accepts a
revoked member result. Persist removal before awaiting channel close; check state,
key/generation and applicable certificate validity after awaited boundaries.
Retain past effects. Strict dial failure reporting needs bounded observed causes.

VS Code origin-keyed refs and lack of endpoint update strand original operations.
HUD single-operation approval markers are memory-only: lost decision plus stale
review_pending after reload may permit retransmission. Default protected fetch
follows redirects. Reuse editor/combined durable send-marker patterns and existing
exact-ID recovery; add bounded nonce/parent recovery without secret transfer.

Mobile has a fixed WSS endpoint. Same trusted hostname/path/new port can use the
existing retained-key challenge while preserving installation/principal/HTTPS
origin, so references remain scoped. Changing trust identity is not migration.
ReconnectSupervisor can deliver onConnected after stop if a dial completes late.

## Decisions and alternatives

Use direct transport; optional ngrok unselected. Use fresh local isolated service
and native clients plus valid prior cloud/provider evidence; do not redeploy a
retained cloud merely to repeat successful reads. No new dependency or protocol.
Duplicate guarantees cover original task/protected operation submissions. Raw
synchronous calls are separate deliberate executions and unknown calls must not
be replayed. Do not falsely claim universal exactly-once RPC semantics.

Full SDD clarification review found functional scope, entities, user flow,
security, integrations, edge cases, tradeoffs and terminology clear from saved
handoff. Timing objectives deliberately await measurements and human review.
Concrete runtime/resource changes follow the existing review boundary. No new
architecture question is necessary. Three agents supplied private read-only
research-runtime.md/research-surfaces.md/research-mobile.md before implementation.
