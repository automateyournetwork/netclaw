# Spec149 qualification still to run

This is an execution handoff, not a pass. **T040 remains unchecked.** The current
session ran on macOS26.5.2 arm64. No current Linux/WSL shell was available in this
workspace; spec148's Ubuntu26.04 evidence belongs to its recorded commits.

## Linux / WSL

Use a separate checkout/home and explicit testing mode for initial read-only tests.
Install `subnet-calc n2n hermes-hud` with the Hermes installer and recorded isolated
interpreters; never repoint an owner companion for source-drift tests. Export the
three fixture variables in `tests/n2n/README.md`, plus `NETCLAW_OPENCLAW_BIN` for the
mixed matrix. Run the real lifecycle, external, mobile, mixed runtime and HUD
process fixtures through `tests/n2n/hermes_acceptance_149.py`. Record OS/kernel,
Hermes revision, Node/Python/MCP and model/provider fixture separately.

Then qualify actual systemd lifecycle: generate/install/enable selected units,
verify active unit ownership and restart behavior, verify exact inaccessible
Border secret paths and per-member writable state, and independently probe the
production model-guard route. Production Hermes remains refused until a separately
reviewed guard/confinement implementation is qualified. Generated unit text and
Mac failure-closed checks are not proof of Linux enforcement.

Verify repeated installation/source rollback with hashes of populated config,
identity, trust, skills, histories and unresolved task/effect ledgers. Do not
perform an in-place database downgrade. Repeat existing OpenClaw regressions.

## Physical mobile / Android

Install the App Store Connect candidate **1.0.3 (6)** after Apple processing and
appropriate tester availability. This session did not assign testers or submit a
public App Review release. Run against both Hermes and OpenClaw Borders:

- Physical iPhone/iPad typed Ask, real microphone transcription, Siri voice
  origin and spoken result, background/foreground reconnect and lost admission.
- Watch→phone Ask/history/manual status, Live Activity progress and termination;
  requested versus confirmed cancellation; uncertain work must never replay.
- Key revocation/re-enrollment, cross-device task denial and recovery across app
  process termination with the original admission ID.
- Confirm Hermes capture is explicitly unavailable; separately test real
  OpenClaw photo/video/audio capture, authorization and result behavior.
- Android build, emulator and physical-device protocol/UI tests with installed
  Android SDK/JDK. Neither build nor device execution ran here.

A signed archive compiles native integrations but does not prove hardware,
background delivery or Siri/Watch behavior. The existing Flutter/protocol tests
are recorded separately in verification.md. No full mobile parity claim is made.
