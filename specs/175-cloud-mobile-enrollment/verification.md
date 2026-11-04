# R04b verification — in progress

No implementation or native acceptance is claimed yet.

## Startup and baseline

Clean main209cba6f matches fetched upstream; no open PR at kickoff. Spec175 and
three separate worktrees created. GAIT branch r04b-cloud-mobile-qr-20261104
explicitly checked out and verified. Startup default pyATS unavailable (HTTP
runtime missing); MemPalace unavailable (module missing). No device query or
runtime install was substituted. GAIT uses the existing local gait_mcp interpreter.

Actual read-only GCP IAP observation succeeded: retained protected federation,
HUD, normal workspace gateway/HUD and Caddy remain running; historical R01 apps
remain stopped. Current role/HUD/source-manifest/Caddy hashes and listener inventory
are private at ~/.local/share/netclaw/roadmap-r04b-20261104/cloud-readonly-baseline.json.
No configuration, enrollment, workload or cloud resource was changed by this probe.
A full authority/state snapshot remains required immediately before deployment.

Installed Xcode27.2, Flutter3.44.8/Dart3.12.2 and iOS26.5 iPhone17 Pro simulator
are available. Simulator optical camera/mobile_scanner analyzeImage and physical
SecureEnclave are unavailable: separate test-only native decoder/key harness is
planned, with production enrollment UI and protocol shared.

## Acceptance matrix

| Surface/behavior | Local | Cloud |
|---|---|---|
| HUD visible QR generation | Pending | Pending |
| Native VS Code Mobile QR generation | Pending | Pending |
| Native simulator actual QR decode/enroll | Pending | Pending |
| Same-key reconnect/uncertain enrollment | Pending | Pending |
| Protected exact review/result/ACK | Scoped fixture pending | Actual read pending |
| Background/process recovery/no effects | Pending | Pending |

Physical iPhone/camera/SecureEnclave and other platforms are unqualified. Existing
R04a evidence retains its original source and scope; it does not qualify R04b.
