# Research: Hermes NCFED federation

Research was conducted against repository baseline9b0719c and spec148's pinned local source. Three read-only research agents investigated protected execution, NCFED trust/tasks and lifecycle/HUD. No live provider/device/peer interaction occurred during research.

## R1 — Reuse the protected companion

**Decision:** keep the pinned spec148 Hermes source, separate federation namespace/credential/port and a private stdio MCP entry point. Both Border and members use a managed long-lived companion.
**Rationale:** existing Bridge/Ledger already provide owned sessions, durable admission, bounded polling and unknown outcomes. ProtectedAIAgent freezes allowed tools and source/handler identity.
**Alternatives:** a raw `hermes` CLI runner loses deterministic tool restrictions and owned recovery; sending to ordinary Hermes gateway inherits unqualified tools; changing HUD's eight-tool contract breaks existing qualification.
**Evidence:** `mcp-servers/hermes-hud-mcp/{bridge,ledger,protected_agent,hermes_api}.py`; pinned upstream `gateway/platforms/api_server_runs.py`. Upstream constructs the agent with ContextVar then executes inference in a worker thread without copying that context: capture immutable authority on the agent before handoff.

## R2 — Separate model intent from dispatch authority

**Decision:** server-created scope and per-effect broker permits; receiver profiles contain no federation/admin tools. Initially qualify subnet-calculator and constrained existing n2n operations.
**Rationale:** the existing n2n-mcp includes grants, approvals, trust, kill and membership mutation. Whole-server allowlisting would exceed the requester's authority. The tool's metadata or prompt cannot enforce origin boundaries.
**Alternatives:** trust a prompt marker; pass requester as model arguments; use the ordinary unauthenticated local task API from receiver turns. All rejected.
**Evidence:** n2n-mcp tool inventory; protected policy; Authorizer/Invoker current admission gates. Broker disappearance or revoked permission must deny before tool dispatch.

## R3 — Keep the protocol and adapt execution

**Decision:** preserve NCFED channels, consent, identity, grants and task operations; select local execution from installation configuration only. Keep OpenClaw adapter and its controls, correcting session identity and uncertain outcomes.
**Rationale:** transport is already runtime-neutral. Required changes are local dispatch/configuration and capability reporting. Remote harness metadata is untrusted information, not launch authority.
**Alternatives:** new federation protocol or remote runtime-specific commands; rejected as unnecessary incompatible scope.
**Evidence:** `gateway.run_agent_turn`, `invocation`, `service`, `chat`. Existing external skill key n2n-skill-{skill} and chat key n2n-chat-{peer} collide across tasks/sessions. Existing member scope truthiness permits empty scope; both need correction. Existing OpenClaw prompt markers do not establish new enforcement guarantees; no broader security certification is inferred.

## R4 — Durable uncertainty and approvals

**Decision:** additive context/dispatch/usage/approval-consumption fields, authenticated deduplication and outcome_unknown. Preserve results and unresolved admissions, recover only by observation.
**Rationale:** current cancellation/restart paths claim cancelled after losing only a waiter; missing usage becomes0; sweep removes active rows; outbound submission has no record until a remote handle arrives. Approved approvals are not currently expired/consumed at exact dispatch.
**Alternatives:** retry on timeout or preserve all current terminal labels; rejected because network operations may already have executed.
**Evidence:** `tasks.py`, `authorization.py`, `invocation.py`; existing readmission, persistence and owner tests.

## R5 — Selected-home lifecycle

**Decision:** resolve canonical runtime selection once before launch; scope identity/base/API/PID/unit/interpreter and member env to the installation. Generate allowlisted Hermes member config and private credentials, not a Border config clone.
**Rationale:** CLI/peering/services and profiles currently hardcode OpenClaw paths; global pkill can affect other installations; member setdefault environment can inherit Border secrets.
**Alternatives:** set NETCLAW_RUNTIME only or reuse OpenClaw homes; rejected because neither fixes credential/state/runtime binding.
**Evidence:** `runtime-selection.py`, `netclaw`, `peering-{setup.sh,launch.py}`, `in2n-{member-home,member,services,profiles,migrate}.py`.

## R6 — Harness card

**Decision:** additive harness object separate from llm/posture/deployment runtime_kind and the inventory version counter. Safe bounded projection for both member and external card, with source/freshness and unknown legacy state.
**Rationale:** current card already carries model/tools/skills/posture; operator requested harness identity. External Border advertises only its own harness.
**Alternatives:** overload runtime_kind or guess OpenClaw for older peers; rejected as semantically wrong and misleading.
**Evidence:** `InventoryBuilder.build`, `member_inventory.project_inventory`, enrollment defaults process/mobile.

## R7 — Host and testing boundaries

**Decision:** use real pinned Hermes/real tool+NCFED under controlled provider on this Mac; retain separate hosted-provider and host/control dispositions. Mac production membership refuses missing containment; Linux/WSL require actual probes.
**Rationale:** spec148 validated its HUD, not NCFED or production confinement. Existing systemd controls are not portable assertions.
**Alternatives:** claim all platforms from unit tests or install unrestricted sandbox fallback; rejected.
**Evidence:** spec148 closure/validation, controls.py, in2n-services.py. Local source/fixture is present at `/tmp/netclaw148-mac-closure/Hermes Home/python-runtimes/hermes-hud-agent/`; this path is an observed local test resource, not a distributable default.

All product choices are resolved. Host availability and actual acceptance outcomes are verification obligations, not assumed passes. Detailed implementation may refine helper boundaries while retaining these decisions.

## R8 — Mobile owner expansion

Authenticated edge Ask Border currently calls the shared gateway without execution context; protected Hermes correctly refuses it. Existing edge enrollment uses device possession/trust and tasks already carry member_id ownership. The new path must be an explicit device operator profile, not the external receiver profile. Current protected scoped profiles accept only chat/subnet and operator broker validates only HUD admissions, so both must be extended together. Existing media is written to a message file; Hermes has no qualified multimodal admission and must reject explicitly before creating work. Flutter baseline1.0.2+4 maps new states to unknown and its reconnect reconciler leaves unknown pending, requiring client changes and compatible server projection. Further read-only mobile/backend/build research is in progress before implementation of this extension.

Research completion: runtime scope must survive disconnect yet revoke on membership/key-generation change. Existing operator broker needs a permit-authenticated federation-ledger mode; voice origin is composition metadata, not trust origin. Flutter changes include Live Activity/watch native Swift projections, not only Dart Chat. Existing integration timeout is informational and must become a failing acceptance assertion. Build environment: Flutter3.44.8/Dart3.12.2, Xcode26.6(17F113), macOS26.5.2, iOS/watchOS26.5 simulators; no Android SDK/JDK found.
