# Implementation Plan: R04b Mobile QR enrollment

**Branch**: `175-cloud-mobile-enrollment` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

## Summary

Extend the existing device enrollment authority and scanner, expose one narrow enrollment API to local/cloud HUD and VS Code Mobile, and route authenticated protected devices through the existing immutable operations backend. Qualify the actual local/cloud QR path in an isolated native iPhone simulator and preserve the intended owner pilot.

## Technical Context

**Language/Version**: Python3.12 federation; existing Node24.19/React18 HUD; TypeScript5.9 VS Code; Dart3.12.2/Flutter3.44.8 and Swift under installed Xcode27.2.

**Primary Dependencies**: existing SQLite, qrcode, WebSocket/TLS/P256, Express, VS Code APIs, Flutter secure storage/mobile_scanner. No new server/framework or hosted QR service.

**Storage**: additive private enrollment issuance records and existing private federation authority; device secure storage for keys/pending identity/references; QR matrix only in transient UI memory.

**Testing**: focused Python refusal/authority tests, Node route/UI tests, extension tests, Dart lifecycle/widget tests, native iOS26.5 simulator with actual QR image decode.

**Target Platform**: actual Mac browser/VS Code, local isolated Border, retained GCP Montréal Border, iPhone17 Pro simulator.

**Project Type**: extension of existing federation, HUD and clients.

**Performance Goals**: finite120second offers, maximum one outstanding offer, bounded message/matrix sizes and operation deadlines.

**Constraints**: trusted TLS; installation/device binding; no user authentication scheme; no effect replay; preserve existing retained cloud state and December1 lifetime.

**Scale/Scope**: one owner development pilot, one isolated local test Border, bounded device enrollments and one separately reviewed protected read. Physical camera/SecureEnclave not qualified by simulator.

## Constitution Check

Pre-design and post-design PASS. Observe/baseline before cloud changes and verify after; root GAIT owns the audit. Existing MCP execution and immutable approval store reused, no new tool server/catalog component. Device registration is explicitly not user authentication; open-lab exposure remains the owner's bounded exception. Existing private secrets/keys stay private. Source/specs/tests updated together. Root preserves source1.18.5, extension1.6.0, Mobile1.0.3+6. README/public rollout/blog deferred under explicit roadmap hold, documented maintainer evidence instead. Owner kickoff and explicit local/cloud/native steering ratify this feature; no further optional implementation loop or later roadmap stage is inferred.

## Project Structure

- `mcp-servers/protocol-mcp/bgp/federation/`: issuance records, edge-only token consumption, authenticated device authority, existing protected operation dispatch.
- `scripts/lib/protected_role.py` and `mcp-servers/protocol-mcp/bgp-daemon-v2.py`: explicit bounded loopback edge configuration.
- `ui/netclaw-visual/src/hud-server/`: narrow issuer handler and protected allowlist, local adapter; `src/` Mobile enrollment card.
- `extensions/netclaw-vscode/src/`: selected-connection Mobile view and client methods; QR matrix rendered locally.
- `mobile/netclaw-mobile/lib/`: additive QR/persisted binding, pending enrollment, capabilities, protected WSS adapter and production review UI.
- `mobile/netclaw-mobile/ios/` and `integration_test/`: separate native simulator harness and actual QR decode, production hardware path preserved.
- `tests/`, component test directories and this spec: focused verification and retained evidence.

Root owns spec/contracts, integration, exact deployment packet and acceptance. Backend, surfaces and Mobile own separate worktrees and files. Shared protocol is frozen in contracts before implementation. Single finite implementation pass; fixes follow observed failures rather than automatic loops.

## Complexity Tracking

Simulator cannot use camera image analysis or SecureEnclave in the installed scanner/plugin. A separately identified simulator-only harness uses native CPU QR decoding and Keychain P256 to exercise the production enrollment handler and full protocol. Hardware behavior stays unchanged and unqualified. This adds no production authentication mode or tool bypass.
