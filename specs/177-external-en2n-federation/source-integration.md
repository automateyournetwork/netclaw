# R06 acceptance and source integration

Source PR: [#333](https://github.com/automateyournetwork/netclaw/pull/333).

The owner accepted completed R06/Spec177 on2026-11-06 and explicitly requested
commit, PR, merge, completed-branch deletion and return to main. All35technical
SDD tasks are complete. This supersedes the earlier R06 source-integration hold;
[verification.md](verification.md) retains actual evidence and qualification
limits. Source integration does not redeploy the frozen tested installations.

Feature branch: `177-external-en2n-federation`.
Base: `6cdfde1e5834725907ed9e4b14f44f22e45013a4` (R05 merge #331).
At integration kickoff, main still matched that base. The separate open
[#332](https://github.com/automateyournetwork/netclaw/pull/332) uses
`177-defenseclaw-sidecar-identity`; keep both full directory names. Its unrelated
change is not part of this PR. Expected next free number is178, rechecked at R07
kickoff. GitHub's merged PR/check records and private final Git/GAIT receipts
remain authoritative for the eventual integration outcome.

## Completed behavior

[Short write-up](completion-summary.md): two independent cloud organizations and
local C passed all six directions of inventory, contextual chat, native subnet
tools, asynchronous skills and original-result retrieval. Actual browser, Mac
VS Code and native iPhone simulator clients passed, along with scope refusals,
budget/consent boundaries and loss/restart recovery. Native effect accounting
and retained failures remain in the verification and parity matrix.

## Validation and source coherence

The qualified implementation has1758broad federation/native/cloud passes with
5existing skips, final520HUD passes,206editor passes with3existing live skips,
499Flutter passes with clean analyzer, and22cloud/retirement passes. Actual
provider/cloud/native-client evidence is separate from these source tests.

Integration adds `cloud-r06` to the contract-suite manifest so its22offline
plan/host/retirement tests run in CI. This closes the declaration gap for the new
test family; no live cloud execution runs in CI. Clean tracked candidate `51e156fc` passed the SDD artifact gate (165 specs,
4 historical exceptions), FastMCP/task adoption, all six reconciliation surfaces,
catalog coverage and suite inventory (36 total suites,33 CI suites). The new
cloud-r06 suite also passed through the canonical runner with isolated dependencies.
New maintainer-document links and the complete staged whitespace check passed.
PR checks must pass before merge; GitHub retains the final check outcomes.

Commands run on the clean tracked candidate:

```sh
python3 scripts/verify-spec-artifacts.py
python3 scripts/check-fastmcp-compat.py
python3 scripts/check-mcp-tasks.py
python3 scripts/reconcile-mcp.py --surface catalog --surface dependencies --surface docs --surface meraki-ids --surface packages --surface portability
python3 scripts/verify-catalog-coverage.py
python3 scripts/run-contract-tests.py --list
python3 scripts/run-contract-tests.py --matrix
```

Canonical isolated suite execution in the working checkout:
`python3 scripts/run-contract-tests.py --suite cloud-r06 --prepare`.
No unchanged live workload was replayed for source integration. Startup pyATS
inventory remained unavailable because its selected HTTP runtime is missing;
MemPalace source is absent. GAIT and file memory retain this source-only session.

## CI fixture correction

The first federation CI run on68177a3c found7failures: the R06 workflow/refusal
fixture assumed an ignored installed subnet MCP clone existed in a fresh checkout.
The remaining1734tests passed, with5existing skips. The corrected fixture includes
only the exact reviewed4,896-byte upstream source and its Apache-2.0 license under
`tests/fixtures/subnet-calculator-177/`, pinned to the existing installer manifest.
Tests apply the same hash-checked migration in a temporary tree and execute the
real native MCP; no test is skipped and no operator installation is changed.
Focused workflow/refusal tests pass10/10. The full federation suite in the clean
checkout with this exact fixture delta passes1741tests,5existing skips and94
existing warnings (101.55s), with no installed subnet checkout present.
Chat/skill model behavior remains a
labeled deterministic fixture, separate from actual cloud/provider evidence.

The upstream text fixture preserves one original whitespace-only line because
changing it would invalidate its reviewed hash. Source whitespace checks exclude
only `tests/fixtures/subnet-calculator-177/upstream.py.txt`; all other source is
checked normally. Final PR checks remain authoritative for the integrated head.

## Retained runtime and release boundary

Source1.18.6, extension1.6.1 and Mobile1.0.4+7 remain unchanged. The owner's
roadmap hold is the coordinated release plan: no source release/tag, package or
Marketplace publication, blog/announcement or general cloud rollout before the
roadmap's release gate. This PR contains maintainer evidence and planning notes.

R06 remains retained until its approved November8 window:15:09:35Z quiesce/export,
15:14:35Z exact owned cleanup,15:19:35Z independent STOP/network fallback. Cleanup
is scheduled, not yet observed; keep the Mac awake/online. R05's November7 jobs,
original Border December1 lifetime, private current state and one-use receipts
remain unchanged. Never replay spent claims or infer disk/IP deletion from STOP.

## Following work

[R07–R10 brief](../../docs/roadmap/issue-310/R07-R10-next-steps.md): recovery gate,
HA authority, GCP multi-region, then Azure single region. Each has its own SDD,
actual acceptance and separate VS Code/Mobile disposition. This source-integration
request does not start those stages or authorize new resources.
