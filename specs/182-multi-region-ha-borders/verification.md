
## Stream B: client region display (T022-T025, T038, T040 prep), 2026-11-08

Display-only region label (`contracts/region-display.md`), added in HUD `ui/netclaw-visual/src/shared/cluster-binding.js`
(`regionLabel`, `clusterNodeRegion`, `clusterFailoverNotice`), VS Code `extensions/netclaw-vscode/src/client/cluster.ts`
(same names; surfaced as `serving_region`/`failover_notice` in `src/views/owner.ts` evidence), Mobile
`mobile/netclaw-mobile/lib/ncfed/endpoint_recovery.dart` (`regionLabel`). HUD UI: `src/dashboard/ClusterTrustGate.jsx`.

T025 signed-manifest validators unchanged: `git diff HEAD` is empty for `mcp-servers/protocol-mcp/bgp/federation/ha/config.py` and
`mobile/netclaw-mobile/lib/ncfed/cluster_trust.dart`; in `cluster-binding.js` the diff has 0 removed lines (append-only, validator
functions untouched); `cluster.ts` change is append-only.

Results (exit codes read directly, not through pipes):
- HUD `npm test`: 545 pass, 0 fail (includes new region test); `npx vite build`: exit 0.
- VS Code `npm run check` (tsc): exit 0; new `test/cluster-region.test.mjs`: pass; `npm test`: 210 pass, 2 fail, 3 skip.
  The 2 failures ("openclaw/hermes: actual managed HUD launcher owns and stops API, Vite and companion") also fail with
  these changes stashed (baseline), so they are pre-existing and unrelated; not investigated further here.
- VS Code `npm run build`: exit 0. Local package (NOT published, version NOT bumped, 1.6.1):
  `/private/tmp/claude-503/-Users-john-capobianco-netclaw/8e4f7aba-bfb3-4565-9ae8-2535153d5ff0/scratchpad/netclaw-182-local.vsix`
  built with `vsce package --no-dependencies` because `scripts/package.mjs` requires a clean committed tree.
- Mobile `flutter test` (new `test/endpoint_recovery_182_test.dart`, plus 178 and cluster_179): all 22 pass; `flutter analyze` on touched files: no issues.
