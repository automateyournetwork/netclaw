# Implementation Plan: NetConverter AI and virtual migration rehearsal

**Branch**: `162-netconverterai` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

## Summary

Integrate the official NetConverter service through one optional NetClaw-owned MCP guard and the unmodified operator-installed Terminal. Enforce the chosen exact-file submission policy locally, then compose existing collection, lab, pyATS, Batfish, Jev and reporting tools. Actually provision and test eligible virtual migration targets. Extend the existing Terminal Intent artifact/change boundary where needed; never invent a generic lab approval exception.

The initial managed profile uses an installation-specific API key and fixed official HTTPS destinations. Hosted-readonly mode requires no Terminal. Local-terminal mode supports ordinary convert/validate/optimize, reviewed submission and verified downloads. Upstream OAuth remains documented for independently configured clients, but is not silently borrowed by the managed submission profile. Guided-draft mutations and mapping-triggered conversion remain explicitly unavailable until a distinct approved contract is implemented; no fallback bypass is allowed.

## Technical Context

**Language/Version**: Python 3.12 for isolated MCP execution; Python 3.10+ compatible installer utilities; existing TypeScript 5.9 and Node runtime policy for VS Code/HUD.  
**Primary Dependencies**: Existing pinned FastMCP 4.0.11 and official MCP SDK 2.3.0; stdlib SQLite/hashlib/path utilities; existing UI stack. Official Terminal 0.5.0 is operator-installed, not vendored or patched.  
**Storage**: Private installation-owned SQLite request/attempt ledger and bounded artifact directories (0700 directories, 0600 private metadata; frozen inputs not writable through exposed tools). Existing API-owned Local/Lab records remain authoritative for candidate application.  
**Testing**: Python unit/contract tests, real official-SDK controlled-peer tests, existing installer/TypeScript/Node suites, isolated native setup interaction and conditional live tenant/vendor-appliance acceptance.  
**Target Platform**: Existing Mac/WSL installer targets; actual appliance execution on a verified compatible lab host. Source-platform qualification and target appliance qualification are separate.  
**Project Type**: MCP integration, runtime skill and narrow existing-workflow extensions.  
**Performance Goals**: Local preparation bounded by a 20 MiB artifact ceiling (further narrowed by upstream capability); MCP calls finite, ordinary polling <=45 seconds/call and <=5 minutes per unattended sequence; resumable known-job reads afterward. No conversion latency guarantee.  
**Constraints**: No upstream redistribution/license acceptance, raw source config in model arguments, generic shell/tool proxy, tool-denial bypass, production attachment or automatic destructive lab cleanup.  
**Scale/Scope**: One optional component, one guarded registration and one new migration skill. Preferred live reference: owner-requested IOS-XE→JunOS with OSPF, actual adjacency/routes/traffic checks and an evidence-based community article. ASA→Palo Alto SET remains an additional conditional workflow. Five recorded implementation review iterations.

## Constitution Check

Pre-design review passes with the following explicit obligations; recheck after implementation and qualification:

- MCP-native: new server uses official SDK/FastMCP. The upstream client's custom protocol implementation is neither copied nor adopted as NetClaw-owned protocol code.
- Read/baseline/apply/verify: virtual targets require real baseline and scoped verification; creating a virtual node does not authorize candidate application.
- Change control: use existing approved production configuration tools or the existing OpenClaw Terminal Intent Local/Lab API workflow. Hermes Local/Lab APPLY remains unavailable. No invented CR or generic LAB_MODE exemption.
- Immutable audit: real GAIT calls for workflow milestones; existing provider logger decorators are not treated as immutable audit. The documented Local/Lab exception retains its own scoped audit.
- Artifact coherence: catalog/installers/readiness/HUD/config/env/README/SOUL/TOOLS/skill and relevant schemas/counts update together.
- Privacy: source collection and candidate apply use local artifact references; approval binds exact bytes, destination and operation. Separate Jev/Batfish disclosures retain their own controls.
- Existing authorization: the file-taking apply route must use the existing configuration tool identity and checks. No new tool alias may bypass a denied existing configuration capability. Collector scopes stay read-only.
- Publication: source work and a community draft do not publish releases, extension packages, articles or tickets. Use the repository's current version convention at completion; source and extension versions remain independent.

No constitutional waiver is proposed. If the runtime cannot preserve the configuration tool's existing denial semantics, its artifact-apply route is unavailable until fixed and tested.

## Architecture and decisions

### 1. Guarded MCP integration

Implement `mcp-servers/netconverter-mcp/` with a small core, transport and private-artifact module. Expose status/discovery, prepare, submit-approved, local request status, guarded reads, job status/wait and verified download. All operations are bounded. Native operator CLI `scripts/netconverter-settings.py` reviews and approves an existing exact digest; no MCP tool issues approval.

A request freezes source bytes under a private NetClaw-owned directory inside the selected Terminal workspace, outside `.netconverter`. Bind installation, request, source identity/hash/size, frozen hash, operation/options, source/target, workspace, executable provenance, fixed destinations and a private credential fingerprint. Approval expires by default after five minutes and is consumed atomically before one outbound attempt. A changed binding invalidates it. Unknown outcomes persist across restart and never trigger another submission.

Use explicit `--auth key`, fixed `--server` and `--mcp-url`, workspace and strict privacy cap; allowlist child environment and disable update/model/provider behavior. Do not silently borrow Clerk/keychain credentials. The configured account label is operator metadata, not a verified tenant ID. Discover the actual path catalog through supported MCP evidence or the fixed official `capabilities` CLI operation; never infer it from vendor names or `account` alone.

Hosted reads use the fixed official HTTPS MCP endpoint, strict-view request, no redirects/environment proxies and a known read allowlist intersected with discovered schemas. Reject unparsed/raw-target retrieval, mutation aliases and unexpected tools. Cap output size and preserve partial/redacted/truncated evidence. Ordinary upstream read availability and the guard's exposure policy must be visible separately.

### 2. Installer and readiness

One `netconverter` component and `netconverter-mcp` registration prevent a second unguarded submission route. The installer installs only NetClaw guard dependencies in its selected isolated runtime. The operator supplies a licensed Terminal executable where local mode is selected. Catalog conditional settings distinguish public mode, private workspace/executable/account references, secret API key and generated private state paths. Both setup paths validate mode; no configuration transfer occurs during setup.

Update the reviewed effect hash/dispatch and native runtime registration contracts. Add `nck_live_` detection to non-secret-plan checks in Python and TypeScript. Readiness reports guard installation, discovery, upstream connectivity, Terminal/license, authentication, capability and approval state separately. Do not equate discovery with readiness to convert.

### 3. Private artifacts and candidate application

Use file references at collector→converter and converter→target boundaries. Start with an optional metadata-only artifact output on the existing managed `pyats_show_running_config` tool, retaining its read authorization and original default behavior. It stores the configuration privately and returns only an artifact reference. Other inline-only collectors need separately qualified fixed adapters; do not add arbitrary relays. Arbitrary server/tool/command selection is prohibited. If no qualified adapter exists, use an operator-staged artifact and report that handoff limit.

Extend the existing Terminal Intent UI/request with reviewed candidate artifact selection, and bind artifact identity/hash, endpoint IDs/identities, active testbed fingerprint, exact configuration tool and verification profile into the API-owned record. Preserve read-only preparation, actual baseline/rollback capture and API APPLY transition.

Add a narrow artifact-reference input to the managed existing pyATS configuration route. Preserve the original tool identity for runtime policy enforcement and backwards compatibility; artifact input is mutually exclusive with inline configuration. The backend requires a fresh API-issued apply capability bound to the recorded task/endpoint/candidate/tool, with a one-use attempt claim. A caller-supplied record path, `approved:true`, an APPLY string, or merely finding an on-disk apply record is insufficient. The API supplies the capability only after the actual reviewed workflow transition. There is no MCP grant-issuing operation; the capability uses the issuer/consumer contract in contracts/rehearsal.md and cannot be widened through tool arguments. Verify broker/tool-denial behavior before qualification.

Read/recheck candidate bytes locally, retain dangerous-command checks and capture full configuration/diff privately without raw upstream logs entering model responses. Record only safe status and evidence references. On timeout, consume the attempt and reconcile observed state; no blind replay. Do not call raw SSH or another platform configuration setter after a denied route. Production and non-pyATS configuration adapters retain their own existing approval requirements; unavailable adapters are explicit.

### 4. Real virtual-target rehearsal

The skill orchestrates existing platform MCPs after discovering actual schemas, images, architecture, licensing, capacity, management/bootstrap and isolated network eligibility. Use exact template/image identities. Node definitions/templates alone are not proof of an installed image. Resource ledger entries precede creation attempts; uncertain creation reconciles by ownership before retry.

Provision only the reviewed run-owned skeleton/bootstrap. Bootstrap itself must be authorized; no converted candidate hidden in a create-node payload. Keep management/data networks isolated from production. Discover actual endpoints, then apply through the artifact-bound workflow above. The pyATS dynamic testbed and subsequent observations must share the same persistent MCP process.

Run positive and negative TCP/UDP flows, selected routes/VRFs and routing adjacency checks, plus observed NAT evidence when present. If both source and target images exist, use the same assertion matrix and retain differences. Test image/version feature coverage explicitly; virtual software cannot establish ASIC/throughput equivalence. FRR can supply peers/traffic and separately labeled intent-based experiments, never impersonate a vendor conversion target.

Retain resources for review by default. Stop/recovery requires the authorized run scope; destructive delete/wipe/destroy/restore is not inferred from cleanup. Record retained/stopped/recovered/unresolved states and exact resource ownership.

### 5. Evidence and composition

Fix Batfish's interpretation boundary so partial parsing and failed differential queries cannot appear as equivalence. Keep modeled versus observed assertions distinct. Jev reviews selected permitted evidence, with its existing enablement/budget/disclosure controls. Produce observed/proposed diagrams, a validation matrix, manual actions, rollback plan and a local ticket/document draft. Sending or creating external records needs the user's applicable authorization.

The skill entrypoint stays concise. References cover upstream operations, collection/composition contracts, lab rehearsal and evidence/reporting. Preserve supplied archive provenance and replace stale vendor/tool claims. Reuse existing skills, correcting narrowly relevant stale tool names or generic lab-control advice where discovered.

## Project Structure

```text
specs/162-netconverterai/
  spec.md, plan.md, research.md, data-model.md, quickstart.md
  acceptance-scenarios.md, tasks.md, verification.md, ralph-iterations.md
  contracts/integration.md, contracts/rehearsal.md
mcp-servers/netconverter-mcp/
  server.py, core.py, transport.py, artifacts.py, README.md
scripts/netconverter-settings.py
scripts/lib/migration_artifacts.py
scripts/pyats-managed.py
workspace/skills/netconverter/SKILL.md
workspace/skills/netconverter/references/{operations,composition,rehearsal,evidence}.md
config/{openclaw.json,installer-access.json,python-components/netconverter.txt}
config/components/{catalog.json,effects.json}
ui/netclaw-visual/{terminal-change-policy.js,terminal-intent-execution.js,LOCAL-LAB-CHANGE-CONTROL.md}
tests/netconverter/
docs/NETCONVERTER.md
```

Existing catalog generators, installer setup/secret/report files, VS Code setup views/validation and HUD/Terminal Intent UI files are extended in place. No new UI framework or general orchestration engine.

## Qualification and delivery

1. Complete core gate/SDK, installer and private-artifact tests without accounts or uploads.
2. Demonstrate actual ordinary upstream discovery only after the operator supplies its licensed client/account; report missing prerequisites honestly.
3. Verify the existing native tool denial remains effective for artifact input, then qualify the reviewed apply transition using controlled peers and isolated UI.
4. On an authorized compatible lab host, create a real virtual target and run a real supported migration rehearsal with exact-file upload approval. Preserve source/target image and test evidence.
5. Run five recorded same-prompt Ralph review/fix/test rounds after initial implementation, followed by cross-artifact reconciliation. Changed code gets appropriate tests; unchanged passing suites are not rerun mechanically.
6. Record source completion separately from live qualifications. An unavailable host/account is a blocked acceptance item, not a passed fixture test or a reason to fabricate completeness.

## Complexity Tracking

No exception. The additional artifact-bound apply extension is necessary because existing configuration APIs take inline text and lack candidate-bound one-use authorization; a skill-only recipe would not satisfy the user's actual virtual migration testing requirement safely.
