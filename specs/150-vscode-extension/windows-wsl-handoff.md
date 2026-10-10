# Windows / WSL handoff — Spec 150

Owner requested this handoff on 2026-10-10 for an **existing real NetClaw on their Windows/WSL machine**. Branch: `150-vscode-extension`, based on spec149 source commit `d332344d5a039e5ee0f2a2202c556ba28e2af206`. All Spec150 changes at this handoff are SDD documentation; no VSIX, extension implementation, new MCP launcher or Marketplace release exists yet.

## Transfer safely

In a WSL terminal, use a separate source checkout so the running installation and its files are preserved. For a new directory, this is sufficient:

```bash
git clone --branch 150-vscode-extension https://github.com/automateyournetwork/netclaw.git ~/netclaw-spec150
cd ~/netclaw-spec150
git status --short --branch
git log -1 --oneline
```

If the directory already exists, do not overwrite it. Inspect its work first and use a clean worktree or another directory. Do not switch/reset/pull the actively running installation blindly. For a previously cloned source repo, fetch and inspect `origin/150-vscode-extension`, then create an isolated worktree. The pushed branch includes its spec149 base; do not cherry-pick only these docs onto an older incompatible base. No `.env`, credentials, live GAIT history or private runtime state should be transferred through Git.

## Prompt to run now

Copy this into Codex or Claude Code in the separate WSL checkout:

```text
Continue NetClaw Spec 150 (150-vscode-extension) on my real Windows/WSL machine.
Read AGENTS.md, SOUL.md, USER.md, TOOLS.md, the current daily memory and
specs/150-vscode-extension/{spec.md,plan.md,tasks.md,windows-wsl-handoff.md},
plus contracts/qualification.md. Follow GAIT startup/record/end requirements.

This handoff authorizes a read-only baseline of my EXISTING NetClaw/Risk in WSL
and completion of the WSL handoff documentation. It does not authorize runtime
installation, upgrades, restarts, shutdowns, provider requests, configuration
changes, extension implementation or publication. Preserve the running install,
credentials, saved investigations and active work. Use a separate source checkout.

Verify the Windows build, WSL version, selected distribution and its Linux
version/architecture, VS Code desktop version and actual WSL extension-host
location. Identify the existing NetClaw path, source/version, selected harness,
runtime versions, standalone/Risk role and supported read-only status. Ask only
if the intended installation cannot be identified unambiguously. Inspect the
actual CLI/status implementation before choosing commands; do not assume the
planned Spec150 launchers exist. Do not print or copy .env values or credentials.

Compare observed state with spec150 requirements and spec149's outstanding
Linux/WSL qualification. Record sanitized facts and explicit blocked/unrun items
in specs/150-vscode-extension/evidence/wsl-baseline.md. Distinguish real host
observations from source-only conclusions. The VS Code extension is not yet
implemented: do not claim WSL extension acceptance. Review the spec/design and
report the next implementation/qualification steps and any concrete blockers.
Do not mark implementation tasks complete from this baseline. End with GAIT log.
```

## Real baseline evidence required now

| Evidence | Required observation |
|---|---|
| Source | Handoff branch/commit and installed NetClaw source/version separately; worktree cleanliness and no changes to running source. |
| Host | Actual Windows build, WSL2 version, selected distribution name (redact privately identifying names in Git), distro/version/architecture, filesystem type and extension-host context. |
| Runtime | Verified selected OpenClaw/Hermes and installed version; Node and isolated Python runtimes, installed management contract if any, exact missing prerequisites. |
| Installation | Stable identity availability, nonsecret path alias, standalone/Border/member role and permitted read-only service status; no guessed “healthy” state. |
| Clients | Installed VS Code/WSL extension, Copilot/Claude Code/Codex versions and MCP support/policy availability; no automatic registration or credential extraction. |
| Preservation | Owner services/active work before and after read-only inspection, with no restart/stop/shutdown or hidden upgrade. |
| Limitations | Spec149 production guard/confinement and broader tool gaps retained; no Mac qualification represented as WSL evidence. |

Public Git evidence contains sanitized versions, result summaries and digests. Raw private hostnames, addresses, network topology, prompts, tokens, configs and audit databases remain local. If a required read is denied, record that result and continue independent observations.

## Later prompt — only after implementation and test scope are authorized

```text
Run Spec150's real Windows/WSL extension acceptance against the implemented
candidate, following specs/150-vscode-extension/contracts/qualification.md.
First verify the implementation, VSIX digest, installed backend contract and
owner-designated test installation/distribution; stop dependent checks if absent.
Use the read-only baseline as evidence, not as an extension pass. Complete E3/E8,
the WSL runtime/client matrix and Q1-Q9 as applicable. Exercise the actual VS Code
desktop WSL extension host and real Copilot, Claude Code and Codex clients with
OpenClaw/Hermes targets. Record named-client versions and provider mode.
Before disruptive restart/shutdown or any write, prepare the exact test target,
active-work impact, baseline/recovery and applicable approval; obtain any missing
authorization. Never interrupt unrelated owner workloads. Prove distro/target
isolation, denial/self-approval, revocation, secret redaction, durable reconnect,
no uncertain replay and extension uninstall preserving backend services/state.
Record sanitized evidence and mark only actually passed tasks complete. Leave
unsupported, blocked and unrun checks explicit. Do not publish to Marketplace
without release authorization. End with a clear result and GAIT log.
```

WSL qualification is mandatory before release. This handoff is not a waiver. Complete `evidence/wsl-acceptance.md` after actual extension tests; link failures and spec149 dependencies. A separate explicit implementation instruction ratifies the reviewed design; this handoff alone does not.


## WSL read-only baseline collected

The 2026-10-10 owner-host observations and prerequisites are recorded in
[evidence/wsl-baseline.md](evidence/wsl-baseline.md). The running installation was preserved.
Implementation and all extension/client/fault acceptance remain pending; T075 is unchecked.
Use that baseline before preparing any separately authorized runtime or acceptance work.
