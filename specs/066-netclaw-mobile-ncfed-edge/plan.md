# Implementation Plan: NCFED Edge Node Foundation + Border-to-Phone Push Channel

**Branch**: `066-netclaw-mobile-ncfed-edge` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/066-netclaw-mobile-ncfed-edge/spec.md`

## Summary

Let a phone join a risk as a new kind of iN2N member — an **edge node** (`node_type=edge`):
no agent runtime, no LLM, connects outbound over WebSocket-over-TLS instead of raw TCP,
authenticated asymmetrically (phone verifies the Border's existing feature-060
domain-verified certificate; Border TOFU-pins the phone's on-device-generated key via the
existing member enrollment token, delivered as a QR code — new). Once connected, the Border
can push explicitly-designated content (text/voice/image) to the phone, with platform push
notifications (APNs/FCM) covering backgrounded delivery, and a heartbeat/self-status
built-in method stands in for the `BASE_FLOOR` skill mandate a skill-less device can't
satisfy. Reuses `host_credential()`/`tls.server_context()` (060), the `member` table's
existing `pinned_key`/`key_fingerprint` columns, the already-bidirectional channel dispatch
(`channel.py`/`service.py`), and the proven exponential-backoff reconnect pattern already
running for agent members (`_in2n_member_dialer`) — ported to a Dart implementation for the
new edge client, not rebuilt in Python (it already works). Delivers the first slice of the
new `mobile/netclaw-mobile/` Flutter (iOS+Android) codebase: enrollment UX and a message
feed. No chat/command channel (067) or capture/biometrics (068) in this spec.

## Technical Context

**Language/Version**: Python 3.10+ (daemon + `bgp/federation/*`, matching 052–065); Dart 3.x / Flutter 3.x (new mobile client, `mobile/netclaw-mobile/`)
**Primary Dependencies**: Python: `websockets` (new, but already present transitively in this environment per Phase 0 research — declared explicitly in `protocol-mcp/requirements.txt`) for the Border-side WS listener; `qrcode` (new, pure-Python) for rendering the enrollment QR; existing `tls.py`/`FederationService.host_credential()` (060) reused as-is for the domain-verified SSL context; existing `manager.py`/`risk.py` enrollment-token and member-pinning code reused, extended with a `node_type` column. Dart: a WebSocket client package (`web_socket_channel` or equivalent), a QR-scanner package (`mobile_scanner` or equivalent), platform secure-storage packages (Keychain/Keystore-backed) for the enrollment key, and platform push packages (APNs/FCM) — exact package choices are an implementation detail of Phase 2 tasks, not fixed here.
**Storage**: Extends the existing SQLite `~/.openclaw/n2n/federation.db` `member` table with a `node_type` column (`agent` default | `service` | `edge`); reuses its existing `pinned_key`/`key_fingerprint` columns for the edge node's TOFU-pinned key — no new table. On the phone: platform secure hardware (iOS Keychain/Secure Enclave, Android Keystore) holds the enrollment private key; app-local storage (not federation.db) holds the message feed and connection state.
**Testing**: pytest under `tests/n2n/` (schema migration, QR-token issuance, domain-verified-cert reuse on the new listener, `node_type=edge` BASE_FLOOR-equivalent heartbeat enforcement, explicit-push-only message delivery, no-mirroring guarantee). Dart: `flutter test` (widget/unit tests for the WS client, reconnect backoff, enrollment flow) — full device/simulator testing happens on the operator's separate Mac for the iOS side; Android is testable in this Linux environment via the Android SDK's headless tooling where available.
**Target Platform**: Linux (systemd `--user` mesh/member services, consistent with the live deployment) for the daemon side; iOS 15+ and Android 8+ for the mobile client.
**Project Type**: Mobile + existing backend daemon (Option 3 shape) — a new Flutter client (`mobile/netclaw-mobile/`) talking to the existing NCFED daemon (`mcp-servers/protocol-mcp/`), which gains a new listener and schema column rather than a new service.
**Performance Goals**: A pushed message reaches a foregrounded, connected phone within the same order-of-latency as any other in-mesh delegated-task notification (seconds, not the push-notification-cold-start path); reconnect after a network blip completes within the existing backoff ceiling (60s cap, same as the proven agent-member pattern).
**Constraints**: No new secrets/plaintext keys (FR-004); Border never dials the edge node (FR-006); edge node gets zero BGP/eN2N topology visibility (FR-012); enrollment refuses outright on any certificate/domain mismatch (US1); explicit-push-only, no channel mirroring (FR-008).
**Scale/Scope**: Small mesh of mutually-known operators (NCFED applicability, unchanged); any number of enrolled edge nodes per risk (066's own assumption); this spec's mobile app surface is intentionally minimal — enrollment + a message feed, not the five-screen app (067/068 add the rest).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| IV. Immutable Audit Trail | PASS — enrollment, connection state changes, and pushed messages are recorded via the existing `Auditor`/GAIT path, consistent with every other iN2N member lifecycle event. |
| V. MCP-Native Integration | PASS — the operator/agent-facing surface for triggering a push (FR-008) is a new `n2n-mcp` tool, reachable identically from Slack/TUI/HUD since they all route through the same agent; the edge-node protocol extension itself is federation-protocol work (like 056/057/060/063), not a bespoke integration needing its own MCP wrapper. |
| VI. Multi-Vendor / Agent Neutrality | PASS — an edge node is protocol-generic (identity + capabilities + policy, no agent runtime required); nothing here is iOS- or Android-specific at the protocol layer. |
| IX. Security by Default | PASS — reuses feature 060's domain-verified cert (real public CA trust, not a fresh TOFU-on-first-contact) for phone→Border verification; reuses TOFU pinning for Border→phone verification, gated by single-use token possession, not a bare first connection; on-device secure hardware for the key; no blanket message mirroring. |
| XIII. Credential Safety | PASS — no new plaintext secrets; the phone's key is generated and held in platform secure hardware, never exported; push-notification credentials (APNs/FCM) follow the existing `.env`-configured third-party-credential pattern. |
| XV. Backwards Compatibility | PASS — `node_type` defaults to `agent` for every existing member row (migration is additive); the new WebSocket listener is a new, separate port/path — the existing raw-TCP iN2N listener and its agent members are completely untouched. |
| XVI. Spec-Driven Development | PASS — follows the clarified spec (7 clarifications across two sessions); no implementation without it. |
| XI. Full-Stack Artifact Coherence | PASS — plan's Project Structure below lists every touchpoint (schema, new listener, new MCP tool, install/catalog entries, README/SOUL/TOOLS/HUD, the new mobile codebase's own README) established in 065's remediation pattern; no orphan surface. |

**Complexity flag (justified, see below)**: Dart/Flutter is not in the constitution's existing approved stack (Python/Node.js/Bash). This is a deliberate, unavoidable addition — no existing NetClaw technology can produce a native iOS+Android app — explicitly chosen by the operator (a single Flutter codebase, not two native apps) and confirmed testable (the operator has a separate Mac, same git repo, for the iOS side).

No other violations.

## Project Structure

### Documentation (this feature)

```text
specs/066-netclaw-mobile-ncfed-edge/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (edge enrollment + push wire contract)
└── tasks.md             # Phase 2 (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/bgp/federation/
├── edge.py               # NEW: WebSocket listener for edge nodes (accept loop, TLS via
│                          #      host_credential()+tls.server_context()), QR enrollment
│                          #      token rendering, push-message dispatch to connected edges
├── manager.py             # member table gains `node_type` column (migration, default 'agent')
├── risk.py                 # consume_token() gains an explicit `node_type: str = "agent"`
│                           #  parameter, persisted in its INSERT/UPDATE member statements
│                           #  (confirmed transport-agnostic — no channel object dependency,
│                           #  research D9); BASE_FLOOR check gains an edge-node branch
│                           #  requiring the built-in heartbeat/self-status methods instead of
│                           #  n2n-member-runtime skill delivery
├── service.py               # + self.edge_channels: Dict[str, EdgeChannel]; + push_to_edge()
│                            #   mirroring delegate_to_member()'s call-out pattern
└── audit.py                 # unchanged — edge enrollment/push events use existing record()

mcp-servers/protocol-mcp/requirements.txt   # + websockets, qrcode (declared explicitly;
                                              #   already present transitively today)

mcp-servers/n2n-mcp/server.py    # + n2n_notify_phone(peer, text, kind) tool — the
                                   #   Slack/TUI/HUD/agent-reachable trigger for FR-008's
                                   #   explicit push (reachable identically from any channel,
                                   #   since they share one agent)

mobile/netclaw-mobile/            # NEW Flutter codebase (this spec's app-side deliverable)
├── pubspec.yaml
├── lib/
│   ├── ncfed/                    # protocol client: WS connection, reconnect backoff
│   │   │                         #   (ports the proven _in2n_member_dialer pattern to Dart),
│   │   │                         #   enrollment (QR scan, key generation in secure hardware,
│   │   │                         #   domain-cert verification via standard TLS), heartbeat
│   │   └── message_feed.dart     # local persistence for the pushed-message feed (FR-011)
│   └── screens/
│       ├── enrollment_screen.dart
│       └── feed_screen.dart
├── ios/                          # generated by `flutter create`; built/signed on the
│                                 #   operator's Mac
└── android/                     # generated by `flutter create`; buildable in this
                                  #   environment via the Android SDK

scripts/netclaw                  # risk-add / enrollment CLI gains a --edge flag rendering
                                   #  the QR code (terminal ASCII + optional PNG) instead of
                                   #  printing the plain-text token

workspace/skills/n2n-federation/SKILL.md   # + edge-node enrollment/push guidance (this spec's
                                             #   slice — chat/capture guidance is 067/068's)
README.md / SOUL.md / TOOLS.md / ui/netclaw-visual/   # capability description, capability
                                                        #   summary, infra reference, and a
                                                        #   HUD node/panel for connected edge
                                                        #   nodes — Constitution XI/X, same
                                                        #   pattern as 065's remediation

tests/n2n/
├── test_edge_enrollment.py       # QR/token issuance, domain-cert verification refusal on
│                                  #   mismatch, TOFU pinning, node_type migration
├── test_edge_push.py             # explicit-push-only delivery, no blanket mirroring,
│                                  #   text/voice/image content forms
└── test_edge_heartbeat.py        # BASE_FLOOR-equivalent enforcement for node_type='edge'
```

**Structure Decision**: A new `bgp/federation/edge.py` holds the WebSocket listener and
push-dispatch logic, reusing feature 060's `host_credential()`/`tls.server_context()` for TLS
and the existing `member` table (plus one migration column) for identity — no new store, no
new wire method family beyond what the already-bidirectional dispatch needs. The mobile app
is a genuinely new codebase (`mobile/netclaw-mobile/`, Flutter/Dart) since nothing like it
exists in this repo; it is scoped in this spec to enrollment + message feed only. Every
Full-Stack Artifact Coherence touchpoint (README/SOUL/TOOLS/HUD/install catalog) is tracked
above, matching the pattern 065's `/speckit.analyze` remediation established.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| New language/runtime (Dart/Flutter) outside the constitution's Python/Node.js/Bash stack | A real iOS+Android app cannot be produced by any existing NetClaw technology; the operator explicitly chose one Flutter codebase over two native apps | Two native apps (Swift/Kotlin) would double the surface for no benefit given the operator's own stated preference; a web-only PWA was rejected implicitly by the spec's requirements for platform biometrics/push/secure-hardware key storage (068/this spec), which a PWA cannot provide reliably across both platforms |
| New Python dependency: `websockets` | Raw asyncio TCP sockets don't speak the WebSocket handshake/framing FR-006 requires; a WS-capable listener needs a WS-aware library | Already present transitively in this environment (verified in Phase 0 research) — declaring it explicitly, rather than adding an undeclared transitive dependency, is the smaller change, not a new risk |
| New Python dependency: `qrcode` | No QR generator exists anywhere in this repo (verified in prior research) and US1 requires rendering one | Hand-rolling QR encoding is not a reasonable alternative to a small, pure-Python, dependency-free library |
| New Python dependencies: `httpx`, `h2` (T031, US3) | The disconnected-device push-notification fallback (FR-011) needs a real HTTPS client for FCM v1 and APNs; APNs mandates HTTP/2, which stdlib `http.client`/`urllib` cannot speak | `httpx` is already a dependency elsewhere in this repo (twilio-voice-mcp); `h2` is the minimal, standard pure-Python HTTP/2 protocol implementation `httpx` itself uses — no heavier alternative reduces scope |
| New Dart dependency: `firebase_messaging` (T003, US3) | Cross-platform (APNs+FCM) push registration on the device side; there is no single first-party Flutter API that speaks both platforms' push token/registration flows | Writing separate native APNs/FCM registration channels (like the Secure Enclave/Keystore plugins) would duplicate a well-established, widely-used package for no benefit |
