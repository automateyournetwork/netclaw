---
name: netclaw-install
description: Plan a new independent NetClaw or mixed OpenClaw/Hermes Risk through the NetClaw setup tools in VS Code. Use for guided installation, deployment intent, or a deployment Spec Kit workflow. Never applies an installation from chat.
---

# NetClaw installation

Use `netclaw_setup_observe` and `netclaw_setup_catalog` before proposing choices. This is an end-user deployment workflow, separate from NetClaw's development Spec Kit and operational network skills. Catalog availability is not installation or runtime readiness evidence.

If an existing NetClaw is detected, clearly say: “Existing NetClaw detected. This setup creates a separate installation.” Offer management through Connections or a separate new, empty home. Never adopt, update, borrow credentials from, or overwrite the existing home. Each claw needs its own identity, home, workspace, provider references, ports, service name and connection. OpenClaw has a workspace below its home; Hermes uses its home as its native workspace.

Ask concise questions in this order, skipping only choices the human has explicitly supplied:

1. Host and prerequisites. Native Windows must reopen an explicitly chosen supported WSL2 Ubuntu distribution. Do not enable features, elevate, reboot or install a distribution. Unsupported/unknown hosts remain blocked.
2. Source. The human selects and reviews the release, main, tag or existing checkout in native setup. Do not submit an arbitrary executable source through a draft.
3. Harness, local/cloud provider, exact model and API mode per claw. Query installed local models through the native wizard. Never download, load or infer merely to discover a model. Unknown transfer size means use the runtime model manager to review and approve separately, then refresh.
4. Open **Comms** and select one or more conversation channels, or explicitly None. Query `netclaw_setup_catalog` with kind `comms` and the selected harness: the two runtimes have different channels, native IDs, dependency requirements and version limits. Explain prerequisites and outstanding setup before selection. Members have no independent conversation channels. Twilio native SMS, runtime voice, NetClaw API/Voice MCPs and Zoom meeting integration are separate choices.
5. Focused or Risk. Explain that a Risk has one routing Border and independently installed members. Use Shape Advisor as advice only. Members inherit the Border harness unless explicitly overridden. Respect the catalog's member profiles and distinguish installer capability selection from operational qualification. Explicitly separate credential trust domains.
6. Components and independent skills for every claw, using canonical IDs and their dependencies. The Comms member profile allows explicit Twilio/Zoom component selection with independent credentials. Full bundles remain restricted to Focused/member claws; same-plan Zoom bindings connect their owned service to the Border's loopback bridge. Explain native setup requirements and external/no-install entries. Never invent a component, skill or supported interface.
7. Classified settings. Secret settings contain only `{kind:"secret",key,owner,source:"prompt"}` references. Never ask for a credential in chat, paste one into a plan, return one in a tool, or reuse another claw's key. `netclaw_setup_secret_entry` opens the native password UI and returns presence only.
8. Optional reviewed inventory and identity files. File selection and contents remain in native setup; tool responses do not expose them.
9. Testing or production posture. Production fails closed when any mandatory host/claw control is missing, unsupported or unverified. Never silently switch to testing. A checkbox or installed binary does not prove enforcement.
10. Verification. Tiers 1–3 are required. Keep per-channel configuration, authentication, connection, inbound and outbound evidence separate. Configuration or accepted submission does not prove delivery. Optional channel requests bind the selected owner, channel, direction and native destination reference; never put a real destination into assistant context. Every send needs exact native destination/content review, and an unknown send never replays automatically. Live model turns, external messages and device checks need separate native consent. Questions authorize no network writes. A discovered tool is not a successful model turn.

Channel and tool preparation instructions are in `docs/COMMS-SETUP.md`. Guided secure forms, QR/login terminals and manual provider prerequisites stay bound to the selected installation. Never request a complete `.env` export, substitute another runtime's credentials, weaken allowlists, start a tunnel, send an introduction or enable meeting capture to make an installer report look ready. Missing adapters/accounts remain explicit incomplete outcomes.

For intent, record explicit assumptions and unresolved decisions in the draft. Missing choices remain missing; don't fill a provider, model, home, channel, posture or production permission silently. Submit via `netclaw_setup_draft`; use the returned planRef/hash for validation and explanation. Tool input objects are closed; do not attach shell commands, approvals, arbitrary file instructions or secret values. Draft success never means apply-ready.

After validation, summarize the exact effects and outstanding limitations. Call `netclaw_setup_review` with the current hash to stage the plan in the visible editor. The human uses **Review installation** there. This tool does not apply, approve, resume or clean up. Client auto-approval settings do not replace native human review. Do not invoke an installer in a terminal as a workaround.

Observe status using `netclaw_setup_status`. Closing/reloading the editor pauses at a safe checkpoint; a surviving writer or lost outcome remains unknown until observed. Resume belongs to the human's native workflow. Existing services and independently started CLI installations continue independently. Use the redacted Claw Report; detailed local export requires a separate human review and is never sent automatically.

Without the visible editor/broker, explain how to reopen NetClaw setup. You may describe documented CLI validation commands for the human to run, but do not execute installation or fabricate approval evidence. This tool boundary is not a sandbox for a client's unrelated unrestricted terminal access.

Starter intents:

- “Help me choose a separate Focused claw for subnet calculations; ask for missing host, provider, model and posture choices.”
- “Plan a Risk with an OpenClaw Border, one inherited OpenClaw member and one explicit Hermes subnet member. Keep provider credentials independent.”
- “Plan production and show exactly which controls remain unverified; do not downgrade it.”
- “Reopen my paused run and show its state; let me resume in the editor.”
- “Create a deployment Spec Kit workspace, then specify, clarify, plan, task and analyze before staging native review.”

Contradictory intents stay unresolved: two harnesses for one claw require a choice; a reused home requires a separate empty home or the existing-management workflow; production without verified controls stays blocked. “Install everything” does not supply missing provider/model, channel, posture or credential decisions. The repository's `docs/INTENT-PROMPTS.md` provides the shared examples and `tests/fixtures/setup/intent-matrix.json` records expected draft behavior. Those protocol fixtures do not certify an assistant's natural-language interpretation.

The deployment Spec Kit **implement** step means submitting the exact canonical plan for human review and recording the resulting typed report. It never means running unattended installer commands.

### pyATS inventory selection (Spec160)

For each selected pyATS claw, ask static or dynamic and select sources using the
canonical `config/pyats-testbed-sources.json`. Store optional `claw.testbed` with
`mode` and `sources`; absence means static compatibility. Dynamic requires at least
one source and cannot coexist with that owner's top-level static inventory import.
Never put credentials or source records into a Claw Plan. Installation configures
the policy only; source MCP access, composition, validation and explicit activation
are later operations. No empty YAML is needed in dynamic mode. Explain source gaps
and session lifetime from `docs/DYNAMIC-TESTBEDS.md`; never infer SSH from consoles
or claim fixture qualification as live access. HUD static inventory is separate.

## GCP deployment

If the user wants a Border or Member in Google Cloud, point them to `docs/NETCLAW-IN-GCP.md`. State first that GCP deployments are
NOT behind any authentication and URLs must stay private (users, SSO and RBAC are R15-R17). Prepare, but do not run on the
user's behalf, `python3 scripts/netclaw-gcp.py plan ...`. Never supply `--ack-no-auth`, `--confirm-cost` or `--confirm-list-sha256`.
