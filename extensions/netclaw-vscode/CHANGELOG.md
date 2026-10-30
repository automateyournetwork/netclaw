# Changelog

## 1.5.0 — optional NetConverter setup (source; unpublished)

- Choose hosted-readonly or local-Terminal mode in the native setup picker, with preserved cancellation and independent per-claw settings.
- Reject API-key literals in non-secret plan fields; installation, account capability and per-file approval remain separate states.
- Use matching source 1.15.0. Controlled installer tests pass; native desktop acceptance, real account/client discovery and live conversion remain pending in Spec162.

## 1.4.0 — dynamic pyATS testbeds

- Choose Static or Dynamic per claw, then select from 14 source routes in native installer prompts. Cancel, reload and neighboring member choices remain independent.
- Show inventory policy in exact plan review; dynamic setup creates no placeholder YAML and does not fetch, activate or connect to devices.
- Label the existing Testbed editor as static inventory, separate from process-local dynamic candidates.
- Dynamic setup requires source 1.14.0; see Spec160 verification for actual Mac and synthetic-source acceptance. Existing runtime upgrades remain explicit.

## 1.3.1 — minor setup fix

- Include the optional MCP-default catalog and resolver in exact source review inputs (Spec 156 / issue #262).
- Use source 1.13.1 for the coordinated MCP-default and Hermes recovery fixes in Specs 156–159. Existing runtime upgrades remain explicit.

## 1.3.0 — guided Comms setup

- Search all 77 documented runtime-specific Comms entries, including WhatsApp, Teams, Discord, Slack, Webex dispositions, Twilio and Zoom.
- Select multiple channels with private native settings, restrictive access and retained choices across cancellation/reload. Keep Border ingress and Focused/member tools separate.
- Add pinned acquisition, native readback/discovery, owned-service checks and explicit configuration/authentication/transport/delivery evidence.
- Require source 1.13.0+ and VS Code 1.109+. Existing runtime homes are unchanged by the extension upgrade.
- Mac installer acceptance passed within recorded fixture boundaries. WSL remains partial, with six service-manager failures and the genuine remote-editor gate open; provider readiness is unverified. See Spec155 release verification.

## 1.2.0 — reviewed new-claw setup

- Add **Set Up a New NetClaw** without an existing HUD: bootstrap a reviewed source, choose a Focused claw or mixed OpenClaw/Hermes Risk, and use new empty homes.
- Review the exact plan natively, keep per-claw credentials private, pause safely and resume explicitly. Save a connection only after authenticated installation readiness.
- Add assistant-guided drafting, deployment Spec Kit, structurally redacted reports and ownership-checked cleanup.
- Require VS Code 1.109+ and source setup engine 1.12.0+. Existing installations remain independent; extension upgrades do not upgrade runtime homes.
- Mac installer acceptance passed, including three fresh-home return scenarios. Windows/WSL qualification is partial; see Spec153 release verification for exact evidence.

## 1.1.0 — workspace files and claw controls

- Add top-panel access to six native workspace Markdown files for OpenClaw and Hermes, with read, reviewed save and exact UTF-8 upload/overwrite; no delete/rename.
- Use the native VS Code document editor for keyboard behavior, Undo and dirty-close protection. Preserve original recovery copies and reject stale revisions.
- Add installation-bound Start/Stop/Restart with durable offline recovery, exact owned-service/supervisor controls and private operation evidence. Unknown ownership disables full control.
- Add Save & Restart gated on verified saved bytes and the reviewed service scope. Keep saving, service readiness and prompt loading distinct.
- Requires source HUD/helper 1.11.0. WSL native-home resolution and systemd neighbor/environment discovery corrections are in the backing source. WSL regular-file reads and native editing/Undo are verified; symlink entries remain refused and live WSL lifecycle is unqualified. See Spec152 release verification.

## 1.0.1 — input and Testbed address hotfix

- Keep Testbed typing local to the webview, without per-keystroke host messages or persisted VS Code state. Bind Save to the reviewed draft revision and reject stale reviews.
- Exclude pyATS `connections.defaults` from endpoint choices, including responses from an already-running HUD. Edit displays the stored endpoint address; shared defaults remain preserved.
- Reject guided endpoint writes to the reserved `defaults` mapping. Advanced YAML continues to support shared settings.
- Add character-by-character editor tests across Testbed, MCP and security forms, endpoint variants, stale review rejection and saved-file readback. Windows VS Code 1.141.0 with a WSL extension host passed ten focused input workflows and all 18 experience checks / 149 layout cases. The reported one-character failure was traced to still-loaded 0.1.1 code despite 1.0.0 being installed; reload the window after installing the update.

## 1.0.0 — button hotfix

- Bring Testbed Edit/Add forms and YAML/review panels into view, then focus an enabled field. Existing-device edits no longer appear to do nothing beneath a long device list.
- Keep keyboard focus while typing, retain the selected connection in saved drafts, prevent overlapping actions, and explain when no recovery copies exist.
- Reveal security reviews, invalidate the old visible review when editing a different rule, and keep MCP Reload available after metadata errors.
- Serialize Chat and Canvas actions, recover Canvas Send after a failed admission or interrupted request, and prevent delayed responses from enabling disconnected views.
- Add existing-device edit/save/cancel/preservation and button-recovery regression coverage. No HUD upgrade is required for this hotfix beyond the existing full-editor prerequisites.

## 0.1.1 — release candidate

- Restore testbed details and MCP configuration access with older running HUDs. Safe editing uses the updated HUD; legacy environment changes retain native review.
- Show native security ACLs, tool scopes, filesystem/process permissions and redacted YAML. Support actual DefenseClaw 0.8.4 connector commands and OpenShell 0.0.32 YAML policy commands.
- Preserve policy fields, refuse stale or unknown outcomes, and qualify native changes against isolated real targets.
- Include the topology renderer and its license notice in the VSIX; packaging now checks every emitted runtime asset.


## 0.1.0 — release candidate

Initial extension client for existing NetClaw: host-bound profiles, HUD observations,
Chat/Canvas/local Avatar, integrated RAG, reviewed environment/budget settings,
existing Intent/peer chat, prepared service commands and opt-in assistant MCP.
Uses unchanged NetClaw interfaces. Publication is on hold by the owner.

WSL qualification fix: restore Chat, Canvas, RAG and observation views after
switching tabs by retaining their message sequence across webview reloads.
Installation binding and replay checks remain enforced.

Windows local hosts now show explicit WSL guidance and filter the command palette
to WSL commands before any connection can be added.

Mac qualification fix: RAG controls show an operation in progress and prevent
overlapping submissions while collections refresh, retrieval runs or native
review is open. Controls recover on completion/cancellation/error and remain
disabled after disconnection. No operation is automatically replayed.
