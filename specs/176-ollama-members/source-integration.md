# R05 source integration and clear-session handoff

The owner accepted R05 on2026-11-06 after the technical/cleanup handoff and
explicitly requested commit, PR, merge and return to main. All33 tasks are closed;
[verification.md](verification.md) retains actual evidence, failed/unknown outcomes
and platform limits. GitHub's merged PR and checks are authoritative for the
integration outcome; private final Git/GAIT receipts and daily memory retain the
exact merge/check identifiers. Source integration does not redeploy tested runtimes.

## Source and validation

Feature branch: `176-ollama-members`, baseline `db0c9682d4997d51a15f75cbf2df83b97d3c3f45`.
Latest production recovery correction: `ab475890`; test-only native driver correction:
`c64f3f18`. Upstream `ea2e2e3b` adds a separate documentation-only
`specs/176-convergence-vm-security/`. Preserve both full Spec176 directory names.
No version bump: source1.18.6, extension1.6.1 and Mobile1.0.4+7. No source release,
tag, package, Marketplace publication, blog or public cloud rollout is authorized.

Protected Python suite:776 passed. HUD47, extension200+3 existing live skips,
Mobile491; later focused presentation checks122 (44/38/40), with builds/typecheck/
analyzer clean. Actual browser, Mac development-host VS Code and iPhone17Pro/
iOS26.5 simulator evidence is separate from fixtures. The normal installed
extension was preserved. Physical phone, Windows/WSL, Hermes Ollama, GPU, other
models, HA and external federation remain unqualified. Native ACK loss was
protocol-tested; the actual lost client HTTP response is a separate case.

Required source artifact, six-surface reconciliation, catalog coverage and
contract-suite list/matrix checks passed in a clean tracked checkout at
`507b3ec4`, matching CI:164 specs/4 historical exceptions, all six reconciliation
surfaces,112 catalog entries/126 registered/52 external,35 suites/32 CI suites.
FastMCP compatibility and MCP task adoption checks also passed. Commands:

```sh
python3 scripts/verify-spec-artifacts.py
python3 scripts/check-fastmcp-compat.py
python3 scripts/check-mcp-tasks.py
python3 scripts/reconcile-mcp.py --surface catalog --surface dependencies --surface docs --surface meraki-ids --surface packages --surface portability
python3 scripts/verify-catalog-coverage.py
python3 scripts/run-contract-tests.py --list
python3 scripts/run-contract-tests.py --matrix
```

The full-range whitespace check identified Markdown hard breaks (removed) and
literal context/removal whitespace inside the hash-checked native MCP patch.
That patch format is preserved; the source whitespace check excludes only that
patch file. No production code changed after the recorded qualification.

The installed working checkout separately reports an unchanged, ignored HumanRail
clone with unbounded `mcp>=1.0.0` and legacy `mcp.server.fastmcp`. Its clean pinned
clone matches both existing Spec141 migration before-hashes; the read-only patch
check reports “2 reviewed files ready.” Tracked migration/pins/checker/workflow
match upstream. No unrelated runtime is patched, no failure is waived and clean
source success does not imply installed-runtime compatibility. Exact commands,
exit codes and output are retained privately under `source-integration/`.

## Retained deployment and evidence

Private root: `~/.local/share/netclaw/roadmap-r05-20261105/`.
Use `current-state-20261106/CURRENT-STATE.json` and current local/cloud handoff
pointers. Primary, supplemental and scheduler-addendum seals and receipts are in
verification. Do not replay old activation, enrollment, approval, recovery or
cleanup packets. Original unknown outcomes and the unfinished inference claim
remain preserved; successful recovery never erases them.

Disposable cleanup is complete. Intended local/cloud NetClaw Ollama members remain
for the approved48-hour delivery, over strict iN2N with no Tailscale. Full teardown
is scheduled for2026-11-07: quiesce14:36:25Toronto; exact ten-resource destruction
no earlier14:41:25Toronto. Current execution-manifest SHA256 is
`5b6a39412c4d02f8ab9ad3923af9768eef34eddc62cd281820a13f41b7d201ec`.
The Mac must be awake/logged-in/online with Docker and gcloud/IAP authorization.
Independent VM STOP does not remove disk/IP charges. Future deletion remains an
operational obligation; check actual receipts/inventory after interruption.
Preserve the existing Border's December1 scope and all unrelated runtimes.

## Next session

Read the [roadmap index](../../docs/roadmap/issue-310/README.md) and
[R06 brief](../../docs/roadmap/issue-310/briefs/R06-external-en2n-border.md).
The next free spec is expected177; recheck upstream branches/PRs at kickoff.
R06 requires an independently administered external Border, bilateral consent,
verified peer identity and one explicitly exported capability over eN2N/NCFED,
without internal member access. External placement remains a kickoff decision.
Keep separate VS Code/Mobile impact and evidence under G12/G13.

The unchanged sequence is R06 external federation → R07 recovery gate → R08
Border HA → R09 three-region GCP mesh → R10 Azure single region. R07 must pass
before multi-region work. No next-stage implementation or new cloud spending is
authorized by this closeout. Thermidor remains a source of proven lessons;
historical transport/runtime evidence never replaces fresh NetClaw qualification.
