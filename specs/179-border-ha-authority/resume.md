# R08 in-progress resume

Continue branch179-border-ha-authority and its48task SDD plan. Owner authorized
R08 completion with three implementation agents in separate worktrees. NCFED is
the foundation; R09, cloud/device changes and public rollout/release remain out
of scope.34tasks now close source/fixture scopes;14remain, including REAL/native
qualification and actual owner acceptance. No REALmodel/nativeeffect or actual
HA browser/Code/Mobile acceptance has occurred.

Private root:~/.local/share/netclaw/roadmap-r08-20261107/. All R08 voters/proxies
are stopped at this checkpoint. Initial etcd-fixture-01 has353record export;
Raft03 has254record export and its6owned containers stopped. Never start the
superseded prepared Raft02 packet. No old fixture is a fresh activation payload.

Actual fixture evidence:core-03 baseline; matrix-raft-network-01 directed Raft/
NCFED/quorum cuts and latency safety; matrix-raft-recovery-02 two-voter loss,
NOSPACE/heal and full voter restart; matrix-retire-01 old-key refusal. Preserve
all earlier failures.300ms quorum latency exceeds the3s admission window and
safely refuses; no R09 availability claim. process-fixture-01 proves actual4OS
process crash/restart/replay fencing but had3Border cleanupTimeoutErrors.

fenced-restore-fixture-01 on d3ed8c3c passes genuine stale rev10→later unknown15
operation/claim/reservation gap, trusted7subject isolation, fresh generation and
status-only activation with global capacity_frozen. All4workers exit0 and owned
sockets close. All3old voters are stopped/disconnected/restart-disabled; all3new
voters are exported17records and stopped. Independent review verifies all65
export hashes and historical receipt signature. Missing history is not recovered
and execution capacity stays fenced. The earlier cleanup failure stays retained.

T021/T034 remain open: independent review requires actual paused old leader while
a member remains unaware, actual iN2N result/ACK loss through production recovery,
and explicit live role/member/external/etcd trust negatives. Qualification agent
prepares a fresh wire_recovery_fixture driver. Root serializes its actual run on
new direct3voters, then exports/stops them. Do not reuse isolated old generations.

Authority agent prepares REAL instrumented control/observer source; unmodified
production native positives come first. Counter reservations are not executions;
actual guard ingress logs differ from model requests. Unknown totals remain
unknown. Exact held submit/clock/proxy controls are qualification-only and must
not become product bypasses. Fresh R08 model/guard logs pin json-file/no rotation;
log completeness and request format still require actual evidence.

Client agent prepares private ios-harness-01 from79tracked Mobile files with
source map36a18a47a7e788a56feaff72cb01a2d9f27c6b925d97c2ee5d0d6123f1a33c10.
No simulator boot/install/launch. First compile failed because nested SwiftPM
sandboxing conflicted with outer network denial; preserve failure. Heavy builds
are held during live admission fixtures and require coordinator scheduling only,
not new user permission. Fresh bundle/key namespace; no Firebase/watch/owner data.

Root checks:1998federation pass/5skip; later110pass+56subtests; restore/process31;
HUD538; editor211/3skip plusbuild/typecheck; Mobile525+clean analyzer. Browser
profile-onlyCA setup has hostname/unknownCA negatives. client-toolchain-01.json
pins Chrome156.0.8078.80,Code1.109,Node24.19,Playwright1.61.1. hud-closure-01.json
inventories74packages/705files/5,313,668bytes after current Vite build. Final source
and matching fixture gate are required before REAL preparation/model activity.

Complete remaining fixture/source review, freeze fresh REAL10operation/20inference/
10native-effect packet, actual native/client/fault/recovery evidence, measurements,
owned cleanup/preservation, memory/GAIT and owner acceptance before R09. Read
verification.md, qualification-matrix.md, measurements.md and runbook.md; unfinished
measurements are explicit. Never reset a spent claim, unknown slot or capacity fence.

Versions source1.18.7/editor1.6.1/Mobile1.0.4+7 remain unchanged. Active GAIT branch
r08-sdd-implementation-20261107, latest progress9107f5c7. End with memory and gait_log.
Startup pyATS/MemPalace unavailability remains; do not repair unrelated environments.

## ⚠ R09 RELEASE GATE: client builds MUST be updated for multi-region HA Borders

Owner instruction (2026-11-08): at the R09 checkpoint (three-region / multi-region deployment of
these HA Borders) the **VS Code extension, the Mobile app and the HUD/Border source builds WILL need
a published update**. This is a hard gate, not a nice-to-have. Until those builds ship, do not
announce, enable or document multi-region HA as available to end users.

What must be true before R09 is called released (verify each; none is done by R08):
1. **VS Code extension** (source version now 1.6.1, `extensions/netclaw-vscode`): a build that includes
   the cluster-aware paths proven in R08 (signed-manifest pinning, native endpoint replacement,
   retained-reference recovery, no-quorum/stale-review states) AND the multi-region additions R09
   defines (region-aware endpoint lists, failover UX). Bump the version, build, publish through the
   owner-approved channel, and check the marketplace-installed version against source.
2. **Mobile app** (source 1.0.4+7, `mobile/netclaw-mobile`): same, including enrollment against a
   multi-region cluster descriptor, `select-node` across regions, and background/cold recovery. Needs
   an owner-approved TestFlight/App Store submission; App Store review time is outside our control.
3. **HUD / Border source** (main is at 1.19.1 after PRs #335-#337; this branch's HUD fixes include the
   cluster-mode mobile-enrollment contract fix): ship the refreshed HUD build with the Border release
   so every Border serves the fixed enrollment route.
4. Re-run the client journeys of `evidence-matrix.md` (HUD, VS Code, iOS) against the **published**
   builds on the multi-region topology, not against repo checkouts.
5. Owner approval for every outward-facing release step; nothing is published, pushed live or
   announced by an agent without it.

Known R08 facts to carry into R09: no extension or app product code changed in R08 except the HUD
enrollment fix; the shipped client versions were not verified against source during R08; R08 used a
single-host loopback topology (no WAN, no regions, no public DNS/TLS).
