# User Profile

## About You

- **Name:** (your name here)
- **Role:** Network Engineer / Architect
- **Timezone:** (your timezone, e.g., America/New_York)

## Preferences

- **Communication style:** Technical, concise — include CLI output and protocol details
- **Report format:** Severity-sorted tables with HEALTHY / WARNING / CRITICAL ratings
- **Change management:** Production requires approved ServiceNow CRs. Explicitly opted-in Terminal Intent Local/Lab requests use scoped local approval and audit under AGENTS.md; lab mode is never assumed or enabled by default.
- **Escalation:** Notify immediately on P1/P2; queue P3/P4 for next business day

## Your Network

- **Testbed:** Defined in `testbed/testbed.yaml`
- **Platforms:** (list your platforms, e.g., IOS-XE, NX-OS, IOS-XR, ACI, F5)
- **Source of Truth:** NetBox (read-write)
- **ITSM:** ServiceNow

## Notes

- Spec153 handoff (2026-10-18): after the fixed Mac engineering gate passed, commit and push the completed source to the feature branch and provide an exact WSL continuation prompt. Windows is bounded smoke/platform-difference qualification, then return to Mac for regression, packaging readiness, recording and the owner walkthrough.

- Spec153 direction (2026-10-17): start a new branch and full Spec Kit cycle using the supplied IDE installer spec, plan and Codex kickoff. Ask five additional clarification questions before planning, then generate tasks, analyze and resolve every finding before implementing and testing. The current request supersedes the kickoff's G2 stop; real installations and publication remain outside scope.
- Spec153 clarification 1 (2026-10-17): a machine may already host claws. Detect and clearly identify them, explain that the new installation is separate, require a new empty runtime home, and support managing multiple claw installations on the same machine.
- Spec153 clarification 2 (2026-10-17): allow mixed OpenClaw/Hermes Risks. Choose the harness independently per claw; members inherit the Border's harness by default with explicit overrides where supported.
- Spec153 clarification 3 (2026-10-17): missing production controls must stop setup. Proceed only after verification or an explicit user choice of testing mode and fresh review of the revised plan; never automatically downgrade.
- Spec153 clarification 4 (2026-10-17): closing VS Code pauses its installation run at the next safe checkpoint; reopening offers explicit Resume. Abrupt termination requires observing unknown outcomes before retrying, without unattended continuation into later phases.
- Spec153 clarification 5 (2026-10-17): installation report exports redact hostnames, IP addresses, usernames and local paths by default; detailed local export requires explicit review. Both exclude secrets. All five clarifications complete; continue the authorized SDD process.
- Spec151 direction (2026-10-11): redesign the VS Code extension around automateyournetwork.com branding and responsive cards; preserve blue actions, filters and search. Add clear connection guidance, testbed CRUD/import and per-MCP environment/setup. Follow SDD with at least five clarification questions before plan/tasks/analyze/fixes/implementation. No packaging, pushing, live deployment or Marketplace/public release until explicitly requested.
- Spec151 theme choice (2026-10-11): automatically follow VS Code's light/dark theme with branded cards, typography and accents; preserve high-contrast accessibility.
- Spec151 testbed workflow (2026-10-11): device cards and guided forms plus an advanced YAML editor, with file import/export.
- Spec151 testbed formats (2026-10-11): YAML/YML and equivalent JSON, plus CSV for basic device inventory fields.
- Spec151 per-MCP setup (2026-10-11): include direct execution of supported installation, registration and restart actions after explicit confirmation, alongside configuration/help and reviewed command staging. Development and acceptance remain isolated; no live deployment is authorized.
- Spec151 visuals (2026-10-11): custom branded imagery plus purposeful interactive 3D, especially topology, with restrained motion elsewhere. All five clarification decisions are complete; continue the authorized SDD workflow through local implementation.

- (Add anything NetClaw should remember about you, your team, or your network here)
- (e.g., "R1 and R2 are in the lab — less strict change control needed")
- (e.g., "Always CC @oncall-noc in Slack for P1 alerts")

- Jev preference (2026-09-27): optional visible Science Officer, dynamically invented questions from human/member context, advice-only with read-only evidence; default $5/day and $0.25/task budgets adjustable by operator. Avoid static question libraries.
- HUD preference (2026-09-27): function over flash; preserve Adam's reusable context/chat canvas and add detailed Science Officer data views during the new HUD phase.

- Roadmap clarification (2026-09-27): spec126 is the small README refresh; HUD is127, preserving Adam's canvas. Phase4 scope is README plus a common utility to upgrade existing NetClaw installations to the latest build.

- HUD127 scope (2026-09-27): panel-first dashboards with Basic/Advanced presentation; Three.js where relationship/topology views help. Cover standalone, iN2N Risk of Claws, eN2N external neighbours, Jev Science Officer and mobile devices. Adam Mason's full context/chat canvas must survive, including existing saved work and investigation affordances.

- HUD refinement: name the preserved workspace Canvas; provide direct RAG uploads/retrieval and a masked configuration inventory in the menu.

- HUD additions: per-Claw MCP/LLM introspection, Tokenomics, Documentation and CLI/API references, direct Logs with filters/commands, Sean Mahoney's guide panel, and early LAB/production plus DefenseClaw/OpenShell views. README should lead with the new HUD rather than the old SSH migration callout. Keep Canvas and hold pushes for review.

- Release preference (2026-09-28): establish official NetClaw 1.0.0, then use 1.x.y versions as completed specs evolve the project; require numbered specs and Spec Kit artifacts for contributions/PRs. Feature specs use minor bumps, fixes/docs/maintenance use patches; source and mobile component versions remain independent.

- Chat preference (2026-09-28): standard back-and-forth Chat should be the default HUD interface, with Canvas still available and native OpenClaw as a third option opening in a separate tab (explicitly approved).

- Tavus exploration (2026-10-09): pursue a spec-driven NetClaw Pal assessment within Free only: 20 conversational minutes, stock faces and no paid upgrade. Spec 143 is abandoned; return to main before the new exploration.

- 2026-10-09: Authorized moving to spec branch 144 and starting Pal implementation. Interested in using a lobster or personal smiley image. Keep the Tavus experiment on Free; local browser icon supported, custom Tavus training excluded.

- Pal design clarification (2026-10-09, supersedes the initial Free-only product scope): Free default with optional custom face/voice on entitled accounts; each owner supplies their own key; full authorized NetClaw access through Border with existing approvals; optional downloadable John photo/voice pack; automatic non-sensitive summaries with private details local. No paid upgrade or provider training has been authorized. John then requested PNG conversion and recording guidance, questioned the paid custom-avatar limitation, and asked to explore local Blender and other services.
- Local Pal approved (2026-10-09): start with John and Lobster selectable local avatars. Existing configured frontier model produces the chat answer; local speech/animation presents it. Keep Blender MCP in the authoring path when connected. Prove the two-character formula before offering custom uploads or an external conversion script. Avatar left, Chat visible on the right, selection below; include move/pan, rotate, zoom and reset controls. Keep the same chat session when switching views or characters.
- Interface correction (2026-10-09): Avatar is the fourth Chat interface beside Chat, Canvas and OpenClaw, not a separate Pal sidebar tab.
- Spec151 security choice (2026-10-11): expose OpenShell and DefenseClaw allow/block rules, supported policies/enforcement modes, status and logs; require explicit acknowledgment for weakened protection. This addition does not include lifecycle start/stop/restart.
- Spec151 merge authorization (2026-10-11): commit all completed work, push the feature branch, create and merge its PR into main, then stop for further instructions. Packaging, deployment, release tags and Marketplace/GitHub release/blog publication remain held.
- Spec152 direction (2026-10-15): new focused VS Code feature/branch for the top-panel workspace files SOUL.md, AGENTS.md, IDENTITY.md, USER.md, TOOLS.md and HEARTBEAT.md. Read, edit/update and upload/overwrite; no deletion. Include restart after saving and direct Start/Stop/Restart. Confirmed both OpenClaw and Hermes using actual runtime workspaces, and full selected-installation lifecycle including its owned gateway/engine, HUD and federation services. Specification work does not authorize live deployment or publication.

- Spec152 implementation authorization (2026-10-15): proceed through planning, implementation and verification, then FIRST show an ephemeral isolated VS Code with the implemented build. Push/live deployment require later owner approval.

- Spec152 WSL handoff authorization (2026-10-15): package the implemented build, add a WSL handoff prompt, and push the feature branch so it can be pulled on the real NetClaw host. Launch an isolated patched VS Code there connected to the real installation for file inspection. This supersedes the earlier package/push hold; no merge or Marketplace publication was requested.

- Spec152 production authorization (2026-10-16): fetch the WSL follow-up, commit remaining work, create and merge the PR, remove completed feature branches, return to main and push to production. This explicitly supersedes the earlier merge/publication hold for this feature.

- Spec153 release authorization (2026-10-24): after three additional actual local Mac installer-only passes, merge the PR, publish source and VS Code extension, close completed work, delete completed Spec153 branches and return to main. Earlier publication holds are superseded. Do not retest operational capabilities or alter existing owner runtimes; retain actual partial Windows/WSL results.

- Spec155 direction (2026-10-25): investigate and complete IDE installer channel setup for the Border. Reference all documented channels supported by OpenClaw and Hermes separately, not only Slack/Teams/Discord/Webex examples; explicitly include Twilio SMS, existing NetClaw Twilio skills/MCPs and Zoom under visible Comms choices with correct Border/member ownership and distinct voice/meeting setup; preserve runtime/version distinctions, complete onboarding and actual readiness. This request authorizes investigation and a follow-up specification, not live channel operation or publication.

- Spec155 implementation authorization (2026-10-25): drive the Comms feature through SDD to completion, including planning, tasks, analysis, implementation and isolated installer verification. Inspect this Mac for existing Zoom setup material first; credential values remain local and absent from chat/artifacts. A full sandbox/WSL .env export is unnecessary. Existing runtimes and operational capabilities remain separate from installer testing.

- Spec155 source handoff authorization (2026-10-25): after resuming parallel implementation, the owner explicitly requested that all Spec155 source be pushed and a copyable WSL NetClaw qualification prompt be returned. Commit/push the feature branch with exact evidence; no merge, release/Marketplace publication or existing-runtime deployment is requested.

Spec160 release authorization (2026-10-30): the owner requested versioned source and touched-extension publication, README/community notes, commit/push/PR/merge, completed-branch cleanup and return to main. Earlier Spec160 source-only publication holds are superseded. The two-part modern_website writeup remains staged as drafts; no website deployment or existing-runtime upgrade is requested. Preserve all recorded qualification limits.

- Issue310 roadmap direction (2026-11-01): assess the supplied 20-brief roadmap and ask questions FIRST, before creating any spec. First operational milestone is a GCP Border directing local member claws. Follow one brief per Spec Kit cycle, retain evidence qualification boundaries, stop after each brief for "next", provide major milestone updates with verified live URLs and draft writeups. Bounded Ralph implementation loops may be used if useful. The driver reserves cloud/spend mutations, ngrok account/endpoint changes, IdP registrations and device operations outside the approved read set for explicit human action/review; access availability does not waive these gates.

- Issue310 initial choices (2026-11-01): use the existing GCP project identified in assessment, described by the owner as having $1,000 in credit budget (remaining credit, expiry and applicability still to verify). Three new local claws: pyATS/SSH against local CML devices and a separate CML API member, both using latest Sonnet; an Ollama member for the IPv4 subnet calculator. Keep the cloud Border control-only. Resolve and record the actual model ID during qualification. Owner supplied `lobsternet.autoamteyourntwork.com`; confirm spelling before DNS/certificate work, likely intended `lobsternet.automateyournetwork.com`. Use unique deployment names across providers/regions while keeping application identities independent of placement. Reusable installation and migration to/from clouds must be credential-agnostic for other users: parameterized role contracts, owner-supplied secret references, explicit identity move versus clone, fenced cutover, durable state and rollback verification. Assessment discussion continues; no spec started.

- Issue310 final opening clarification (2026-11-01, supersedes pending details above): owner confirmed `lobsternet.automateyournetwork.com`, Montréal and a 30-day initial trial. The roughly $1,000 credit was ONLY to identify the intended GCP account/project, not a spending cap or instruction to consume it. Use that selected project; do not repeatedly ask the same budget question. Proceed with R01 after the completed opening assessment, retaining the driver's concrete infrastructure approval gates and per-brief stop.

- R01 fresh-pilot direction (2026-11-01): owner said to start fresh with local/GCP participants and delegated the choice; do not ask for existing host references again. Root `.env` credential is named exactly `NGROK`. Preserve existing installations and source work. Prepare new isolated pilot participants for R01 qualification; retain the recorded exact cloud/endpoint/spend review boundary and stop within R01. Direct account API checks identified this value as an agent authtoken (ERR_NGROK_206); an API key remains a separate prerequisite.

### Spec168 direct-cloud pivot (2026-11-01)
John explicitly approved pivoting cloud Borders from mandatory ngrok to native
cloud TCP ingress. Preserve home/commercial-Internet Border ngrok configuration.
Cloud-friendly members may live in cloud; members needing local SSH/internal
systems stay on premises and dial outbound to their Border. Private/air-gapped
on-prem Border/member topology needs no ngrok; offline provisioning is separate.
Keep hybrid, multi-cloud and multi-region in the roadmap. Update README, setup.sh,
VS Code and all affected guidance consistently. Protocol distinction remains
member iN2N versus independent-Border NCFED/eN2N. Preserve R01 stop and exact
cloud/spend approval boundaries; do not ask for a paid ngrok plan for this pilot.

John also requested a working cloud HUD link and actual on-prem member-to-cloud
iN2N evidence. Include this in the R01 pilot, without treating it as completion
of R03 or model/device workload acceptance. The existing HUD is a trusted local
operator interface with SSH access, not a public authenticated application;
IAP/SSH access is the scoped pilot default unless John chooses a reviewed public
login gateway. Never label a planned URL or loopback fixture as live evidence.

R01 explicit execution decisions: John selected IAP HUD access, delegated the
exact11-resource foundation apply, then explicitly approved the budget-only
recovery after the quota-project403. Both approvals are consumed by those scoped
operations, not by later runtime activation or IP relocation. The runtime packet
is a separate pending review; record subsequent replies here before treating
future actions as authorized.

John subsequently explicitly authorized the reviewed R01 runtime packet, including
scoped pilot repairs/restarts: OS Login key, IAP/SSH, cloud-only secret/source
transfer, two owned services and fresh on-prem iN2N/NCFED qualification. This
supersedes the pending-runtime-review note above. No new public port, device/model
execution or later roadmap brief is authorized; exact IP-relocation/teardown
plans retain their separate review boundary.

Spec168 R01 access steering (2026-11-01): John superseded IAP-only viewing with
an open cloud HUD URL for lab testing, without login, then explicitly requested
DNS/certificates and fully delegated remaining R01 activation/relocation changes.
He corrected the two-view status-only narrowing: restore the full HUD, Chat,
Canvas, RAG and other views. He authorized his Anthropic key and Sonnet for the
cloud Border and scoped on-prem member, with actual question/answer evidence.
The member must be clearly named and its real capability shown; it is a fresh
Mac subnet-calculator, not an existing pyATS member. Users/SSO/RBAC remain R15–17.
No need to re-ask delegated R01 permission. No later brief, existing owner-runtime
upgrade, device changes, commit or publication is authorized.

## Roadmap source integration and release hold — 2026-11-02

The owner authorized committing, pushing and merging the completed R01 source into
main, with a short maintainer summary. This supersedes R01's earlier source-merge
hold only. The issue310 roadmap work remains unreleased until the entire roadmap
is complete, including user identities, SSO and RBAC (R15–R17) and closure (R20).
Do not bump a version, create a release/tag, publish a package/Marketplace build,
publish a blog/changelog/announcement, or promote general cloud deployment for
this work. R01 transport proof is not authorization to deploy a cloud Border
without user controls. Keep technical specs/evidence for maintainers; rollout
copy is deferred under specs/168-ngrok-transport-contract/deferred-docs/ and absent
from the public README, setup wizard and general installation guides. Existing
owner pilot authorization is a bounded exception, not a user deployment recipe.
Upstream1.18.1 and extension1.5.0 are preserved; no R01 version increment.
Next roadmap brief is R02 execution parity, expected next available spec169;
it is not started by this integration request. No R02 cloud/device operation is
authorized here. Keep the original R01 directory name despite the parallel
upstream168-openclaw-2026-10-compat feature; cite R01/full path to distinguish them.
