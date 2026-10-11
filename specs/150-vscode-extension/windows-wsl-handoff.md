# Windows/WSL development and qualification handoff

Updated 2026-10-10 after the owner authorized implementation, chose a WSL handoff
and chose local authentication for eventual Marketplace publishing. The earlier
read-only baseline prompt is superseded by this development handoff. Its actual
observations remain unchanged in [wsl-baseline.md](evidence/wsl-baseline.md), from
commit `aa2795313b487e00ccbe85d53f6a78db07b10a94`.

## What is ready to transfer

Branch: **`150-vscode-extension-implementation`**. First implementation checkpoint:
`9b4a0ffcda18eaf750d3befa85f5e1387cd25616`; use the latest pushed tip and record it.
This is a development candidate, not a completed extension or a release approval.
Only five of 79 tasks are checked. The remaining tasks include implementation as
well as actual platform/client acceptance. The original `150-vscode-extension`
branch and the running Mac checkout were preserved.

The candidate includes private management MCP, durable operator conversations,
Chat/Canvas/local Avatar, environment proposals and a dedicated integrated RAG
panel. RAG uses the existing backend store, supports reviewed uploads and cited
retrieval, and supplies deliberately selected Chat/Canvas context. Actual Mac
process/editor evidence is in [mac-development.md](evidence/mac-development.md).
Assistant delegation is deliberately refused until its permission propagation is
implemented and qualified. Remaining domains must not be passed by labeling them
unavailable.

## Get the source without touching running services

In WSL, use a new directory. Do not run this over an existing checkout:

```bash
git clone --branch 150-vscode-extension-implementation https://github.com/automateyournetwork/netclaw.git ~/netclaw150-wsl
cd ~/netclaw150-wsl
git status --short --branch
git log -1 --oneline
git merge-base --is-ancestor aa2795313b487e00ccbe85d53f6a78db07b10a94 HEAD
```

If that path exists, inspect and preserve it; choose another unused checkout or a
separate worktree. Never reset or switch the source beneath running NetClaw
services. Private runtime homes, `.env`, credential stores, audit databases and
real network evidence stay on their existing host and out of Git.

## Prompt to run in the WSL coding agent

```text
Continue NetClaw Spec150 on my Windows/WSL machine from the latest pushed
origin/150-vscode-extension-implementation in an isolated source checkout.
Confirm aa2795313b487e00ccbe85d53f6a78db07b10a94 is an ancestor. Preserve all
existing work and running services; use a new branch 150-vscode-extension-wsl
only if that branch name is not already in use.

Read AGENTS.md, SOUL.md, USER.md, TOOLS.md, the constitution and daily memory.
Follow GAIT startup, recording and session-end requirements. Read:
- specs/150-vscode-extension/{spec.md,plan.md,tasks.md}
- specs/150-vscode-extension/{implementation-readiness.md,windows-wsl-handoff.md}
- specs/150-vscode-extension/evidence/{wsl-baseline.md,mac-development.md}
- specs/150-vscode-extension/contracts/{operator-mcp.md,assistant-mcp.md,editor.md,qualification.md}
- docs/VSCODE-PUBLISHING.md
Use the established SDD implementation and analysis process.

The owner authorized implementation and qualification. This is a partially
implemented development candidate, not a full release: five of 79 tasks were
checked at the Mac checkpoint. Continue the remaining implementation and fix
actual failures; do not limit this to rendering controls or a baseline review.
RAG must remain a dedicated panel with existing-store collections, reviewed
upload, indexing state, citations and explicit Chat/Canvas context selection.
Do not register unrestricted operator tools with Copilot or terminal agents.
Keep assistant delegation unavailable until runtime and per-hop grants are
actually enforced and tested; assistants cannot approve their own changes.

First re-observe Windows, WSL distribution, actual VS Code extension-host
location, existing installations and active work. Keep Mac and WSL evidence
separate. The earlier owner baseline found Node25.1 unsupported, missing live
stable installation identity/management components, older loaded service
shapes and outstanding Spec149 Linux/WSL qualification. Verify rather than
assuming these conditions still hold. The extension must not install, upgrade
or initialize its backend. Prepare concrete prerequisite changes through the
normal backend workflow; apply only within the established authorization and
change-control scope. Ask only when the intended target or necessary authority
is genuinely missing. Never replace credentials, restart unrelated services,
replay uncertain work or turn a legacy daemon into a verified identity by fiat.

Use isolated supported Node (24.19–24.x or26.1+), Python3.12 federation/MCP and
pinned Python3.14 Hermes environments. Install locked development dependencies
only in the isolated checkout. Build/test the candidate there, then exercise
actual Windows desktop VS Code connected to the intended WSL distro. Complete
E3/E8 and applicable runtime/client/fault gates, including real Copilot, Claude
Code and Codex workflows and a separately designated second distribution.
Never infer live tool execution from an advertised integration or a mock result.
Production network writes still require independently approved change control.

Record commands, exact versions, source/VSIX digests, observed outcomes and
remaining blocked/unrun checks in evidence/wsl-acceptance.md and the relevant
story evidence. Mark only fully completed tasks. Finish the required catalog,
installer, HUD, skills and documentation coherence. Commit and push reviewed
source and sanitized evidence on the WSL branch; transfer no secrets or private
runtime state. End with GAIT log and a precise Mac return prompt identifying the
pushed commit, artifact, remaining work and any missing release prerequisites.
Do not publish to Marketplace in this WSL phase: the owner will return the WSL
results to the Mac session for review and finalization.
```

## Reproducible development commands

After selecting supported Node explicitly for this shell, from the isolated
checkout (these commands do not initialize the owner's backend):

```bash
npm ci --ignore-scripts --prefix ui/netclaw-visual
npm ci --ignore-scripts --prefix mcp-servers/netclaw-operator-mcp
npm ci --ignore-scripts --prefix mcp-servers/netclaw-assistant-mcp
npm ci --ignore-scripts --prefix extensions/netclaw-vscode
node --test tests/operator/*.test.mjs tests/assistant-clients/*.test.mjs
npm --prefix extensions/netclaw-vscode run check
npm --prefix extensions/netclaw-vscode test
npm --prefix extensions/netclaw-vscode run build
npm --prefix extensions/netclaw-vscode run test:package
```

The four opt-in process tests require explicit isolated runtime paths; skips are
not passes. `tests/vscode/runner.mjs` tests the actual editor process it launches,
which on Linux is not evidence of Windows desktop's WSL remote extension host.
Actual E3/E8 observations must come from the Windows desktop application.

From a clean committed checkout, `npm --prefix extensions/netclaw-vscode run
package` produces `netclaw-0.1.0.vsix` and an ignored `out/package.json` containing
its source SHA and package SHA-256. Packaging pins Marketplace documentation/image
links to that commit and checks the exact file allowlist separately. ZIP timestamp
metadata can change a rebuilt artifact's digest; record the artifact actually
installed. Do not represent a development VSIX as published or release-qualified.

## Return to Mac

Push the WSL source/evidence branch, then return its exact commit and the summary
of `wsl-acceptance.md`. The Mac session should fetch that branch into an isolated
checkout, review all changes/evidence, finish remaining tasks and release checks,
then use the locally authenticated `NetClaw` publisher for the reviewed artifact.
The user's Microsoft/Marketplace credentials are never needed in chat. Public
completion still requires an observed Marketplace installation and connection.
