---
name: hermes-hud-diagnostics
description: Diagnose selected Hermes HUD readiness and uncertainty without submitting agent work or registering recursive conversation tools.
license: Apache-2.0
user-invocable: true
---

# Hermes HUD diagnostics

Use for a Hermes installation whose shared HUD is unavailable, incorrectly selected, or showing an uncertain request. Read `docs/HERMES-HUD.md` and `mcp-servers/hermes-hud-mcp/README.md` in the NetClaw checkout.

1. Run `./scripts/netclaw hud status` from the checkout. Observe selection, configuration presence, authenticated companion readiness, qualified tools and separately reported execution verification. Do not print provider credentials or private transcript contents.
2. If selection is wrong, explain the intended `hud select hermes /absolute/home` change before making an owner-requested switch. Do not infer a home from OpenClaw data.
3. Missing component needs `./scripts/install.sh --runtime hermes --add hermes-hud`; start only when requested. Never restart the owner's Hermes gateway as a diagnostic shortcut.
4. A source/policy mismatch requires requalification or restoration of the pinned source. Do not disable protection, register unreviewed tools or silently switch to OpenClaw.
5. Unknown work is reconciled through its owned HUD status/history. Never resubmit it, infer cancellation from stop acknowledgment, or claim a device operation from assistant prose.
6. Live provider/tool tests require the explicit acceptance workflow; a read-only status request does not authorize inference, tool execution or device access.

The bridge's eight tools are **HUD-private**. Do not add them to Hermes or OpenClaw MCP registries, call conversation submission from inside an agent, or broaden once/deny approvals. Initial qualification supports only the reviewed IPv4 subnet tool and static installed skill context. Writes, attachments, model/effort overrides, hosted Avatar and federation are unavailable; federation belongs to spec 149. Local Avatar shares Standard Chat without creating a run merely by switching views.
