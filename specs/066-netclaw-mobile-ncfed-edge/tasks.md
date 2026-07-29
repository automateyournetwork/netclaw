# Tasks: NCFED Edge Node Foundation + Border-to-Phone Push Channel

**Input**: Design documents from `/specs/066-netclaw-mobile-ncfed-edge/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the spec's Success Criteria and quickstart.md call for pytest + `flutter
test` coverage, and the repo is test-driven (`tests/n2n/`).

**Organization**: By user story (US1/US2/US3, all Priority P1 — this spec is the tight
foundational slice of the NetClaw Mobile initiative; 067/068 add P2 depth on top).

> This revision incorporates `/speckit.analyze` remediation (2026-07-22): a corrected
> attribution for where `node_type` is actually set (`consume_token()`, not `add_member()` —
> confirmed transport-agnostic, no channel dependency), plus five new tests closing coverage
> gaps (plain-text-enrollment regression, revocation blocking delivery, edge-channel method
> scoping, key-non-exportability, and the BASE_FLOOR positive case) and a missing
> `.env.example` entry. Task IDs were renumbered; there is no prior implementation to
> reconcile against.

## Path Conventions

Single project spanning two runtimes. Federation daemon: `mcp-servers/protocol-mcp/bgp/federation/`
and `mcp-servers/protocol-mcp/bgp-daemon-v2.py`. Operator/agent tools: `mcp-servers/n2n-mcp/server.py`.
New mobile codebase: `mobile/netclaw-mobile/` (Flutter/Dart). Tests: `tests/n2n/` (Python),
`mobile/netclaw-mobile/test/` (Dart, via `flutter test`). Skill docs: `workspace/skills/`.

---

## Phase 1: Setup

- [X] T001 Scaffold the Flutter project under `mobile/netclaw-mobile/` (run `flutter create .` if `pubspec.yaml`/`lib/` don't already exist beyond the placeholder `README.md`; confirm `flutter --version` and that an Android build target is available in this Linux environment — note the iOS target requires the operator's separate Mac, per plan.md).
- [X] T002 [P] Add `websockets` and `qrcode` to `mcp-servers/protocol-mcp/requirements.txt`; `pip install -r mcp-servers/protocol-mcp/requirements.txt` and confirm both import (`python3 -c "import websockets, qrcode"`).
- [X] T003 [P] Add Dart dependencies to `mobile/netclaw-mobile/pubspec.yaml`: a WebSocket client (e.g. `web_socket_channel`), a QR scanner (e.g. `mobile_scanner`), platform secure storage (e.g. `flutter_secure_storage`, backed by iOS Keychain/Secure Enclave and Android Keystore), and a cross-platform push-notification package (APNs + FCM); run `flutter pub get` and confirm it resolves.
- [X] T004 [P] Create empty test modules `tests/n2n/test_edge_enrollment.py`, `tests/n2n/test_edge_push.py`, and `tests/n2n/test_edge_heartbeat.py`, each importing the shared `conftest.py` manager fixture, so later test tasks just add cases.

**Checkpoint**: Both toolchains are ready; nothing yet depends on implementation.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Schema, the actual member-creation change, the WS listener skeleton, and the BASE_FLOOR-equivalent heartbeat mechanism every user story below depends on.

- [X] T005 Add `("member", "node_type", "TEXT NOT NULL DEFAULT 'agent'")` to the existing additive-migration list in `mcp-servers/protocol-mcp/bgp/federation/manager.py` (~line 240, alongside the feature-060 column additions using the same `ALTER TABLE ... except sqlite3.OperationalError: pass` pattern already established there) — every existing member row defaults to `agent`, preserving current behavior exactly.
- [X] T006 Extend `RiskManager.consume_token()` in `mcp-servers/protocol-mcp/bgp/federation/risk.py` (`risk.py:377-424`) with a new `node_type: str = "agent"` parameter, adding it to both the `INSERT INTO member` and `UPDATE member` statements inside — this is the function that actually creates/updates the member row on successful enrollment (confirmed transport-agnostic: it takes only `raw_token`/`member_id`/`cert_pem` strings and bytes, no channel object — research D9). Do NOT modify `add_member()`, which only mints the token and never touches the member row.
- [X] T007 [P] Create `mcp-servers/protocol-mcp/bgp/federation/edge.py` with an `EdgeChannel` class wrapping a `websockets` connection, exposing the same `.call()` / handler-dispatch shape `FederationChannel` (`channel.py`) already has, so it plugs into the existing bidirectional call-out pattern (`delegate_to_member`'s shape) without any special-casing at call sites. Its handler map MUST contain only edge-specific methods (enrollment, heartbeat, self_status, message) — no BGP, eN2N, or inventory methods (FR-012).
- [X] T008 [P] Add `self.edge_channels: Dict[str, EdgeChannel] = {}` to `FederationService.__init__` in `mcp-servers/protocol-mcp/bgp/federation/service.py`, alongside the existing `self.member_channels`.
- [X] T009 Implement the WS accept loop in `edge.py`: bind a new port (`N2N_EDGE_WS_PORT` env var — add it to `.env.example` alongside the other N2N_* vars in this same task), obtain the domain-verified SSL context via `fed.host_credential()` + `tls.server_context()` (research D1 — do NOT use `internal_channel.build_ssl_contexts`, which is the older risk-CA path and does not carry the domain-verified cert), wrap accepted connections in `EdgeChannel`, and route the initial handshake into the existing `in2n/enroll` protocol, calling `RiskManager.verify_possession()` and then `consume_token(..., node_type="edge")` (T006) on success.
- [X] T010 Add a `node_type` branch to `BASE_FLOOR` enforcement in `mcp-servers/protocol-mcp/bgp/federation/risk.py` (~line 41-46): for `node_type='edge'` members, the mandate is satisfied by responding to the two built-in methods added in T011, not by having delivered the `n2n-member-runtime` skill.
- [X] T011 [P] Implement server-side `n2n/edge/heartbeat` (periodic, Border-initiated, trivial ack) and `n2n/edge/self_status` (on-demand) handlers in `edge.py`, updating the `member.health` column exactly as the skill-delivered equivalent (`member_heartbeat`) already does for agent members.

**Checkpoint**: Schema, WS listener, enrollment plumbing, and heartbeat all exist and are unit-testable without a real phone.

---

## Phase 3: User Story 1 — Enroll a phone into a risk by scanning a QR code (Priority: P1)

**Goal**: An operator can enroll a phone by scanning a QR code the Border displays, with the phone verifying the Border's real certificate and the Border TOFU-pinning the phone's key.
**Independent test**: Generate a QR from the Border, scan it from the app, confirm the phone appears in the member list as `node_type='edge'` with a pinned key; confirm a mismatched-domain QR aborts before any token exchange.

- [X] T012 [US1] Extend `scripts/netclaw`'s enrollment command with a `--edge` flag that renders the QR payload (`{border_host, border_port, claw_domain, enrollment_token}`, from `RiskManager.issue_token()`'s existing token) as terminal ASCII art using the new `qrcode` dependency, instead of printing the plain-text token.
- [X] T013 [US1] Implement the Dart enrollment client in `mobile/netclaw-mobile/lib/ncfed/`: scan the QR (`mobile_scanner`) → parse the payload → dial `wss://<border_host>:<border_port>` → verify the TLS-certified hostname matches `claw_domain` *before* proceeding, aborting hard on any mismatch (research D7 — this is standard TLS verification, not custom crypto) → generate a keypair in platform secure storage (using the secure-storage package's key-generation API so raw key material is never handed back to app code) → complete the existing possession-proof handshake, presenting `enrollment_token`.
- [X] T014 [US1] Implement `mobile/netclaw-mobile/lib/screens/enrollment_screen.dart`: "Scan Border QR Code" UI, explicit error states for domain-mismatch/expired-token/already-used-token, and on success navigate to a topology view showing the Border and existing members with the phone marked as the current device.
- [X] T015 [P] [US1] Test in `tests/n2n/test_edge_enrollment.py`: enrollment via a QR-delivered token creates a `member` row with `node_type='edge'` and `pinned_key`/`key_fingerprint` set; a second enrollment attempt with the same token fails (single-use, reusing existing `consume_token` semantics).
- [X] T016 [P] [US1] Test in `tests/n2n/test_edge_enrollment.py`: an enrollment attempt against a Border whose certified domain doesn't match the expected `claw_domain` never reaches the token-exchange step (assert zero calls to `consume_token`).
- [X] T017 [P] [US1] `flutter test` widget/unit test for the enrollment flow in `mobile/netclaw-mobile/test/`: a mismatched-domain QR aborts before dialing the token exchange; a successful scan drives the app to the topology view.
- [X] T018 [P] [US1] Regression test in `tests/n2n/test_edge_enrollment.py`: a plain-text (non-QR, non-`--edge`) enrollment still succeeds and produces a `member` row with `node_type='agent'`, unaffected by the T005 migration and T006/T012 changes (closes `/speckit.analyze` finding G1 — FR-002's backward-compatibility clause).
- [X] T019 [P] [US1] Test in `tests/n2n/test_edge_enrollment.py`: after enrolling an edge member, removing/quarantining it via the existing member-removal mechanism (unchanged) causes a subsequent `push_to_edge` call and heartbeat check against it to both fail cleanly — no further delivery is possible post-revocation (closes G2 — SC-005/FR-013).
- [X] T020 [P] [US1] Test in `tests/n2n/test_edge_enrollment.py`: `EdgeChannel`'s handler map (T007) contains only `n2n/edge/*` methods (enroll, heartbeat, self_status, message) and none of the BGP/eN2N/inventory method names the agent-member channel exposes (closes G3 — FR-012).
- [X] T021 [P] [US1] `flutter test` in `mobile/netclaw-mobile/test/`: the enrollment key, once generated via the secure-storage package (T013), cannot be read back as raw bytes through any app-facing API — only sign/use operations are exposed (closes G4's key-non-exportability half — FR-004).

**Checkpoint**: US1 independently demonstrable — a real phone can enroll end to end, revocation genuinely blocks it afterward, and the edge channel is provably scoped to only what it should expose.

---

## Phase 4: User Story 2 — The Border pushes an important message to the phone (Priority: P1)

**Goal**: An operator or the agent can explicitly push a text/voice/image message to a connected phone, and only explicitly-designated content ever arrives — never a blanket mirror.
**Independent test**: With an enrolled, connected phone, call `n2n_notify_phone` and confirm the message reaches the phone's feed; send an ordinary, non-designated message through the same channel and confirm it does not.

- [X] T022 [US2] Implement `push_to_edge(member_id, content)` in `service.py`, mirroring `delegate_to_member()`'s existing call-out shape — calls `n2n/edge/message` on the connected `EdgeChannel` from `self.edge_channels`.
- [X] T023 [US2] Implement the `n2n/edge/message` server-side registration in `edge.py` (added to the edge channel's handler map) and the Dart client-side handler that appends the received message into the local feed store (`mobile/netclaw-mobile/lib/ncfed/message_feed.dart`).
- [X] T024 [US2] Add `n2n_notify_phone(peer: str, content: str, kind: str = "text") -> str` MCP tool in `mcp-servers/n2n-mcp/server.py`, calling a new `POST /n2n/edge/push` daemon route; docstring notes it's reachable identically from Slack, TUI, HUD, or agent reasoning, since they share one agent.
- [X] T025 [US2] Add `POST /n2n/edge/push` route in `mcp-servers/protocol-mcp/bgp-daemon-v2.py`, validating `content_type` (`text`|`voice`|`image`) and calling `fed.push_to_edge(...)`.
- [X] T026 [US2] Implement `mobile/netclaw-mobile/lib/screens/feed_screen.dart`: renders text/voice/image message items from the local feed store, in chronological order.
- [X] T027 [P] [US2] Test in `tests/n2n/test_edge_push.py`: a message pushed via `push_to_edge` reaches a mocked connected `EdgeChannel` via `n2n/edge/message`; assert no other code path ever triggers that method (explicit-push-only, no mirroring, FR-008).
- [X] T028 [P] [US2] Test in `tests/n2n/test_edge_push.py`: all three content types (text/voice/image) round-trip through `push_to_edge`/`n2n/edge/message` unmodified.
- [X] T029 [P] [US2] `flutter test` for `message_feed.dart`: appended messages persist across a simulated app restart (local storage reload).

**Checkpoint**: US2 independently demonstrable — the Border can push, the phone renders it, and only explicitly-designated content ever arrives.

---

## Phase 5: User Story 3 — Reach the operator even when the app is backgrounded (Priority: P1)

**Goal**: A pushed message reaches the operator via platform push notification when the app is backgrounded, and a dropped connection recovers automatically with bounded backoff.
**Independent test**: Background the app, push a message, confirm a platform notification arrives and opens to it; toggle airplane mode and confirm automatic reconnection with increasing, capped backoff.

- [X] T030 [US3] Implement the Dart reconnect supervisor in `mobile/netclaw-mobile/lib/ncfed/`, porting `_in2n_member_dialer`'s exact backoff bounds (5s→60s exponential, permanent retry loop, `bgp-daemon-v2.py:824-847`, research D4) — triggered on any WebSocket close/error, cleanly cancelled on explicit disconnect (e.g. unenrollment).
- [X] T031 [US3] Wire platform push notifications: register for APNs (iOS) and FCM (Android) in the Dart app, and extend `push_to_edge()` (T022) to fall back to sending a push notification when the target `EdgeChannel` is not in `self.edge_channels`, using `.env`-configured credentials (document `APNS_*`/`FCM_*` vars in `.env.example`, following this repo's existing third-party-credential pattern).
- [X] T032 [US3] Implement notification-tap deep-linking in the Dart app: tapping a delivered push notification opens the app directly to the corresponding message in the feed.
- [X] T033 [P] [US3] Test in `tests/n2n/test_edge_push.py`: `push_to_edge()` against a `member_id` with no entry in `edge_channels` calls the push-notification path instead of attempting `n2n/edge/message`, and returns/raises cleanly rather than hanging.
- [X] T034 [P] [US3] `flutter test` for the reconnect supervisor: simulated repeated connect/disconnect cycles show increasing backoff capped at 60s, and a successful reconnect resets the backoff counter to its initial value.
- [X] T035 [P] [US3] Test in `tests/n2n/test_edge_heartbeat.py`: a disconnected edge node's `member.health` reflects unhealthy/disconnected within the expected heartbeat-miss window.
- [X] T036 [P] [US3] Test in `tests/n2n/test_edge_heartbeat.py`: a connected, heartbeating `node_type='edge'` member with zero skills delivered passes `BASE_FLOOR` enforcement (T010) — the positive case, complementing T035's negative case (closes G4's other half — FR-005/SC-006).

**Checkpoint**: US3 independently demonstrable — backgrounded delivery and resilient reconnect both hold, and BASE_FLOOR's guarantee is proven to hold both ways (healthy and unhealthy).

---

## Phase 6: Polish & Cross-Cutting

- [X] T037 [P] Update `workspace/skills/n2n-federation/SKILL.md` with edge-node enrollment/push guidance — this spec's slice only (note that chat/command guidance is 067's and capture/biometrics is 068's).
- [X] T038 [P] Update `README.md` with the edge-node/NetClaw Mobile capability description and tool/count updates, following the same remediation pattern feature 065 established.
- [X] T039 [P] Update `SOUL.md` with a capability summary for the edge-node push channel.
- [X] T040 [P] Update `TOOLS.md` with the `n2n_notify_phone` tool reference and the new env vars (`N2N_EDGE_WS_PORT`, push-notification credentials).
- [X] T041 [P] Add a HUD node/panel to `ui/netclaw-visual/` showing connected edge nodes and recent pushed messages, following the same pattern feature 065's HUD remediation established.
- [X] T042 [P] Write `mobile/netclaw-mobile/README.md` documenting the app's structure, how to run it against a local Border, and that the iOS build/sign step explicitly requires the operator's separate Mac.
- [X] T043 Run the full n2n suite (`python3 -m pytest tests/n2n -q`) and confirm zero regressions; map passing tests to SC-001…SC-006.
- [X] T044 [P] Run `flutter analyze` and `flutter test` in `mobile/netclaw-mobile/`; confirm a clean Android build in this environment; explicitly note the iOS build/sign step is deferred to the operator's Mac.
- [ ] T045 [P] Run the `quickstart.md` manual walkthrough end-to-end (steps 1–10) against a live Border and a real or emulated device, and record the result.
      - **2026-07-25 (iOS, spec `071-ios-mobile-port`)**: attempted from the iOS side, still blocked — the available Mac has no Xcode.app or Flutter SDK installed, so the app cannot yet be built for iOS at all. Not closed by this pass; retry once `specs/071-ios-mobile-port/tasks.md` Phase 1 (Setup) is complete.

---

## Dependencies & Execution Order

- **Setup (T001–T004)** → **Foundational (T005–T011)** blocks everything below.
- **US1 (T012–T021)** depends on Foundational; nothing else is reachable without an enrolled, connected phone.
- **US2 (T022–T029)** depends on US1 (needs an enrolled, connected phone to push to).
- **US3 (T030–T036)** depends on US2 for the push-fallback logic (T031 extends T022) and benefits from US1's connection code existing, though the reconnect supervisor itself (T030) can be developed alongside US1's initial-dial code.
- **Polish (T037–T045)** last.

**MVP** = Setup + Foundational + **US1** + **US2** (a phone can enroll — with revocation genuinely working — and receive explicitly-pushed content). **US3** makes that reliable in the real world (backgrounded, intermittent mobile networks) rather than only in a foreground demo.

## Parallel Opportunities

- T002 ∥ T003 ∥ T004 (Setup, different toolchains/files).
- T007 ∥ T008 ∥ T011 (Foundational, different files/regions); T005/T006/T009/T010 are sequential prerequisites for later tasks in their own files.
- Within US1: T015/T016/T017/T018/T019/T020/T021 in parallel once T012–T014 land.
- Within US2: T027/T028/T029 in parallel once T022–T026 land.
- Within US3: T033/T034/T035/T036 in parallel once T030–T032 land.
- Polish: T037 ∥ T038 ∥ T039 ∥ T040 ∥ T041 ∥ T042 ∥ T044 ∥ T045; T043 after all Python code tasks.

## Parallel Example: User Story 1

```bash
# Once T012–T014 land, launch all of these together:
Task: "Test QR enrollment creates node_type='edge' member row in tests/n2n/test_edge_enrollment.py"
Task: "Test domain-mismatch aborts before token exchange in tests/n2n/test_edge_enrollment.py"
Task: "Test plain-text enrollment regression (node_type='agent') in tests/n2n/test_edge_enrollment.py"
Task: "Test revocation blocks further delivery in tests/n2n/test_edge_enrollment.py"
Task: "Test EdgeChannel handler map excludes BGP/eN2N methods in tests/n2n/test_edge_enrollment.py"
Task: "Flutter widget test for enrollment flow in mobile/netclaw-mobile/test/"
Task: "Flutter test: enrollment key never readable as raw bytes in mobile/netclaw-mobile/test/"
```

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: US1 (enrollment)
4. Complete Phase 4: US2 (push)
5. **STOP and VALIDATE**: run quickstart.md steps 1–7 (enrollment through no-mirroring)
6. Deploy/demo if ready — this alone proves the core NCFED Edge Node concept end to end

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → US2 → test independently → deploy/demo (MVP!)
3. Add US3 (backgrounded delivery + resilient reconnect) → test independently → deploy/demo
4. Hand off to specs 067 (command channel) and 068 (biometrics/capture), both built on this foundation

## Notes

- [P] tasks touch different files (or clearly separable regions/toolchains) with no unmet dependency.
- [Story] label maps a task to its user story for traceability.
- Commit after each task or logical group.
- Stop at any checkpoint to validate a story independently.
- Avoid: implementing the WS listener's TLS via `internal_channel.build_ssl_contexts` — that
  path does not carry the domain-verified certificate; use `host_credential()` +
  `tls.server_context()` (T009) or phone-side verification silently falls back to trusting
  the wrong kind of certificate.
- Avoid: building new Python reconnect infrastructure for T030 — the proven pattern already
  exists (`_in2n_member_dialer`); the task is porting it to Dart, not inventing it.
- Avoid: adding `node_type` to `RiskManager.add_member()` — that function only mints the
  enrollment token and never touches the `member` row; `consume_token()` (T006) is the actual
  creation point (fixed post-`/speckit.analyze`, finding I1).
