# Research: Merge Modular TUI Installer with Full Component-Coverage Parity

**Feature**: 049-merge-modular-installer
**Date**: 2026-07-08

## R1: Why the PR Is Reported as CONFLICTING

**Finding**: PR #96 (`ae0afd6`) branches from `97a0e8b` ("045 ue5 digital twin"). Main has since advanced through specs 046 (Three.js viz + sketchfab-mcp-server), 047 (docs inventory reconciliation), and 048 (chrome-devtools-mcp), each of which added steps to the old monolithic `scripts/install.sh` — the exact file PR #96 deletes wholesale (3,391 of its 3,472 total deletions) and replaces with a 360-line dispatcher. Git cannot 3-way-merge "delete this whole file" against "three independent sets of edits to lines inside it," hence `mergeStateStatus: DIRTY`.

**Decision**: Resolve by rebasing/merging main's current state into a working copy of PR #96's branch, taking PR #96's new `scripts/install.sh` + `scripts/lib/*` wholesale (no textual line-merge needed there — it's a clean replacement), then manually re-adding installer support for everything main gained since branch point as new catalog entries + install functions (this is the real work, not a git mechanics problem).

## R2: Actual Catalog Coverage Gap (Manual Audit)

**Method**: Compared PR #96's `scripts/lib/catalog.sh` (72 entries) against `config/openclaw.json`'s 51 registered MCP servers on current main plus README.md's full 110-row MCP Servers table (the authoritative human-curated inventory, since 59 of the 110 are "externally documented" integrations not captured as static JSON — built-in plugins, remote OAuth services, etc.).

**Confirmed gaps** (catalog entries to add or expand):

| Gap | Existing on main since | Notes |
|-----|------------------------|-------|
| GNS3 | spec 012 (predates PR #96 branch point — a **pre-existing** gap PR #96 inherited, not one it introduced) | `gns3-mcp` registered; no catalog entry at all |
| DevNet Content Search | spec 026 (pre-existing gap) | `devnet-content-search` registered; no catalog entry |
| Memory MCP | spec 033 (pre-existing gap) | Distinct from `mempalace` (which IS in the catalog) — `memory-mcp` has no entry |
| Ollama Domain Experts | spec 037 (pre-existing gap) | No catalog entry at all |
| Telemetry receivers (SNMP trap, syslog, IPFIX/NetFlow) | spec 010 (pre-existing gap, oldest one found) | Three related UDP receivers, registered as `snmptrap-mcp`/`syslog-mcp`/`ipfix-mcp`; no catalog entry |
| Nautobot Golden Config | spec 028 (pre-existing gap) | `nautobot-golden-config-mcp` registered; catalog's single `nautobot` entry doesn't cover it |
| Nautobot Routing | spec 030 (pre-existing gap) | `nautobot-routing-mcp` registered; same issue |
| Base Twilio (core API/messaging) | spec 039-ish era (pre-existing gap) | `twilio-mcp` (core `@twilio-alpha/mcp`) registered separately from `twilio-voice-mcp`; catalog's `twilio` entry describes only the voice one |
| Three.js Network Viz + Sketchfab | spec 046 (post-branch-point — genuinely introduced by the conflict window) | `threejs-network-viz` skill + optional vendored `sketchfab-mcp`; no catalog entry |
| Chrome DevTools (headless + Watch Mode) | spec 048 (post-branch-point) | This feature's specific retrofit target (see R4) |

**Not a gap**: `scripts/verify-inventory-counts.py` and other spec-047 maintenance tooling — these are repo-maintenance scripts with nothing to "install," correctly out of scope per the spec's Assumptions.

**Decision**: Treat the pre-existing gaps (present even at PR #96's own branch point) and the post-branch-point gaps (046/047/048) with the same bar — FR-002/FR-003 require full parity with *current* main regardless of when a given gap was introduced. Nine new/expanded catalog entries in total close this list. This is a bounded, enumerable list — not an open-ended audit — which keeps this feature's scope tractable.

**Important caveat**: This is a manual, one-time pass. Per FR-008, the actual authority going forward is the coverage-check script (R3) — if this manual pass missed anything, the script will catch it, and that's the point of building it.

## R3: Coverage-Check Script Design

**Decision**: Add `scripts/verify-catalog-coverage.py`, modeled directly on the existing `scripts/verify-inventory-counts.py` (same language, same "enumerate ground truth, enumerate the artifact, diff, exit non-zero on unexplained gap" shape, same repo convention of a small stdlib-only script). It:

1. Enumerates `config/openclaw.json`'s `mcpServers` keys (ground truth for registered servers).
2. Enumerates `scripts/lib/catalog.sh`'s catalog ids (parsed the same simple `|`-delimited way `catalog.sh` itself parses).
3. Loads a small, explicit allow-list of intentional groupings/exclusions (e.g., `checkpoint` → covers all 15 `chkp-*` servers; `aws` → covers 6 AWS servers; maintenance scripts with no install step) — this is the mechanism that satisfies the spec's Edge Case about distinguishing real gaps from documented intentional exclusions (FR-010).
4. Reports any registered server that isn't covered by a catalog id (directly or via the allow-list) as a gap, with a non-zero exit code.
5. Does the same comparison for `workspace/skills/` against catalog coverage, for skills that have their own MCP dependency (a skill with no MCP server of its own, calling only already-covered servers, doesn't need a separate catalog entry — also encoded in the allow-list).

**Rationale**: A script that can be re-run on every future feature branch (not just this one) is what actually satisfies FR-008 ("repeatable... not a one-time manual audit"). Reusing the existing script's shape keeps it consistent with repo convention rather than inventing a new style.

**Alternatives considered**: A pure documentation checklist (rejected — exactly the failure mode that created this gap in the first place, since PR #96's own stated test plan was manual/eyeball); folding this into `verify-inventory-counts.py` itself (rejected — that script's job is skill/MCP *count* reconciliation across docs, a different concern from catalog *coverage*; keeping them separate, single-purpose scripts is more consistent with the repo's existing one-script-per-concern pattern).

## R4: Chrome DevTools Retrofit — One Catalog Entry, Both Registrations

**Decision**: Add a single catalog entry, `chrome-devtools`, whose `component_install_chrome_devtools()` function registers *both* `chrome-devtools-mcp` (headless) and `chrome-devtools-mcp-visible` (Watch Mode) and provisions/resolves the Chrome binary — mirroring the precedent already set by `checkpoint` (one entry, 15 servers) and `aws` (one entry, 6 servers). An operator selects "Chrome DevTools" once; both registrations and the browser resolution happen together, since they're one capability from a user's point of view.

**Rationale**: The spec's FR-010 explicitly permits this style of grouping when it matches existing precedent, and splitting headless/Watch Mode into two separately-selectable catalog entries would be user-hostile — nobody wants "headless Chrome DevTools" without also being able to ask for Watch Mode, they're two modes of one thing.

## R5: Fate of `scripts/chrome-devtools-enable.sh` (resolves FR-006)

**Decision**: **Keep it standalone**, and additionally inline equivalent logic into `component_install_chrome_devtools()`. Do not delete it, do not have the new install function shell out to it.

**Rationale — direct precedent found in PR #96's own tree**: `scripts/forward-enable.sh`, `scripts/memory-enable.sh`, and `scripts/defenseclaw-enable.sh` all still exist standalone in PR #96's branch, untouched, *alongside* their own inlined `component_install_forward()` / equivalent functions. Inspecting `component_install_forward()` directly confirms it reimplements Forward's clone/build/env-setup logic inline rather than calling `forward-enable.sh`. This is the new architecture's actual, observed convention: the TUI-driven install function is self-contained (so `install.sh` never has to shell out to N different scripts with N different flag conventions), while the standalone `*-enable.sh` script remains available for direct, non-TUI use (re-running just that one piece, CI, documentation examples that predate the TUI, etc.). Chrome DevTools already has extensive documentation (`mcp-servers/chrome-devtools-mcp/README.md`, `quickstart.md`, both `SKILL.md` files) pointing at `chrome-devtools-enable.sh` by name — keeping it avoids a documentation-wide rename for no functional benefit, while still giving the TUI its own self-contained function per the architecture's convention.

**Alternatives considered**: Deleting the standalone script and having the install function be the only entry point — rejected, breaks existing documentation for no gain and contradicts the pattern set by three other existing components in the same PR. Having `component_install_chrome_devtools()` call `bash scripts/chrome-devtools-enable.sh` — rejected, doesn't match how `forward`/`memory`/`defenseclaw` do it (they inline, not delegate), and PR #96's own components generally avoid shelling out to other scripts within an install function.

## R6: Constitution Amendment Scope

**Decision**: Amend Principle XI ("Full-Stack Artifact Coherence") and the associated Artifact Coherence Checklist, replacing the line `scripts/install.sh — installation steps for new dependencies` with language describing the catalog-entry-plus-install-function pattern (naming both `scripts/lib/catalog.sh` and `scripts/lib/install-steps.sh` explicitly), and adding a note that the new coverage-check script (R3) is how compliance gets verified rather than manual review alone. Version bump: MINOR (clarifying/extending existing principle text to match reality, not redefining or removing a principle), per the constitution's own semantic-versioning rule in its Governance section. A Sync Impact Report comment block is added at the top of the file, matching the style already used for the 1.0.0 → 1.1.0 bump.

**Alternatives considered**: A MAJOR bump — rejected, this doesn't redefine what artifact coherence *means*, only updates which concrete files satisfy it, which is exactly the kind of change the constitution's own versioning rule reserves for MINOR.

## R7: Attribution / Merge Mechanics

**Decision**: Complete this work directly on `pr-96-review` (local branch tracking `refs/pull/96/head`), then push the result to `calcuttin:feat/installer-tui-refactor`. Confirmed via `gh pr view 96` that `maintainerCanModify: true` — the contributor explicitly enabled maintainer edits, so this is both technically possible and clearly welcomed by them. This updates PR #96 in place rather than opening a new, competing PR, preserving the contributor's own commit and its authorship in the final history regardless of who pushes follow-up commits after it.

**Fallback** (only if the push is rejected for a reason not visible from `maintainerCanModify`, e.g. branch protection on their fork): open a new PR that includes their original commit (via merge, not squash-and-reattribute) with an explicit comment on PR #96 crediting them and linking to the superseding PR, then close #96. Discussed and pre-approved by the operator; not expected to be needed.

## macOS keyboard follow-up (2026-10-09)

On the host's `/bin/bash` 3.2.57, `read -t 0.05` reports an invalid timeout.
A pseudo-terminal reproduction sends Down to `tui_menu`: the tail read fails,
returns `esc`, and the menu aborts. `select_runtime` then swallows that failure
with `|| return 0`, continuing with OpenClaw. This matches the reported symptom;
Greg's exact terminal and keystroke stream have not been tested.

Use an integer one-second bound for escape-sequence tails, supported by Bash
3.2 and modern Bash. Preserve the first blocking character read, propagate its
failure, recognize both arrow encodings, and cancel instead of accepting a
runtime on failure. A standalone Escape can take up to one second to resolve.

## Python prerequisites follow-up (2026-10-09)

The supplied log explicitly shows pyATS failing because uv is missing. The
shared helper creates component venvs from NETCLAW_PY (default: python3),
then reuses existing runtimes solely on executable/pip availability. The
prerequisite check does not validate Python version or require uv for the
staged pyATS/GAIT installers. Apple Python 3.9 is available on this host;
Greg's exact Python version remains unconfirmed.

PyPI metadata for fastmcp 4.0.11 and mcp 2.3.0 declares Python >=3.10:
https://pypi.org/pypi/fastmcp/4.0.11/json and
https://pypi.org/pypi/mcp/2.3.0/json. These pins are compatible with each
other's Python minimum; removing constraints would not repair Python 3.9.

Use Python 3.12 as operator guidance, matching pyATS' default. Existing
automatic environments with unsupported Python must not be reused after
changing NETCLAW_PY; use a separate version-suffixed target, with the same
ownership checks and success-only interpreter records.

## Received full-log evidence (2026-10-09)

104 actual logs: 42 contain ResolutionImpossible, 11 contain old-pip editable
installation errors, five report no matching distribution, and two staged
runtimes fail for missing uv. These are message counts, not 104 failures or
proof that every error is exclusively Python-related. The supplied version
output confirms Python 3.9.6. pip 21.2.4 predates PEP 660 editable support
added in pip 21.3 (https://pip.pypa.io/en/stable/news/#v21-3).

Additional direct defects: gtrace uses grep -P (rejected by macOS grep), ignores
failed sudo binary placement, and logs success; claw-certs lacks cryptography
and calls undefined log_success; multivendor requires virtualenv and hardcodes
/usr/bin/python3; dedicated ANTA/source environments can retain old Python on
retry. Canonical `.venv/bin/python` templates currently ignore runtime records,
so recovery must update binding for those known templates while retaining
custom command conflicts and unrelated transports.

The archive also warns of absent Docker, kubectl, Ollama, tshark/capinfos,
Graphviz, browser provisioning and production guards. Computer Use is explicitly
a Linux virtual desktop. These external prerequisites need operator setup
or selection changes; do not misclassify them as Python resolver bugs.

## Second archive and preflight design (2026-10-09)

Zabbix's requirements contain ./vendor/zabbix-mcp-server. pip resolves that
against cwd, not the requirements file's parent. Removing the former cd in
PR285 introduced the failure; offline pip parsing reproduces it and resolves
the vendored directory when run from zabbix-mcp.

Forward's quoted message comes from command -v go failing. Upstream requires
Go 1.25 and CGO (https://github.com/forwardnetworks/forward-mcp#prerequisites).
Panorama explicitly requires >=3.10,<3.13. Zoom rtms 1.1.0 publishes cp310–cp313
wheels for darwin-arm64/linux-x86_64, with no cp314 wheel or source distribution.
https://pypi.org/project/rtms/1.1.0/ and
https://pypi.org/project/iflow-mcp-cdot65-palo-alto-mcp/.
Cisco's RADKit PyPI page directs users to https://radkit.cisco.com/pip; the
public index has only placeholder 1.99.1, not the pinned SDK 1.9.0. Preflight
must report the need for vendor sources instead of promising a Python-only fix.

Jev's archived error log is byte-identical to the first archive and predates
the retry. Interactive success does not replace a prior failure log. Separate
run directories prevent mixing these records. A read-only report cannot prove
package resolution, credentials or service connectivity; label its scope.

Use a JSON policy shared by the read-only checker and pip helper. Defaults
cover all catalog entries; explicit bounds/tools/platform rules override them.
Validate policy ids against the catalog and derive uvx/docker launcher needs
from tracked MCP registrations. Keep the checker stdlib-only and Bash helpers
compatible with Apple Bash 3.2. No package changes during offline tests.
