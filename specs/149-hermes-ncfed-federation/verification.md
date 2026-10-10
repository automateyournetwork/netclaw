# Spec149 verification — 2026-10-10

Implementation is verified for the Mac controlled-provider scope below. Linux/WSL
host qualification remains pending (T040); physical mobile and Android execution
are unrun. No production device configuration was changed.

## Observed toolchain

macOS26.5.2 arm64; Node24.19.0; isolated federation/bridge/tool Python3.12.12,
MCP2.3.0/FastMCP4.0.11; companion Python3.14.6; Hermesv0.21.6 source
`818c13be1dc4fd28987e1e881a9408224afd4535`. OpenClaw2026.7.1-2
(`0790d9f`) ran in isolated homes/gateway processes. Flutter3.44.8/Dart3.12.2,
Xcode26.6(17F113). No Android SDK/JDK was available.

The real fixtures execute pinned Hermes/OpenClaw and real MCP subnet code against
a deterministic loopback provider. Authenticated NCFED sockets, consent,
certificate possession, grants and enrollment run normally. This is actual runtime
execution with a controlled provider, not hosted-model/provider qualification.
Synthetic homes, copied source for drift tests and test-owned processes preserve
owner credentials/configuration/services. Reproduction is in tests/n2n/README.md.

## Acceptance and regressions

| Check | Actual result / scope |
|---|---|
| Real Hermes lifecycle + process loss | Final rerun:2passed,21.38s. Includes actual selected daemon CLI start/status/repeat-start/stop/restart from another cwd, no OpenClaw home/provider inference, plus actual subnet evidence; conversation-only chat; kill owned companion after dispatch, restart, retained unknown and zero replay; owner configuration preserved. |
| All-Hermes internal/external + mobile delegation | 1passed; actual iN2N and bidirectional eN2N tool/skill/contextual chat; two independent peer conversations; authenticated mobile→protected operator→official MCP→internal/external subnet result. Final combined acceptance run also passed this test. |
| Real Hermes mobile | 1passed; authenticated WebSocket enrollment, text/context, voice-origin composition, progress/reconnect, cross-device/key-generation denial, requested versus confirmed cancellation, explicit media refusal. No physical phone involved. |
| Mixed runtime matrix | 1passed,70.30s; six separate service processes and an isolated OpenClaw gateway; H/H,H/O,O/H,O/O internal skill results; bidirectional H/O external real tool/skill and two-turn contextual chat. |
| Shared NCFED suite | 585passed,4skipped,52.18s. Includes existing OpenClaw gateway/Ask Border/origin/attachment/progress/recovery, grants, knowledge, replication and authenticated transport tests. Four real-runtime fixtures intentionally skipped here and executed separately above. |
| Real Hermes HUD regressions | 24passed plus3subtests,57.57s, including all six real-agent/process integration tests, owned HTTP admission, Chat/Canvas/local Avatar contracts, source/config/auth failures, restart/stop and preservation. |
| HUD Node tests / build | 372passed; production build passed. Existing >500kB bundle warning remains. |
| Canvas regression runner | 27/27suites passed; no network devices contacted. |
| Flutter unit/widget regressions | 442passed; full existing suite plus canonical outcomes, request persistence/lost receipt, cancellation, legacy peers, Summary type and Watch/manual provisional-receipt recovery. |
| Flutter analysis | No issues. |
| Installer/CLI/preservation focused set | 46passed,8.51s. Final selected-lifecycle/runtime/recovery follow-up:17passed,2.03s. |
| Declared unit contracts | 832passed,2skipped across 96isolated modules; passed. |
| Catalogue | 111components,124registered servers,52external integrations; zero unexplained gaps. |
| Spec artifacts | 133specifications checked,4existing legacy exceptions; passed. |

## Mobile distribution

Source mobile version advances from1.0.2+4 to **1.0.3+6**. The Summary page includes
Border harness type/version/model/capabilities and unknown/last-received states.
The minimum for final qualified uncertainty/Watch recovery is1.0.3(6).

Build5 was signed, exported and accepted by App Store Connect at17:57Toronto;
it was superseded by build6 after a final Watch provisional-receipt recovery fix.
Build6's signed archive is `mobile/netclaw-mobile/build/ios/archive/Runner.xcarchive`.
All five app/extension bundles report1.0.3/build6, with iOS deployment target16.2.
The archive compiles iOS, Watch and Live Activity native changes; it is not a
simulator or physical-device execution test. Apple accepted build6 at18:09Toronto (22:09UTC); delivery
`40c66732-20b4-4977-997e-69d974b80a6c` entered processing. Final Apple processing
completion/tester availability was not observed. The Flutter wrapper subsequently
reported a missing local export directory because destination=upload produces no
local IPA; Xcode ContentDelivery explicitly reported UPLOAD SUCCEEDED with no errors.
See evidence/mobile-upload-6.json. The separate local export succeeded at `mobile/netclaw-mobile/build/spec149/export6/netclaw_mobile.ipa` (23MB). No public App Review submission or App Store release was performed.

Hermes photo/video/audio attachments are explicitly unavailable and rejected before
admission. Text produced by voice transcription is supported. Real microphone,
camera, Siri, Watch hardware, iPad and Android execution remain unverified.

## Defects caught and corrected

- Real companion loss initially left an upstream queued receipt visible after its
  worker died. Federation startup now preserves an explicit unknown outcome;
  read-only reconciliation cannot turn it back into a silent queue or replay it.
- Mixed real execution found OpenClaw gateway lookup ignoring the selected custom
  config. It now honors the selected config; all four pairs then passed.
- Watch manual status could retain a provisional request ID after phone recovery.
  The final client resolves both original admission and rebound task aliases by
  read-only lookup; build6 supersedes the earlier upload.
- Isolated n2n component registration changed old fixed-count installer assumptions;
  updated contracts validate the added registration and noncredential endpoint.
- The old HUD test expected blanket federation refusal. The updated contract
  requires503when the selected federation daemon is unavailable, and allows it
  only when matching installation/harness readiness succeeds.
- A broad combined Python invocation produced module-name collisions and missing
  optional dependencies. Families were rerun separately in their declared/isolated
  environments; that attempted invocation is not represented as a passing suite.

## Boundaries

Initial protected tool/skill qualification is read-only IPv4 subnet calculation
(`/24`–`/30`). Registered catalogue capabilities do not inherit that qualification.
Hermes production model guard/confinement fails closed and is not qualified here.
The MSP image is a proposed architecture, not multi-tenant isolation acceptance.
Source rollback/owner preservation tests do not establish safe database downgrade.
New interactive HUD browser/device qualification was not run; real HTTP/process,
Node and Flutter widget coverage is reported as such. Historical spec148 browser
and WSL evidence retains its original scope. See validation-handoff.md.
