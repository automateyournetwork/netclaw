# Verification ledger

Run2026-10-31 / start00:09:29UTC / deadline00:54:29UTC / three attempts per task.
Checkout /home/ubuntu/netclaw-convergence-read, branch162-convergence-read,
base4d791a364989405a98ac52bec91a9530cf4317b4. Prior spec1012 is complete; this is a
new user-authorized milestone. Main fork/runtime untouched. Spec Kit workflow is
executed manually against checked-in instructions, with spec committed before code.

T001 COMPLETE: proposal accepted, current upstream and open PR/branch inventory
checked;162 unused. Public external build f54bafca and common tool envelope agreed.
T002/T003/T004 attempt1: implement scoped connector, HUD and installation surfaces.
Required evidence is the spec acceptance; missing hosts or credentials are gaps.
Delegates may not push, deploy, merge or change shared files outside assigned scope.

T002/T003 attempt1:17 connector/projection tests and393 HUD tests PASS; production
build PASS. Independent review found missing native defaults and an escaped-token
redaction gap; both corrected with regressions. T004 adds scoped registration
regeneration after settings, with safe defaults and no broader credential reuse.
Catalog descriptors/generation, metadata, all six reconciliation surfaces and
spec artifacts PASS. Installer qualification is running separately.

T005 attempt1: real pinned demo export reaches the new summary tool, but evidence
returns compatibility. This is a contract gap in the new reader, not a service
pass or a reason to weaken scope checks. T005 attempt2 captures the private
synthetic raw response to identify the unsupported field shape before correction.
The harness reuses only the pinned service's disposable producer/cleanup fixture,
replacing its consumer callbacks with the new connector/native projection/HUD.
No service deployment code is imported into upstream.

T005 attempt2 COMPLETE: actual GoFlow2 protocol fields are named UDP/TCP, not only
numeric. Added bounded named-protocol validation and regression without relaxing
scope/window/address checks. Both demo and host paths PASS through real retained
storage, viewer-scoped generated native MCP entry, Chromium HUD selection, repeat
installation, disable/reprojection and restart persistence. Demo:2 records; host:
62 summary records and64 latest records (traffic continued between reads). Browser
156.0.8078.4, zero JavaScript errors. Private artifacts and logs are under
~/.local/state/convergence-read-evidence and convergence-home-test; no credentials,
raw diagnostics or machine traffic are committed. Service pinned f54bafca.

T006 attempt1 independent verifier PASS:18 connector tests,9 catalog tests,
metadata/generation/whitespace; native lifecycle and workflow reviewed. All earlier
findings resolved.393 HUD tests and production build PASS. Installer suite PASS.
T004 attempt2 corrects missing plan dispatcher and additive inventory assertions.
Local broad tests initially encountered group-writable fixture paths (umask002);
rerunning with022 tests the documented ownership guards without weakening them.
Host integration and browser tests do not claim a full gateway/model session.
Native ARM64 hosted execution remains pending; macOS/WSL/Hermes and physical
network capture remain unqualified.

T004 attempt2 COMPLETE: explicit stdio launcher declaration matches existing native
components; inventory assertions include the new component and check its safe
defaults exactly. Targeted installer/default/routing checks37PASS,1existing skip.
Setup-installer suite PASS (272 tests,32 skipped); installer suite PASS.
Full unit suite is running with umask022; core deployment fixtures now pass without
source changes. Reconciliation, spec artifacts, generated catalog, metadata,
coverage and release metadata/tests PASS. Source release1.15.0 prepared; no tag
or deployment published. T006 hosted CI and upstream publication remain pending.
