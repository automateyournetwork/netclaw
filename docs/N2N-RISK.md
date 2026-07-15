# A Risk of NetClaws — Internal Federation (iN2N)

> A **risk** is the (real) collective noun for a group of lobsters. NetClaw is a
> lobster. So a coordinated group of NetClaws is **a risk of NetClaws** — and,
> for a security-adjacent product, the pun is intentional.

iN2N (internal NetClaw-to-NetClaw federation) lets **one operator** run a group
of **focused, specialized NetClaws** — a *risk* — coordinated by a single
**Border Claw**. You only ever talk to the Border; it routes each request to the
member claw that owns the capability and returns the result. It is the internal
counterpart to **eN2N** (external federation between *different* operators over
the NCFED mesh — see [N2N-PEERING-NETCLAWS.md](../N2N-PEERING-NETCLAWS.md)).

## Why

One monolithic NetClaw carrying 190+ skills is expensive (huge context per turn)
and blast-radius-wide (every credential in one process). A risk splits that into
small specialists:

- **Focus & token economy** — a CML claw carries ~5 skills, not 190; a pyATS
  claw carries only pyATS. Each member's context stays small and cheap.
- **Least privilege** — each member gets *only* its integration's secrets. A
  compromised CML claw literally has no path to your Azure or firewall creds.
- **One door, one audit trail** — the Border is the single interface, the single
  external identity, and the single place every action is logged.

## The model

```
                    (you talk only to the Border)
                              │
                    ┌─────────▼─────────┐        eN2N (NCFED mesh)
   external ◄───────┤    BORDER CLAW    ├───────► other operators' risks
   peer risks       │  gateway · comms  │         (Border-to-Border only)
                    │  routing · audit  │
                    └───┬───┬───┬───┬───┘
                iN2N (internal transport — members dial OUT)
                    │   │   │   │
                  ┌─▼┐┌─▼┐┌─▼┐┌─▼┐   ... each a focused, scoped member claw
                  │cml││pyats││azure││ise│   (CML claw, pyATS claw, Azure claw, …)
                  └──┘└────┘└─────┘└───┘
```

- **Standalone** — a classic NetClaw is simply "a risk of one, its own Border".
- **Border Claw** — the only claw with the gateway and comms (Slack/Discord/
  Webex/Twilio/Twitter/PagerDuty/ServiceNow), routing, audit/GAIT, memory, and
  humanrail. Deliberately carries **no** domain skills — its job is to broker.
  Exactly one per risk. It also runs eN2N (external federation) if enabled.
- **Member Claw** — a tightly-scoped specialist (one vendor/tool per claw). Dials
  the Border, runs delegated tasks over only its scoped MCPs, never talks to the
  outside world. Base floor on every member: iN2N runtime + self-status + memory
  + GAIT + humanrail escalation.

## Key properties

- **Hub-and-spoke, no mesh.** Members **dial outbound** to the Border's one
  reachable endpoint — loopback when co-located, or a private-network / overlay-
  VPN / tunnel address when distributed across hosts/clouds/datacenters. No
  inbound ports on members, no ngrok, **no iBGP/mesh** — the Border is the hub.
- **Trust = pinned key, not consent.** A member enrolls once with a single-use
  token and its own runtime-generated self-signed key, which the Border pins
  (trust-on-first-use). No CA. eN2N's mutual-consent model applies only *between*
  risks, at the Border boundary.
- **One external identity.** To a peer risk, the whole risk appears as one
  identity (the Border). Member identities/endpoints/topology never leak. The
  Border advertises the **aggregate** of member capabilities under the risk (so a
  peer learns "this risk can do CML, pyATS, Azure…") without exposing structure.
- **Any provider/model per claw.** Each member is its own OpenClaw *embedded*
  agent (`openclaw agent --local --model <provider/model>`) — Anthropic, OpenAI,
  Google, or **local/Ollama**, mixed freely. The Border can reason on a flagship
  model while members run cheaper/faster ones.
- **Hybrid runtime (cold/on-demand).** A hot set stays always-on; other members
  idle-exit when quiet and the Border **cold-starts** them on the next route
  (spawns, waits for enrollment, delegates). Big resource/token savings.
- **Security posture is a risk mode — actually enforced (feature 057).**
  `N2N_RISK_MODE=testing` (fast iteration, no guards) vs `production`, which
  **enforces fail-closed**: members run inside the [OpenShell](DEFENSECLAW.md)
  sandbox, their model I/O is DefenseClaw-guarded and their skills/MCPs are
  component-scanned, and every federation event is committed to an immutable GAIT
  git trail. The Border reports an **honest posture** and never claims full
  production while a control is missing. See [Production mode](#production-mode-feature-057).
- **Enforced scope.** A member refuses out-of-scope work even from its Border.

## Roles at install

The installer asks: **standalone**, **Border**, or **Member**. A Border chooses
`eN2N` / `iN2N` / `both`. A Member points at its Border and enrolls. This is the
**primary** path — a fresh install stands up a risk directly; an existing
monolith can also be *migrated* into one (below).

## Profiles (env-gated, one claw per vendor/tool)

Member profiles are **derived from your installed skill catalog** and **gated on
their backend being configured** — you are never offered a member you can't run.

```bash
python3 scripts/in2n-profiles.py list          # members you can run right now
python3 scripts/in2n-profiles.py list --all     # + dormant (skills present, no backend)
python3 scripts/in2n-profiles.py show cml        # skills in the cml member
```

Granularity is per vendor/tool: `cml`, `containerlab`, `pyats`, `ipfabric`,
`suzieq`, `batfish`, `forward`, `gtrace`, `packet`, `itential`, `aap`, `nso`,
`aci`, `catalyst-center`, `f5`, `meraki`, `sdwan`, `ise`, `asa`, `checkpoint`,
`paloalto`, `fortimanager`, `zscaler`, `claroty`, `nmap`, `nvd`, `fwrule`, `aws`,
`azure`, `gcp`, `netbox`, `nautobot`, `infrahub`, `infoblox`, `github`. Utilities
like visualization (`viz`) stay grouped. DefenseClaw + OpenShell are the
production-mode security layer.

## Operating a risk

On the Border (MCP tools, or `netclaw risk …` / the `netclaw` TUI):

| Action | Tool / command |
|--------|----------------|
| Risk status (role, stacks, members) | `n2n_risk_status` · `netclaw risk status` |
| List members (scope, state, live) | `n2n_member_list` · `netclaw risk members` |
| Member health / quarantine alerts | `n2n_member_health` · `netclaw risk health` |
| Provision a member (+ token) | `n2n_member_add` · `netclaw risk add <profile> <name>` |
| Issue an enrollment token | `n2n_enroll_token` · `netclaw risk token` |
| Route a request to a member | `n2n_route` · `netclaw risk route "<request>"` |
| Remove a member (unpin) | `n2n_member_remove` · `netclaw risk remove <id>` |
| Production posture (enforced/degraded/testing) | `n2n_posture` |
| Fault isolation (daemon/member/backend) | `n2n_faults` |

Members run the lightweight launcher `scripts/in2n-member.py` (dial + enroll +
execute; `--idle-exit N` for cold/on-demand).

## Production mode & the security layers (feature 057)

`N2N_RISK_MODE=production` makes the risk **enforce**, fail-closed — it is not a
label. Three enforcement controls are each probed **live** and aggregated into an
honest posture that the Border **never** overstates.

### The layers, and how each is wired

| Layer | Kind | How it's wired | Effect if unavailable |
|-------|------|----------------|-----------------------|
| **Member sandbox — host-level kernel confinement** | containment | Each member runs as a **`systemd --user` unit hardened** with `NoNewPrivileges`, `ProtectSystem=strict` (read-only system), `InaccessiblePaths=~/.openclaw/.env` (the operator's master secrets are invisible to the member), `PrivateTmp`, and — on a native-Linux manager — syscall/namespace/address-family restrictions. On-demand members are cold-started inside a transient hardened `systemd-run` unit. *(OpenShell containers were evaluated and rejected for live-infra members: they are empty, network-egress-denied sandboxes — a member that must reach real devices/APIs can't run in one. Host confinement keeps the member's real tools/network while confining it.)* | delegation **refused** (no unconfined run) |
| **Model-guard — DefenseClaw LLM guardrail proxy** | containment | `defenseclaw setup guardrail` stands up a Go proxy (`:4000`) and patches OpenClaw to route the model through it; **every prompt/response is inspected**. Availability = `defenseclaw` present **and the proxy reachable** (started via `defenseclaw-gateway start`). Members' skill/MCP sets are also **component-scanned** (`defenseclaw skill scan`) before they run. | delegation **refused** (no unguarded run) |
| **Audit — GAIT immutable git trail** | audit | Every delegation/enrollment/removal/quarantine is committed to a git repo at `~/.openclaw/n2n/gait/` (append-only, never rewritten), cross-referenced to the SQLite audit row. Emitted on **both** the Border and the member side. | delegation **runs but flagged `audit-degraded`** |
| **Least-privilege secrets** | containment (by construction) | Each member's `.env` is a scoped slice — only its integration's secrets. Combined with the sandbox hiding the master `.env`, a compromised member has no path to another member's keys. | — |
| **Durable runtime** | resilience | Mesh daemon + always-on members are `systemd --user` services (`Restart=always`, survive churn + reboot), generated repeatably by `scripts/in2n-services.py`. | — |
| **Honest posture + fault isolation** | truth | Posture (`testing` / `production — enforced` / `production — DEGRADED (<controls>)`) surfaced via `n2n_posture`, the operator heartbeat, and the HUD; `n2n_faults` distinguishes daemon-down / member-down / backend-unreachable. | — |

The Border **never** reports `enforced` while a control is missing. `N2N_STRICT_ALL=1`
blocks on *any* gap (including audit). Per-control policy: a **containment** gap
(sandbox or model-guard) refuses delegations fail-closed; an **audit-only** gap
(GAIT) runs but flags every result `audit-degraded`.

> **Operational note:** the DefenseClaw guardrail sidecar (the model-guard proxy)
> runs as a **durable `systemd --user` service** (`defenseclaw-sidecar.service`,
> `Restart=always`), generated + enabled by `scripts/in2n-services.py` alongside the
> mesh daemon and members — so model-guard survives a reboot with no manual step.
> One-time prerequisite: `defenseclaw setup guardrail` (patches OpenClaw to route
> model I/O through the proxy). If the proxy is ever down, posture honestly reports
> `production — DEGRADED (model-guard missing)` and containment fail-closes.

```bash
# ask the Border its posture (MCP), or:
curl -s http://127.0.0.1:8179/n2n/posture      # {"summary":"production — enforced", ...}
curl -s http://127.0.0.1:8179/n2n/faults       # daemon / member / backend fault isolation
```

**Durable runtime.** The mesh daemon and always-on members run as `systemd --user`
services (`Restart=always`, survive session/terminal churn + reboot), generated
repeatably — one unit per always-on member (single-owner: the cold-start path
never double-launches a service-managed member):

```bash
python3 scripts/in2n-services.py generate   # mesh daemon + DefenseClaw sidecar + one unit per always-on member
python3 scripts/in2n-services.py enable      # daemon-reload + enable --now
python3 scripts/in2n-services.py status      # per-unit active/failed
```

The generator emits, and `enable` starts, all durable units: `netclaw-mesh.service`,
`defenseclaw-sidecar.service` (model-guard proxy), and one
`netclaw-member-<id>.service` per always-on member — everything needed for
`production — enforced` to come back on its own after a reboot.

On a non-systemd host the generator degrades gracefully and posture reports the
durable-runtime aspect accordingly. Full detail:
[specs/057-in2n-production-enforcement](../specs/057-in2n-production-enforcement/).

## A2A capability cards (what a peer/member learns)

Every claw advertises an **A2A capability card** (the federation inventory) to
consenting peers. Feature 057 enriched the card so a neighbour understands not just
*what* a claw can do but its **security posture** and **reasoning capability**:

```jsonc
{
  "identity": "as65001-4.4.4.4",
  "skills": [ ... ], "mcp_servers": [ ... ], "badges": [ ... ],
  "posture": {                      // NEW (057): the risk's production posture
    "mode": "production", "state": "enforced",
    "summary": "production — enforced",
    "controls": { "sandbox": true, "model-guard": true, "audit": true }
  },
  "llm": {                          // NEW (057): reasoning capability, no secrets
    "primary_model": "claude-opus-4-8",
    "guarded": true,                // routed through the DefenseClaw guardrail
    "note": "Border reasoning model; member claws run their own per-specialty tiered models"
  }
}
```

- **Posture** lets a peer see whether the claw it's delegating to is actually
  enforcing (sandbox + model-guard + immutable audit) or `testing`/`degraded`.
- **LLM** lets up/downstream claws gauge a neighbour's reasoning capability and
  route accordingly — the model family/tier and whether it's guardrail-routed.
  **No credentials, no per-member topology** (a Border advertises its own model and
  notes that members are tiered).

These render in the HUD too: the local risk panel shows posture + controls + model;
a federated peer's panel shows its advertised posture and model.

## Token / context economy — the whole point

The monolith carried **everything in one context, every turn**. A risk carries a
lean Border that routes and members that each carry a sliver. Measured on this repo:

| | Monolith (one claw) | Border (router) | A member (e.g. IP Fabric) |
|---|---|---|---|
| Domain skills in context | **~194** | **0** (broker skills only) | its base floor + **~3** specialty (risk avg 2.7) |
| MCP servers loaded | **~37–52** | **5** (n2n + memory + comms) | **2** (its vendor + memory) |
| Tool schemas in context | **hundreds–thousands** (full catalog ≈ 2,755 tools across the estimate) | **~32 broker tools** + memory | just its vendor's tools (e.g. cml ≈ 24, ise ≈ 16, netbox ≈ 12) |

**What that means for context/tokens** (illustrative model at ~150 tokens per tool
schema + skill preamble):

- The monolith hauled the **entire** tool catalog into every turn — on the order of
  **10⁵ tokens of tool/skill schemas** before the user even speaks, diluting the
  model's focus across 194 skills.
- The Border's per-turn tool context is just its **broker set (~40 tools ≈ ~6K
  tokens)** — it reasons about *routing*, not about CML or Azure internals.
- Each member's per-turn tool context is just **its own slice (~tens of tools ≈
  ~4–8K tokens)** — a focused specialist, not a generalist.

Net: **roughly a 15–30× reduction in per-claw tool-schema context** versus the
monolith, and — just as important — each claw's model is **focused** on one job
instead of being diluted by ~190 irrelevant capabilities. The token economy also
compounds with **tiered models** (Border on Opus for routing/reasoning; members on
Sonnet/Haiku or local Ollama for their narrow task).

*(Counts are from this repo's live catalog — 194 skills, 52 registered MCP servers,
~2,755 estimated tools — and the live `johns-risk`: 1 Border + 27 members, avg 2.7
specialty skills each. The token figures are an estimate/model, not a measured
count; the structural reduction is exact.)*

## Live production results (2026-07-13)

Validated end-to-end on the running Border `johns-risk`:

- Posture flips **`production — DEGRADED` → `production — enforced`** as controls
  come up (it caught a real systemd `PATH` misconfig and *refused* to claim enforced
  until fixed — honesty working).
- A real production delegation to the **confined** IP Fabric member returned live
  data — *"11 snapshots total in IP Fabric (8 loaded, 3 unloaded)"* — while the
  member ran under systemd host-confinement and the DefenseClaw guardrail proxy was
  up; **GAIT committed on both Border and member sides**.
- The mesh with **Nick (AS 65007)** and **Byrn (AS 65099)** stayed **federated**
  throughout every restart (frozen eN2N core intact).
- 120/120 `tests/n2n/` pass (44 eN2N regression + 45 iN2N/056 + 31 new 057).

## Migrating a monolith into a risk

`scripts/in2n-migrate.py` is **generate-only** — it never stops/starts/removes
anything. It reads your existing `~/.openclaw/.env` and produces, in a
gitignored `migration-staging/`, a **least-privilege `.env` slice** + launcher
per member, a `border.env.additions`, and a step-by-step **`RUNBOOK.md`** for a
**parallel cutover** (backup → promote to Border alongside the running monolith →
bring up members one at a time → move comms to the Border last → decommission the
monolith last, with a rollback path).

```bash
python3 scripts/in2n-migrate.py --risk my-risk --border-endpoint 127.0.0.1:11790
# review migration-staging/RUNBOOK.md — then run it by hand
```

## Environment

See `.env.example` (`N2N_ROLE`, `N2N_RISK_NAME`, `N2N_ENABLED_STACKS`,
`N2N_IN2N_PORT`, `N2N_BORDER_ENDPOINT`, `N2N_QUARANTINE_THRESHOLD`, and the member
vars `N2N_MEMBER_ID` / `N2N_MEMBER_MODEL` / `N2N_MEMBER_SCOPE` /
`N2N_ENROLLMENT_TOKEN` / `N2N_IDLE_EXIT_S`). Production enforcement (feature 057):
`N2N_RISK_MODE` (`testing` | `production`), `N2N_STRICT_ALL` (block on any missing
control), `N2N_GAIT_DIR` (immutable GAIT git trail location).

## Proven live — the full recipe (and gotchas)

Decomposing a real monolith into a risk surfaced details worth writing down:

- **A member runtime** = a *scoped OpenClaw home* (`scripts/in2n-member-home.py`):
  filtered `mcp.servers`, **comms plugins stripped** (slack/webex crash
  `openclaw agent --local`), a **direct model provider registered at the member's
  tier** (and whitelisted in `agents.defaults.models`), workspace shared. The
  member process is `scripts/in2n-member.py` (dial + enroll + execute; `--idle-exit`
  for cold/on-demand), launched **detached** (`setsid`) so it survives.
- **Slimming a Border is TWO things, not one:** (1) trim its `mcp.servers` to the
  broker set, AND (2) give it its **own workspace + Border persona**
  (`scripts/in2n-border-workspace.py`) — broker skills only + a SOUL that says
  "I'm the Border, I DELEGATE domain work to members via `n2n_route`." Without (2)
  the Border still carries ~190 skill files and answers like the monolith instead
  of routing. Point `agents.defaults.workspace` at the Border workspace + restart
  the gateway.
- **Models:** each claw registers a **direct provider** (any: Anthropic / OpenAI /
  local Ollama) at its tier — Border=Opus, heavy members=Sonnet, trivial=Haiku.
  If your model routes through a proxy (e.g. a DefenseClaw LLM gateway) make sure
  it's running, or register a direct provider so a claw isn't blocked by a down
  proxy. `agents.defaults.model.primary` needs a matching `models.providers[...]`.
- **Deploy the `n2n-federation` skill** to a Border's workspace — without it the
  Border's agent doesn't know the `n2n_*` routing tools exist.
- **On-demand cold-start** requires members to be *routable while `provisioned`*
  (the router treats provisioned members as candidates → `ensure_member_up`
  spawns them on first route).

## See also

- [N2N-PEERING-NETCLAWS.md](../N2N-PEERING-NETCLAWS.md) — eN2N (external peering)
- [N2N-RISK-MIGRATION-FOR-PEERS.md](N2N-RISK-MIGRATION-FOR-PEERS.md) — for peers
  (Nick/Byrn): what changed and whether you need to do anything
- [DEFENSECLAW.md](DEFENSECLAW.md) — the production-mode security layer
- **NCFED protocol spec (IETF Internet-Draft):** [`docs/ietf/draft-capobianco-ncfed-00.md`](ietf/draft-capobianco-ncfed-00.md) — the wire protocol (discrimination, handshake, framing, trust models) written up as `draft-capobianco-ncfed-00` (Experimental) for IETF `agentproto`
- Spec: `specs/056-in2n-internal-federation/` (the risk) ·
  `specs/057-in2n-production-enforcement/` (production enforcement + durable runtime) ·
  `specs/059-ncfed-internet-draft/` (the NCFED I-D)
