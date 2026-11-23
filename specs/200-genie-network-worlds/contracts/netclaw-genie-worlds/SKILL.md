> Historical planning draft. The source workflow has been promoted to
> [the executable-workflow skill](../../../../workspace/skills/netclaw-genie-worlds/SKILL.md)
> after actual MCP discovery/control qualification. Risk installation and Google
> acceptance remain open; this historical text is not the installed-skill authority.

---
name: netclaw-genie-worlds
description: Prepare and operate an illustrative network walkthrough with Google Genie through NetClaw controls, keeping pyATS facts local and separate. Use for a network-world demonstration or its session status, not device configuration or a routing simulation.
---

# NetClaw Genie worlds

Planning draft for Spec200; tools below are proposed, not installed. Promote
this file to `workspace/skills/netclaw-genie-worlds/SKILL.md` only after native
MCP qualification. Google API access is still required behind the MCP.

Use [control contract](../control.md) for tool arguments and
[provider contract](../provider.md) for lifecycle limits. During installation,
copy these two references into the skill's `references/` and update these links.
Do not infer tools are available because this draft names them.

## Owner-corrected delivery

Required worlds come from Google Genie 4 through the Gemini API. Demonstrate
realistic and fantasy styles as separately reviewed actual sessions. Do not draw
a replacement world locally or count a fixture as generation. This remains a
planning draft, not installed functionality.

## Route the request

- A real network question goes to existing pyATS read-only collection and the
  local facts view. Preserve source,time,unknowns and parser failures. Do not
  send those facts to Google or a hosted agent. Inventory is not device health.
- A hosted world starts from `synthetic-museum-v1`, an independently fictional
  fixture. Renaming a private topology does not make it eligible.
- Navigation and the fictional lamp event cannot configure a device, boot CML
  nodes or prove reachability. Generated scenery is an illustration.

## Prepare and review

1. Discover the six `genie_world_*` tools. If unavailable, report the missing
   integration; do not substitute an unrelated Genie MCP or browser workaround.
2. Call `genie_world_prepare` with the synthetic fixture ID. Use a private
   snapshot ref only for a local draft, never as input to hosted generation.
3. Open the local human review of exact outbound bytes/model/event,20s target,
   deadline,price and finite allowance. Use the resulting `review_ref`; do not
   manufacture it or pass an approval boolean. Existing valid exact approval
   need not be requested again. Planning/preview requires no paid credentials.
4. Credential entry belongs to the selected installation's private setup.
   Required backend settings are `GEMINI_API_KEY`, `NETCLAW_GENIE_STATE_DIR` and
   `NETCLAW_GENIE_ENABLED`; never ask for a secret in chat or expose it to tools.
   Browser subscription/key presence does not prove API entitlement.

## Start, observe and finish

Call `genie_world_start` once with stable request ID/projection/review refs.
Persist that UUID: start uses `operation_id=request_id`.
If a response is lost,read status with the same UUID; never create a replacement request.
Use `genie_world_status` for retained state. Direct the operator to the local
viewer for at least10s movement and a look-back. Tool responses contain no video.

Invoke `genie_world_event` once for the pre-reviewed lighting event only when
the operator marks its target visible in the viewer (readiness expires in2s);
never infer visibility from elapsed time or tool status; use the same event ID if inspecting a duplicate
result. Sent/acknowledged is not visual success. Do not retry because the lamp
failed to change. Record the outcome for review.

Use `genie_world_stop`, then read status/evidence. Stop requested, successful
SDK return and browser closure are not confirmed termination. Require a provider
terminal receipt and separately check usage. Unknown means possible ongoing or
unsettled activity: preserve the original ID/reservation,report it and do not
start another session,clear holds,switch credentials or claim zero cost.

Get `genie_world_evidence` and compare baseline/post-navigation/post-event views
against the four structures,three corridors and one event. Label added/missing
objects,unseen connections and uncertain outcomes explicitly. Retain failures;
a preview/prompt/API announcement does not satisfy live-world acceptance.

Report measured facts separately from fiction,actual navigation/event outcome,
terminal/usage status and reviewer verdict. Audit with existing GAIT; no external
message or publication is part of this workflow.

## Examples

- “Prepare the synthetic network museum for review.” → prepare only, no spend.
- “Start this reviewed world.” → validate existing exact grant, one start.
- “The tab closed; run it again.” → original status/termination reconciliation
  first; never assume closing the tab ended billing.
- “Make my real topology public by renaming routers.” → retain it locally;
  offer the independent synthetic scene instead.
