# Spec150 real Windows/WSL baseline

Observed 2026-10-10. **Baseline collected; extension implementation and acceptance NOT RUN.**
This is the read-only portion of T075 only. All 79 implementation/acceptance task
checkboxes remain unchecked, including T075. No E3/E8 or Q1–Q9 pass is claimed.

## Scope, source and target

The owner authorized the handoff's “Prompt to run now”: inspect the existing real
NetClaw/Risk, preserve its work and record prerequisites. No installation, upgrade,
restart, shutdown, configuration/client-registration change, provider request, extension
implementation or publication was performed. The only persistent writes were the new
source clone, private audit/baseline records and these handoff documents.

| Alias | Observation |
|---|---|
| `BASELINE_CHECKOUT` | Separate Linux-home clone `~/netclaw-spec150`, branch `150-vscode-extension`, starting at `1ffd5fb91a52dfba644a669ad6b4757d887cde1a`; initially clean, source VERSION 1.8.0 |
| `OWNER_SOURCE` | Existing `~/netclaw` checkout, also at `1ffd5fb` / VERSION 1.8.0; clean before/after; existing service working directories point here. This checkout was not switched, pulled or edited by this baseline |
| `OWNER_RUNTIME` | Existing OpenClaw home; default resolver selects OpenClaw, configuration present, legacy repository dotenv fallback reported. Owner credential values were never printed or copied |
| `OWNER_DISTRO` | Actual selected WSL2 distribution, Windows display label withheld. Its legacy name differs from its installed Ubuntu version; use observed `/etc/os-release`, not the label |
| `SECONDARY_HERMES` | Existing isolated Spec148 acceptance profile/HUD, source worktree at `3252977`, source VERSION 1.6.2. Preserved as a separate test installation, never substituted for the owner's Risk |

On-disk source version does **not** establish the code loaded by already-running
services. Owner HUD `/api/runtime` returned 404, while `/api/hud/runtime` and gateway
status returned older response shapes. The running daemon `/status` lacks spec149
installation/harness identity fields. Exact loaded backend source commit is therefore
**unverified**; do not call these processes qualified 1.8.0 services solely because
VERSION on disk says 1.8.0.

## Host and editor observations

| Item | Actual read-only observation | Qualification implication |
|---|---|---|
| Windows | Build 26300.9550, display version 26H2, OS API 10.0.26300; PowerShell 5.1.26100.9549 | Exact build recorded; not proof of all Windows releases |
| WSL | 3.0.1.0, kernel 6.18.40.1-1; WSLg 1.0.79 | Actual WSL2, not an environment-variable-only simulation |
| Linux | Ubuntu 26.04 LTS, x86_64, glibc 2.43 | Matches the 26.04 fixture family; Ubuntu 24.04 was not tested |
| Filesystem | `findmnt` reports ext4 for the separate checkout under Linux home | No runtime/source checkout created under `/mnt/c` |
| Distributions | One running owner distro; one stopped container-infrastructure distro | No second user NetClaw distro established; E8 remains unrun. Neither distro was started/stopped |
| Windows VS Code | Running Code process product/file version 1.140.0 | Above minimum 1.102.0; minimum-version and release-current test rows remain unrun |
| WSL support extension | `ms-vscode-remote.remote-wsl` 0.104.3 installed on Windows | Presence only, not Spec150 extension qualification |
| Actual remote host | Linux `/proc` shows an active VS Code `extensionHost`, executing from the WSL user's `.vscode-server` tree; server package 1.140.0, commit `07f806f999227108933c2e30515b26eecc1fda74` | Confirms an actual Linux extension-host process; Windows VS Code working-directory paths on some processes do not change executable/platform identity |
| Editor bundled Node | 24.21.0 | Separate from NetClaw/backend Node; do not substitute this for the service interpreter |

Desktop version was obtained from running Windows Code executables after the usual
unversioned package path was absent. Remote version was independently read from the
installed server package. No editor window/profile was opened or reconfigured.

## Existing runtime and Risk

| Read | Result | Limit |
|---|---|---|
| Owner HUD gateway status | HTTP 200, `online: true` | Service-reported connectivity, no chat/provider request or tool execution |
| Owner HUD runtime metadata | HTTP 200, `available: true` | Existing metadata available; does not implement the planned management contract |
| Risk overview | HTTP 200, role `border`, stacks `both`, 28 registered members, 4 reported active | Counts are daemon observations, not health/authority proof for every member; names, topology and addresses withheld |
| Daemon status | HTTP 200, `status: running`; legacy shape | No installation UUID/harness identity in response |
| New source's strict federation status | Exit 1: `foreign or legacy daemon: selected installation identity does not match` | Expected refusal against missing/unverified identity; no ownership file was created and no daemon restarted |
| Default HUD selection status | OpenClaw, config present, stable installation identity unavailable | Source inspection shows the CLI's `runtime_stopped` readiness default is not an OpenClaw liveness probe; actual gateway reports online. Do not present that placeholder as a stopped service |
| OpenClaw installed package | 2026.6.11 | Package metadata, not newly executed inference or version-qualified feature acceptance |
| Owner Node | 25.1.0, both default shell and running gateway/HUD executable | Outside specified backend range `>=24.19 <25` or `>=26.1`; no replacement performed |
| Owner Python | System Python 3.14.4; existing mesh process uses system interpreter | Required isolated federation Python 3.12 record not found in the owner's standard records directory; alternate private layouts were not exhaustively searched |
| uv | Default 0.6.14 | Existing version recorded; no toolchain update performed |
| Existing optional toolchain | Private Spec148 Node 24.19.0 executable is already present | Could be selected for later authorized development; owner service PATH was unchanged |
| Secondary Hermes | HTTP 200, selected Hermes v0.21.6, `ready: true`, historical `executionVerified: true`; companion Python 3.14.6; separate bridge/subnet records Python 3.12.10 | Existing Spec148 test instance only; no new execution qualification, no federation readiness inferred. Hermes CLI is absent from default PATH |
| Startup device inventory | Existing `pyats_list_devices` returned a diagnostic containing `Unsupported keys` / `arguments` | No device inventory/health pass. Protocol success wrapper is not semantic success; testbed not edited and no follow-up device operation performed |

The recent-task read returned **50 records: 39 completed, 4 submitted, 7 failed**,
with the same aggregate counts at the final read. This is a bounded recent list;
submitted tasks may be unresolved/stale, and this does not prove that all active work
has been enumerated. No task was cancelled, replayed or otherwise modified.

## Named clients and policy prerequisites

| Client | Observed version / presence | What remains unverified |
|---|---|---|
| Copilot | Built-in remote `GitHub.copilot-chat` 0.68.0 package and Copilot runtime process present | Account entitlement, effective organization policy, MCP tool consent, grant enforcement and real NL workflow |
| Claude Code | CLI 2.1.288; installed editor package directories 2.1.295 and 2.1.296 | Which editor package is activated, account/provider mode, effective policy and real NetClaw MCP workflow |
| Codex | CLI 0.162.1; remote `openai.chatgpt` 26.1007.21434 | Account/provider mode, effective policy and real NetClaw MCP workflow |

Both terminal clients' `mcp --help` commands exited 0, establishing command-surface
availability only. Existing client configurations were inspected for presence/counts,
not credentials or tool execution. No registrations were added or altered. The inspected
Windows VS Code policy registry keys were absent, and the remote Machine settings had
no matching `chat.mcp`/Copilot policy entries. This **does not establish permission**:
other settings scopes, organization policy, account entitlements and actual consent must
be tested later. No provider prompt or new external data-sharing boundary was exercised.

## Concrete implementation/acceptance prerequisites

1. **Implementation authorization:** the design remains unratified for implementation
   in these artifacts; this baseline does not supply that authorization. Once authorized,
   begin T001–T014 in the isolated checkout: pinned extension/server packages, strict
   schemas, installation/principal binding, propagated grants, durable journal/workers,
   independent approval validation, private façade and foundation denial/recovery tests.
2. **Missing product/backend:** the planned extension directory, operator/assistant
   launchers and shared management directory are absent in this checkout. No VSIX or
   management-contract-major-1 handshake exists. An existing HUD being online cannot
   satisfy the connection acceptance or justify registering its private APIs with agents.
3. **Qualified service baseline:** the running owner's legacy identity shape and Node25
   must be addressed through a separately authorized, planned owner update/test deployment.
   Capture exact process provenance and unresolved work first. Neither the extension nor
   this baseline may install/upgrade the backend. Do not silently initialize an identity
   to make a mismatched live daemon appear compatible.
4. **Spec149 T040:** actual Linux/WSL selected systemd lifecycle, ownership, Border-secret
   confinement, model-guard and populated rollback/mixed-runtime qualification remain open.
   Mac controlled-provider results and source unit text do not establish WSL enforcement.
   Production Hermes model-guard/confinement remains unavailable/fails closed per spec149;
   a running DefenseClaw/OpenShell process is not proof of this missing protection.
5. **Host/client matrix:** obtain an owner-designated second WSL test distro/installation
   for E8 and explicit disruption scope before any shutdown/restart test. Retain Ubuntu
   24.04, native Linux, Mac and Remote SSH/minimum-editor rows. Test actual named clients,
   both harnesses, scoped grant/disclosure, self-approval denial and uncertain recovery
   after the implementation exists. Presence/version checks above do not close these rows.
6. **Release prerequisites:** owner-selected publisher/extension ID and release authorization
   are not established here. Packaging, Q1–Q9, public listing/VSIX and Marketplace install
   remain future work; no publication should be inferred from prior spec-branch pushes.

## Preservation and evidence provenance

Before/after reads verified matching content hashes and modes for the sampled owner
OpenClaw dotenv/configuration and repository dotenv (three files). The global selection
descriptor was absent and remained absent. Twelve existing relevant user service records
retain their active/running states, main PIDs and start timestamps. Sixteen sampled
relevant process identities retain their PID/start-time pairs, including owner gateway,
HUD, mesh, guard/OpenShell, actual WSL extension host and secondary Hermes services.
The owner's source worktree remained clean. Normal runtime activity is not frozen;
no assertion is made that every log/database byte stayed constant.

Raw diagnostics, private path mapping and fingerprints remain only in
`~/.cache/netclaw-spec150-baseline/` with owner-private directory access. No environment
values, raw network topology, prompts, tokens or audit databases are committed.

- Private initial snapshot SHA-256: `2b9e8bf1c610143ea2658bfa0689ba8c90e06cc9a56e08a3c8fb8fda9ae2693a`
- Private final preservation report SHA-256: `599dd1ee07c1f3cb624b4ca47c2e73736508c77b7ba75bde08a1c553d3e6bd04`

Observed commands included Git status/revision and VERSION reads, `/proc` metadata,
`/etc/os-release`, `findmnt`, Windows registry/product-version reads, `wsl --version` /
`wsl --list --verbose`, package metadata, version/help-only CLI commands, `systemctl
--user show` on existing services, the inspected `hud-launch.mjs status` and
`federation-control.py status`, and GET-only existing HUD/Risk status/recent-task endpoints.
Raw responses were reduced to allowlisted fields/counts before writing public evidence.

GAIT session: `spec150-wsl-baseline-20261010`; startup record `5448b345`.
Native MemPalace/pyATS connector tools were unavailable. Existing local GAIT was used;
pyATS inventory used the existing component launcher and its unsuccessful result is
recorded above. Session-end record and log are retained locally. No ticket, external
message, provider request or device configuration change was made.

Session-end GAIT record: `afea2b1d`. Full inherited GAIT log is
retained privately in `~/.cache/netclaw-spec150-baseline/gait-log-private.json`.
Spec artifact check passed: 134 specs, four existing legacy exceptions; whitespace
check passed. No implementation test or live-extension result is implied.
