---
title: "Claroty xDome joins NetClaw — OT visibility lands as MCP #74"
date: 2026-06-08
authors: [John, Claude]
status: draft
target: WordPress MCP (not configured locally — publish manually)
spec: specs/035-claroty-mcp/
---

# Claroty xDome joins NetClaw — OT visibility lands as MCP #74

NetClaw's coverage has always leaned IT — Cisco fabrics, F5 load balancers, NetBox, ServiceNow, the usual suspects. Today we close one of the biggest visibility gaps on the OT side by bringing **Claroty xDome** in as MCP server #74, with three new skills and 21 tools (15 read-only, 6 ITSM-gated writes).

## What we built

A FastMCP/stdio server (`mcp-servers/claroty-mcp/`) that wraps the Claroty xDome REST API, plus three new skills under `workspace/skills/`:

- **`claroty-asset-inventory`** — discover OT / IoT / IoMT devices, filter by Purdue Model layer / device purpose / site, and classify newly discovered assets with their Purdue level or compliance tags. Cross-references Nautobot and NetBox to flag drift between Claroty's observed inventory and the SoT of record.
- **`claroty-risk-triage`** — unified alert + vulnerability triage. List alerts by severity, compute blast radius with `get_vulnerable_devices`, correlate with the NVD CVE MCP for CVSS vector decomposition, then label / assign / acknowledge with full ITSM gating.
- **`claroty-ot-topology`** — feed device communication maps into Canvas/A2UI or draw.io for inline topology rendering and exportable diagrams; surface organisation zones to audit segmentation.

The xDome API throws three curveballs that the client layer hides from tool authors:

1. **Every endpoint is POST.** No GETs, even for pure list/lookup operations.
2. **Pagination is offset/limit in the JSON body.** Not page tokens, not Link headers.
3. **Rate limit is 2000 requests/min/endpoint** with 429 + Retry-After on exhaustion.

`clients/claroty_client.py` exposes `post(endpoint, body)`, `paginate(...)`, and `collect(...)`. Tool authors never write a pagination loop. The sliding-window rate limiter inside `post()` caps outgoing requests at the configured budget so the upstream gate is never tripped under normal load.

## Why it matters

OT / IoT / IoMT visibility is not optional any more — it's where ransomware and supply-chain attacks land hardest. A CCIE-level network engineer needs to be able to answer "what devices does this CVE actually touch on the plant floor?" and "is this PLC really at Purdue level 1, or did someone wire it into the IT VLAN by mistake?". Without Claroty we were guessing.

Just as important: every write tool is **ITSM-gated** using the exact same `validate_change_request(cr_number)` pattern we ship in `gnmi-mcp`. Same `CHG\d+` regex, same `NETCLAW_LAB_MODE` bypass, same "Implement" state check against ServiceNow. Consistency across the project is its own value — if you know one of the gates, you know all of them.

## Key technical decisions

- **GCF shim, not refactor.** The small `utils/gcf_helper.py` shim imports `netclaw_tokens.gcf_serializer.serialize_response()` with a JSON fallback — the same pattern `azure-network-mcp` uses, so the server matches the repo's GCF standard out of the box. Tempting to refactor the serializer into a proper shared package import, but that touches every MCP — separate spec, separate PR.
- **ITSM gate copied verbatim.** Rather than abstract the gate into a shared library (which would touch `gnmi-mcp` too), we copied `itsm_gate.py` and only changed the module logger name. The cost is a small amount of duplicated code; the value is total decoupling — Claroty does not have to wait on gnmi or anything else to evolve.
- **No `CLAROTY_LAB_MODE`.** NetClaw already has `NETCLAW_LAB_MODE` (gnmi) and `ITSM_LAB_MODE` (nautobot) in use. Introducing a third would make the lab-mode story worse. We chose `NETCLAW_LAB_MODE` because it's the one the constitution mentions and the one `itsm_gate.py` already uses.
- **Edge sensor lifecycle deferred.** The xDome API exposes 59 operations; v1 implements 21 (the highest-value reads plus the writes that map cleanly to NetClaw's CR taxonomy). Sensor lifecycle (add/update/delete locations, generate/rotate API keys) gets its own spec — it has its own CR shape and probably its own skill.
- **3 skills, not 4.** We considered splitting alert triage and vulnerability triage into two skills. We didn't, because real incident response crosses the boundary constantly — an alert leads to a CVE, a CVE leads to a different alert, both lead to a label or assignment. Keeping `claroty-risk-triage` unified means the operator doesn't have to context-switch.

## Lessons learned

The `azure-network-mcp` pattern is the gold standard for FastMCP REST servers in this repo — `tools/`, `clients/`, `models/`, `utils/` separation, GCF helper shim, FastMCP `mcp.tool()(fn)` registration. We copied that layout almost verbatim and it just worked.

The `INTEGRATION_CATALOG` and `ENV_MAP` in `ui/netclaw-visual/server.js` are easy to forget. They're both required by Principle XI (Artifact Coherence) — without the catalog entry, the new MCP is invisible to the HUD; without the ENV_MAP entry, the "Edit ENV" button 404s. Two edits in one file, not a separate config.

`SOUL-SKILLS.md` is the kind of artifact that decays silently. We added the three new skill procedure blocks in this PR; on the next milestone we should grep `SOUL-SKILLS.md` against `workspace/skills/` to confirm nothing has drifted.

### The six-round fix journey — what live smoke caught

The initial commit "worked" in a unit-test sense. Live smoke against a real production xDome tenant found six distinct classes of bug, each of which had to be discovered and fixed independently:

1. **Endpoint path inference from `operationId` names is dangerous.** `get_device_communication_map_api_v1_device_communication_map__post` looks like it implies the path `/api/v1/device_communication_map/`. It doesn't. The real path is `/api/v1/device/communication-map/` (singular `device`, hyphen). 11 of 21 paths I'd inferred were wrong. **Rule: always read the `paths` block, never the operationId.**
2. **`fields` is required on every list endpoint** and the `filter_by` shape is `{field, operation, value}` — schema key is `operation`, not `operator`, despite what one OpenAPI example shows. Strict-schema validators win over docstring examples.
3. **Response wrapper keys are resource-named** (`devices`, `sites`, `alerts`, `audit_log`, `organization_zones`), and one endpoint uses `records`. None use `items` / `results` / `data`. A parser that falls back to those silently returns `count: 0` — which **looks identical to an empty tenant**. We now log a `WARNING` when no recognised key matches, so this never goes invisible again.
4. **`limit` should mean "max total returned"**, not page size. Returning a separate `max_items` to the public API meant `list_alerts(limit=3)` actually paged 167 times until 500 items. Smoke caught the wall-clock immediately.
5. **Enum hallucinations**. I'd documented `acknowledge_alert(status="Investigating")` and `set_vulnerability_relevance(relevance="Mitigated")` from memory. The real enums are `{"resolved", "unresolved"}` (lowercase) and `{"Confirmed", "Potentially Relevant", "Fixed", "Irrelevant"}` (title case with spaces). Always cross-check enums against the spec, even ones that "obviously look right."
6. **Spec inconsistency on the `id` field**. xDome's `Vulnerability.fields_enum` doesn't include `id`, but the spec's own example uses `"fields": ["id", "name", ...]` and the path parameter is documented as "the `id` field of a vulnerability". The fix: capture `id` from the raw response (xDome returns it implicitly), document the inconsistency, don't add it to the default fields list to dodge a possible strict-validator 422.

### Live smoke doubled as a posture audit

The same smoke run surfaced real operational findings about the customer's environment — unsegmented device groups, sparse edge-sensor coverage, exploitable CVEs on specific device classes, and a high-severity finding the relevance evaluator under-counted. **Those specifics are customer-confidential and were delivered to the operator out-of-band, not committed to git.**

The MCP server's first day in production turned into a working OT-security audit. That's the right shape of result.

### Structured errors over opaque ones

Phase E end-to-end mutation got blocked at xDome RBAC — the test token didn't have alert-write scope. The wrapper's structural pass was confirmed (gate passes, body builds correctly, response shape correctly distinguishes the four outcomes), but the final 403 was opaque. We added a `ClarotyAPIError` class that captures status code, path, parsed body, and operator hints, then plumbed it through every tool's error envelope. Now the agent sees:

```json
{
  "itsm_gate": {"valid": true, "state": "lab_mode", ...},
  "applied": false,
  "error": {
    "status_code": 403,
    "path": "/api/v1/device-alert-status/set",
    "message": "xDome HTTP 403 — Forbidden — ...lacks the scope...",
    "body": {"detail": "Token lacks write:alerts scope"}
  }
}
```

…instead of a bare `HTTPStatusError` string. Whoever debugs this next gets a runway.

## Coherence checklist — what got touched

- `mcp-servers/claroty-mcp/` (server + tools + utils + models + README)
- `workspace/skills/claroty-{asset-inventory,risk-triage,ot-topology}/SKILL.md`
- `specs/035-claroty-mcp/` (full SDD spec — spec, plan, research, data-model, contracts, quickstart, tasks, checklist)
- `config/openclaw.json` — `mcpServers.claroty-mcp` registered
- `.env.example` — 5 new `CLAROTY_*` vars
- `scripts/install.sh` — Step 50h installs Claroty deps
- `ui/netclaw-visual/server.js` — `INTEGRATION_CATALOG` + `ENV_MAP`
- `README.md` — bullet + MCP #74 table row + count bump
- `SOUL.md` — "Claroty OT Security Skills (3)" section + count bumps
- `SOUL-SKILLS.md` — 3 new procedure blocks
- `TOOLS.md` — Claroty MCP section

## What's next

Hooking the Claroty skills into the existing reconciliation workflows. The asset-inventory skill cross-references Nautobot today, but we should formalise a `claroty-vs-nautobot-drift` skill once we have a few weeks of joined data. The risk-triage skill hand-offs to `ise-incident-response` are documented but not yet automated — that's the natural next step.

Also: edge sensor lifecycle. We deferred it for good reasons (separate CR taxonomy, separate skill domain), but operators provisioning new plants will want it sooner rather than later. Watch for `specs/03X-claroty-edge-lifecycle/`.

---

*If the WordPress MCP server isn't configured in this deployment, publish this draft from `docs/blog/2026-06-08-claroty-mcp.md` manually.*
