# Existing Mobile QR path — November 4 assessment

The deployed protected cloud Border does **not** support the existing Mobile QR
enrollment flow as-is. The separately qualified cloud operations screen does not
establish QR enrollment support. The owner requested preserving the existing
scanner/device registration and adding its cloud enrollment entry in the HUD;
the proposed follow-up is [R04b](../../docs/roadmap/issue-310/briefs/R04b-cloud-hud-mobile-enrollment.md).

## Contract and present gap

- `mobile/netclaw-mobile/lib/ncfed/enrollment_qr_payload.dart` defines the existing
  `border_host`, `border_port`, `claw_domain`, `enrollment_token` payload.
  `enrollment_flow.dart:attemptEnrollmentFromQr` retains the current scanner path.
- `ncfed/edge_client.dart:EdgeClient.enroll` opens `wss://claw_domain:port/` with
  platform TLS verification, receives `n2n/edge/challenge`, and submits
  `in2n/enroll` with the device certificate and signed nonce. Reconnect uses
  `in2n/hello`; `enrollment_store.dart` retains device identity, not the spent token.
- `scripts/netclaw:risk_edge_token` currently creates the QR through the private
  daemon's `POST /n2n/enroll/token`. The current protected HUD has no QR issuer.
- `ui/netclaw-visual/src/hud-server/protected-server.js:createProtectedServer`
  allowlists runtime/operations/session routes and rejects WebSocket upgrades.
  `scripts/lib/protected_role.py:_OPTIONAL` excludes `N2N_EDGE_WS_PORT`;
  `bgp-daemon-v2.py:_start_edge` therefore reports `no_port` for this role.
- `bgp/federation/service.py:_edge_border_capabilities` truthfully disables legacy
  text, voice, attachments and request recovery on protected Borders. Its protected
  edge handler refuses `n2n/edge/ask`. Existing edge approval/task IDs are not the
  immutable protected operation review, revision, digest and ACK contract.

Device key possession and one-use device enrollment are distinct from user
sign-in. Removing user tickets/cookies does not supply the missing transport,
device registration or protected operation integration. Do not enable legacy Ask
or expose the daemon admin API to make QR scanning appear successful.

## Actual deployment evidence and limits

Private receipts under `~/.local/share/netclaw/roadmap-r04a-owner-20261104/` bind the
initial `c7b70edd` deployment and dedicated protected HTTPS service:

| Receipt | SHA-256 |
| --- | --- |
| `runtime-source-v2/source-receipt.json` | `1946d9a8585e09d62b6a0a3f95cb52c2f18b5ce93d5188b34fe78a1f47eb02a0` |
| `public-https-complete/verification.json` | `20002b00cc5d5b107ad34986f5ca48f8712616d25da8c01cb7d4b49a92e032a6` |
| `post-cutover-host.json` | `2d3cb9a1d51905a58494aba3616165d99103f69b60be3b2f405778d96546bca2` |
| `actual-cutover.json` | `e4854bc3d614d6c8ceb516f25db8091e8162a8979cfe68b361397a71955152ff` |

Caddy forwards to this protected service, not a legacy edge listener. The subsequently deployed `7f7df355` open-lab access change adds no QR/WSS routes.
Its actual public readiness receipt is
`open-lab-cloud-migration/public-readiness-v2/verification.json`, SHA256
`0e1ef7c34d186925b9297b19976a87d9ddda3863aad90ec682a0c4a24b762e74`. This assessment performed no new
enrollment, native installation or workload. November 3 simulator evidence remains
evidence for the separate cloud operations path; physical Mobile and cloud QR
enrollment are unqualified.

The bounded R04a compatibility correction only lets that existing separate screen
honor explicit `access.mode: open-lab` without user authentication. It retains
HTTPS/installation pins, exact review, historical owner attribution and no-replay
references. It introduces no replacement connection wizard and changes no scanner,
device keys or enrolled Chat flow.

Verification of this correction: 30 focused cloud client/widget tests pass,
including eight explicit open-lab cases. The combined cloud, enrollment, device
reconnect/lifecycle and existing Hermes compatibility selection passes 70 tests;
analysis of the four touched Dart files reports no issues. Coverage includes no
session requests/credential headers, strict mode/principal and installation checks,
retained historical failed results, lost decisions, durable unsubmitted proof and
background cancellation. This is source/unit/widget verification, not a new native
cloud or QR acceptance run.
