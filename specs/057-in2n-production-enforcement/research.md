# Phase 0 Research: iN2N Production-Mode Enforcement & Durable Runtime

All spec `[NEEDS CLARIFICATION]` were resolved in `/speckit.clarify` (Session 2026-07-13). This document records the technical decisions that back the plan. Format per decision: **Decision / Rationale / Alternatives considered**.

## R1 — Control verification model (preflight + background poll)

**Decision**: Every delegation runs a **synchronous preflight** in `service.py` (`route_and_delegate` / `delegate_to_member`) that probes the three controls via `controls.py` and applies FR-019 (block containment gaps, allow+flag audit gap). Independently, `bgp-daemon-v2.py` starts a **background poller** (asyncio task, ~10s interval) that refreshes a cached `RiskPosture` used by the status tool, heartbeat, and HUD. Probes are cached ~3s so a burst of delegations doesn't spawn a burst of CLI calls, but the cache TTL is short enough that a preflight reflects a control that just dropped.

**Rationale**: Preflight is the only place a fail-closed guarantee can be made (SC-003: 0% unguarded when DefenseClaw is down) — a poll-only design has a window between polls where a task could slip through. The background poll exists purely so the *displayed* posture is fresh without waiting for the next delegation (US1/US6). This is exactly the two-tier answer chosen in clarify.

**Alternatives considered**: *Preflight only* — posture display goes stale between tasks, hurting the heartbeat's usefulness. *Poll only* — cannot guarantee fail-closed (the very failure 056 exhibited).

## R2 — OpenShell sandbox wrapping (fail-closed member launch)

**Decision (REVISED during implementation — see note)**: In production, a member runs **kernel-confined via host-level systemd sandboxing** — its unit is hardened (`NoNewPrivileges`, `ProtectSystem=strict`, `InaccessiblePaths` on the master `.env`, `PrivateTmp`, and syscall/namespace/address-family limits on a native-Linux manager), and on-demand members cold-start inside a transient hardened `systemd-run` unit. `controls.py::sandbox_available()` probes that the systemd user manager is reachable AND member units carry the confinement directives; if unavailable in production the launch is **refused** and posture goes degraded (FR-005).

**Why NOT the OpenShell container (original plan, rejected during live validation)**: OpenShell sandboxes are fully isolated, **network-egress-denied, empty containers** (no `openclaw`, no member home, no route to a device/API). A member whose job is querying live infrastructure cannot run in one without a bespoke per-member image (version-matched openclaw + repo MCP servers + deps) *and* an egress policy — a whole sub-project, and it fights OpenShell's design (isolated ephemeral compute, not a live-infra agent). We verified this on the running system (reverse-engineered OpenShell's policy schema, got least-privilege egress working, then hit the image/deps wall). Host-level confinement keeps the member's real tools/network while genuinely confining it, and is what the live 6/6 was validated on. OpenShell remains available for isolated code execution.

**Rationale**: Reuses the already-installed `openshell` CLI (`~/.local/bin/openshell`, spec 027 NetShell). Wrapping at launch means the whole member process (agent + its scoped MCP servers) is contained, which is the least-privilege guarantee behind the "compromised member can't reach other secrets" promise. Both launch paths must wrap, or a cold-started member would escape the sandbox.

**Alternatives considered**: Sandbox only the service-managed members (leaves cold members unsandboxed — rejected, violates SC-002). Sandbox per-tool-call inside the agent (wrong layer; the member process itself must be contained). Build a new sandbox (violates "reuse, not reinvent").

**Open item for Phase 1 contract**: the exact `openshell` invocation form (`openshell run -- <cmd>` vs profile flag) — captured in `contracts/controls.md` as the wrap contract; the implementer confirms against the installed CLI's `--help`.

## R3 — DefenseClaw model-I/O guard + component scan (fail-closed)

**Decision**: Two DefenseClaw touchpoints in production:
1. **Component scan before a member runs** — `defenseclaw skill scan <name>` / component scan across the member's scoped skill/MCP set (from its profile). A flagged component blocks that member (FR-008). Runs once at (cold-)start, result cached for the member's lifetime.
2. **Model I/O guard** — member/Border model calls routed through the DefenseClaw guard path. The existing `invocation.py::_defenseclaw_inspect` already gates *tool* calls fail-closed when `security.mode == defenseclaw`; this spec extends guarding to the **member model turn** in `gateway.py` (the `openclaw agent --local` path) so prompts/completions are inspected, and makes production **require** the guard reachable (fail-closed if `defenseclaw` CLI/proxy is unavailable — FR-009).

`controls.py::defenseclaw_available()` probes the `defenseclaw` CLI **and** its guard/proxy health **and** that `security.mode=defenseclaw` is in effect.

**Two mode switches — reconciled (resolves analyze finding I1/C1)**: there are two independent switches and they must not diverge. (a) `N2N_RISK_MODE` (`testing`|`production`) is 057's risk-level enforcement flag. (b) OpenClaw's `security.mode` (`hobby`|`defenseclaw`, in `~/.openclaw/openclaw.json`) is what the *existing* `invocation.py::_defenseclaw_inspect` keys on — and it **early-returns allow when `security.mode != defenseclaw`**, with `hobby` the default. If we reused that verbatim under production, a `production` + `hobby` risk would silently NOT guard, yet a CLI-presence probe could report the control "available" → a **false enforced** claim (the exact thing FR-002 forbids). Resolution:
- Entering production **requires (verify-only) `security.mode=defenseclaw`** so the **Border's own** model turns (which run through the OpenClaw gateway, not the member local path) are guarded by OpenClaw's guardrails (covers C1 — Border-side guarding). This mode lives in `~/.openclaw/config/openclaw.json` (the DefenseClaw config); it is NOT written by the daemon — an earlier auto-write into the *gateway's* `~/.openclaw/openclaw.json` (wrong file, stricter schema) broke gateway startup with `security: Invalid input`, so the daemon now only *checks* and the operator enables DefenseClaw via its own tooling.
- The **member** local-execution path (`gateway.run_agent_turn local=True`) routes its model I/O through DefenseClaw **unconditionally in production** — it does NOT consult `security.mode` (so `hobby` can't create an unguarded member).
- `defenseclaw_available()` returns available **only** when the guard is reachable AND `security.mode=defenseclaw`; a merely-installed-but-disabled CLI is reported unavailable → posture degraded, never enforced (FR-009).

**Rationale**: 056 already proved the fail-closed tool-inspect pattern (deny on `FileNotFoundError`/error). We extend the same discipline to model I/O and add the pre-run component scan, rather than inventing a new guard. Tying the availability probe to *both* reachability and `security.mode` is what prevents the false-enforced trap and covers both the Border (via gateway guardrails) and members (via unconditional local guarding).

**Alternatives considered**: Rely on OpenClaw's own `security.mode` alone (it gates the Border's gateway path but NOT the member local turn, and doesn't drive posture — so members could go unguarded). A LiteLLM/proxy-only interception (the proxy was the thing that was down; CLI inspection is the reachable fallback and both are probed).

## R4 — GAIT-git immutable trail (complement SQLite)

**Decision**: New `gait.py` maintains a dedicated git repo at `~/.openclaw/n2n/gait/`. On each federation security event (delegation, enrollment, member removal, quarantine) it writes/append a JSON line to an event log file and `git commit`s it with an attributable message (operator/claw + event + timestamp). `audit.py::_gait_ref` (currently returns `None`) calls `gait.emit(...)` and stores the returned commit SHA in the existing `gait_ref` column — so the SQLite row and the git commit cross-reference. Trail is **unbounded** (FR-012a); rely on `git gc`. Read access is a thin `gait.recent()` for review/HUD. Best-effort: a GAIT failure never breaks the SQLite audit (which stays authoritative), but in production a non-recording GAIT drives posture degraded (FR-011).

**Rationale**: Constitution IV mandates the git immutable trail; the SQLite audit is queryable but mutable. A separate repo (not the netclaw source repo) keeps federation audit isolated and avoids polluting code history. Commit-per-event gives natural immutability and time-ordering. Matches the existing `gait_ref` column already in the schema (designed for exactly this).

**Alternatives considered**: Commit into the main repo (pollutes history, risky). One commit per session summary (loses per-event attributability required by FR-012). A non-git append-only file (git gives the immutability + attribution + tooling for free; Constitution names GAIT specifically).

## R5 — Durable services: one unit per always-on member (generator)

**Decision**: New `scripts/in2n-services.py` **generates** systemd `--user` units: `netclaw-mesh.service` (formalizing the hotfix, checked into repo as a template) and `netclaw-member-<id>.service` for each always-on member, each `Restart=always`, `WantedBy=default.target`, with an `EnvironmentFile` pointing at that member's env. `risk.py` gains a `managed_by` field per member (`service` | `cold`). Single-owner reconciliation in `service.py::_cold_start`: if a member's `managed_by == service`, the cold-start path checks the unit is active (start it via `systemctl --user start` if not) instead of `create_subprocess_shell` — so a service-managed member is never double-launched. Non-systemd hosts: the generator detects `systemctl --user` availability; if absent, it writes the units + a note and posture reports the durability control degraded (documented fallback).

**Rationale**: Mirrors how `openclaw-gateway.service` and the `netclaw-mesh.service` hotfix already run — proven on this host. One unit per member gives independent restart and honest per-member `systemctl status` (feeds FR-017 fault isolation) and makes single-owner trivial (unit active ⇒ skip cold-start). Generating (not hand-authoring) satisfies FR-015 and Constitution XI (installer coherence).

**Alternatives considered**: Single supervisor service (reintroduces a single point that can take members down together — the 056 failure mode). Daemon-supervises-in-process (couples member lifetime to the daemon, complicates single-owner and independent status). `nohup`/`setsid` (the exact non-durable thing 057 exists to kill).

## R6 — Fault isolation: daemon vs member vs backend

**Decision**: Health/status in `service.py` computes three distinct causes: **daemon-down** (the mesh daemon / listener not answering — detectable because the status tool itself can't reach the daemon, or a self-probe fails), **member-down** (daemon up, but a member's channel is absent/unhealthy — from the existing per-member `health`/`_spawning` state, plus whether it will cold-start), **backend-unreachable** (member up and a task ran, but the member's *task result* reports its backend/device/API failed — surfaced from the task error, not conflated with a federation fault). The operator heartbeat consumes this triage (FR-018). Fixes the 056 misdiagnosis where a poll bug read as a "member flap."

**Rationale**: The three causes need different operator actions (restart daemon / wait-for-cold-start / check the device), so conflating them makes the heartbeat untrustworthy. The state needed already largely exists (`self.health`, `_spawning`, task errors); this is mostly correct attribution, not new plumbing.

**Alternatives considered**: A single up/down health bit (the status quo that caused the misdiagnosis). A separate health-probe daemon (overkill; the data is already at the Border).

## R7 — Degraded-operation policy wiring (per-control, FR-019/020)

**Decision**: The preflight (R1) maps missing controls to actions: **containment gap** (OpenShell OR DefenseClaw) → refuse the delegation with a clear reason code; **audit gap** (GAIT) → allow but tag the result `audit-degraded` and reflect it in posture/heartbeat/result; operator **strict-all** override (env `N2N_STRICT_ALL=1`) → refuse on any gap. The delegation result envelope carries an `enforcement` field (`enforced` | `audit-degraded` | `refused:<control>`) so an operator always knows what happened (FR-020).

**Rationale**: Directly encodes the clarified per-control decision — containment is a security guarantee (block), audit is a compliance record (warn), and the operator can tighten to strict-all. Carrying the state in the result is what makes SC-008 testable.

**Alternatives considered**: All-or-nothing block on any gap (safe but makes an audit-only gap needlessly halt operations; offered as the opt-in strict-all instead). Warn-only on all gaps (unsafe for containment — rejected).

## R8 — No wire/protocol change (SC-007 guard)

**Decision**: None of the above touches `internal_channel.py`'s `IN2N` preamble, the NCFED framing, or eN2N. Enforcement is applied at **launch** (sandbox), **execution** (guard), **audit** (GAIT), and **routing preflight** — all Border/member-local. The 44 eN2N regression tests + 45 iN2N tests are run unchanged as the guard.

**Rationale**: The freeze is a hard constraint (052/053 + 056). Keeping enforcement out-of-band of the wire is what lets production controls be added without risking the federation with Nick and Byrn.

**Alternatives considered**: Signaling posture over the wire to peers (unnecessary; posture is a local operator concern, and it would change the protocol).
