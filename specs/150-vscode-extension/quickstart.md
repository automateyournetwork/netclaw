# Quickstart and acceptance walkthrough

This describes the intended product and future validation. The extension and management launchers are not implemented by this specification change. For the existing Windows machine now, use the [WSL handoff](windows-wsl-handoff.md).

## Intended user workflow

1. Install **NetClaw** from its verified Marketplace listing or matching release VSIX. No listing/publisher is claimed yet. Use desktop VS Code; Windows+WSL users open the intended WSL distribution through the WSL extension. Remote users open their existing SSH host or choose an explicit SSH profile.
2. Choose **NetClaw: Add Connection** and the existing installation path/approved SSH alias. Confirm verified host, installation UUID, harness, role and capabilities. Missing backend management components produce setup/upgrade guidance; the extension does not install them.
3. Inspect Overview and Risk. Open Chat, send a qualified read-only request and follow its owned operation. Add selected editor context only after reviewing destination/content. Reload and recover the same operation without resend.
4. Open Settings, change a supported nonsecret field, review the redacted difference and restart impact, satisfy applicable approval and verify actual state. In a controlled fixture, prove a second window's stale revision is refused. Secret keep/replace/clear is tested with synthetic values.
5. Browse GAIT, Tokenomics, MCP/skills, topology, logs, RAG/memory, Science Officer and mobile views. Exercise each supported domain from the coverage contract; preserve unsupported runtime distinctions.
6. Choose **NetClaw: Configure Assistant**, select Copilot/Claude Code/Codex and review installation, action scope, expiry and model-provider disclosure. Approve only that client configuration/grant. Ask “Which Claws and harnesses are in this Risk?” and submit a qualified subnet request. Ask for a managed-change proposal; inspect it in Operations. The assistant cannot approve/apply it itself.
7. Disconnect/revoke the client and verify subsequent calls fail. Close VS Code and confirm a separately configured terminal client can still use its valid grant. Confirm independent NetClaw services remain running after extension disable/uninstall.

## Developer/qualifier sequence after ratification

- Follow [tasks.md](tasks.md); do not treat these future command names as runnable source today. Build scripts and exact pinned test commands must be recorded in the new extension README/package metadata during implementation.
- Foundation checks first: schemas, authenticated binding, permission attenuation, actual change-control checks, durable journal/deduplication and private redaction. Use synthetic installations for destructive fault simulation and never infer lab status from address/name.
- Run each story's independent test and the full [qualification matrix](contracts/qualification.md), including real named clients and the owner's Windows/WSL gate. Actual installation paths and credentials remain local.
- Record all failures/unrun checks with scope. Do not replace missing supported workflows with disabled controls, simulator passes, Mac-only results or a packaged VSIX.
- Complete catalog/documentation/skill/HUD coherence, package/privacy scan, compatibility/update checks and authorized public installation evidence. Only complete tested tasks; no claim of published availability until the public listing and install are observed.
