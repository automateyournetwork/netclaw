# Architecture decision: SuzieQ as the Convergence state-history plane (scale tier)

**Status**: Proposed 2026-08-01 (operator direction: target larger-scale
deployments)
**Spec**: [`spec.md`](./spec.md) US12 / FR-043–FR-050 · tasks T158–T170
**Relates to**: [`otel-convergence.md`](./otel-convergence.md) (ingest hub —
this does **not** supersede it), [`telemetry-setup.md`](./telemetry-setup.md)
(inventory + apply pipeline, reused wholesale),
[`investigation-policy.md`](./investigation-policy.md) (T0/T1/T2 — where SuzieQ
earns its keep)

## Decision

Convergence adds **SuzieQ** as an optional **state-history plane** for
larger-scale deployments — a fourth data class alongside metrics, logs, and
intended state:

```text
   ┌──────────────┬──────────────────────────────────┬───────────────────────┐
   │ Data class   │ Collector                         │ Answers               │
   ├──────────────┼──────────────────────────────────┼───────────────────────┤
   │ Numeric TS   │ otel-collector (SNMP), blackbox,  │ "how much / how many, │
   │              │ unifi-exporter                    │  over time"           │
   │ Logs         │ otel-collector (syslog), promtail │ "what did it say"     │
   │ Intended     │ Nautobot / NetBox                 │ "what should be"      │
   │ **State hx** │ **SuzieQ poller → parquet lake**  │ **"what WAS the BGP/  │
   │              │                                   │  route/MAC/ARP/LLDP   │
   │              │                                   │  state at T-15m"**    │
   └──────────────┴──────────────────────────────────┴───────────────────────┘
```

It ships **off by default** as component `convergence-suzieq`, excluded from
`PROFILE_CONVERGENCE`, and is only recommended above a documented scale
threshold.

## Why now (and why not before)

The prior assessment against the home fleet stands and is **not** being
reversed: on 3 Cisco access switches, a pfSense, and some UniFi APs, SuzieQ
duplicates what the OTel SNMP path already provides and adds a fourth store for
little gain. That assessment is fleet-size dependent, and the operator target
has changed to larger-scale deployments, where the calculus inverts.

The gap it closes is specific and currently unaddressed:

**T2 investigation reaches for live state at investigation time.** By the time
an alert traverses Alertmanager → alert-receiver → policy resolution → budget
check → agent spin-up, a transient has often healed. Nautobot gives intended
state, Prometheus gives numeric series, pyATS gives *now*. Nothing in the stack
answers "what did the L2/L3 adjacency state look like 15 minutes before this
fired." That question is the core of most fabric root-cause work, and it scales
in value with protocol complexity (BGP/EVPN/VXLAN/MLAG) — exactly what a
larger deployment has and the home lab does not.

## What was already built, and what was missing

SuzieQ was **not** unexplored. `specs/001-suzieq-mcp-server` (2026-03-26) is
closed at 28/28 tasks and shipped:

| Artifact | Path | State |
|---|---|---|
| MCP server (5 tools) | `mcp-servers/suzieq-mcp/server.py` | built |
| REST client | `mcp-servers/suzieq-mcp/suzieq_client.py` | built |
| Skill | `workspace/skills/suzieq-observability` | built, user-invocable |
| Gateway registration | `config/openclaw.json` | present |
| iN2N member | `migration-staging/members/suzieq/` | scoped, model-pinned |
| Catalog entry + profiles | `scripts/lib/catalog.sh` | in RECOMMENDED / LABS / OBSERVABILITY |

Two things were missing, and both are the actual work:

1. **No SuzieQ server anywhere.** No container, no pod, `SUZIEQ_API_URL`
   commented out in `.env`. Spec 001 scoped "wrap the REST API" and never scoped
   "deploy the poller." A client was built and never given a backend — so
   `suzieq` sitting in `PROFILE_RECOMMENDED` today advertises capability that can
   only return connection errors. That is a defect independent of this phase
   (T158).
2. **No convergence integration.** Zero references under `deploy/convergence/`;
   absent from `PROFILE_CONVERGENCE`.

## Verified facts (measured, not assumed)

### The MCP server has no payload controls — this blocks everything

Read directly from `server.py` / `suzieq_client.py`:

- **No row limit.** No `limit`, `max_rows`, or slice anywhere in the response
  path. The only `[:200]` slices in the codebase are on HTTP error strings
  (`suzieq_client.py:191,264`).
- **No response size ceiling.** Nothing measures or truncates the payload.
- **`columns` defaults to all columns** (`server.py:256` — "default: all
  columns").

At home scale this is invisible. At the target scale it is a context bomb:
`suzieq_show table=route` returns every route from every device in one
unbounded payload, and `mac` / `arpnd` behave the same way. Those are precisely
the tables most wanted during triage.

This bypasses Phase 9's entire budget model. `budgets.max_tokens: 200000` on T2
is enforced by the policy engine around the session, but a single unbounded tool
result can consume the window before the second turn. **SuzieQ must not be
exposed to the T2 allowlist until T158 lands.**

### To verify during PR0 (not yet measured — do not treat as fact)

The following are load-bearing for scope and are explicitly unverified:

| Claim to test | Why it matters | How |
|---|---|---|
| IOS-XE table coverage quality (`bgp`, `route`, `mac`, `arpnd`, `lldp`, `vlan`, `interface`) | SuzieQ's strongest support is Cumulus/SONiC/Arista/Junos/NXOS; IOS-XE has historically been the weaker path | Stand up a poller against 2 lab Catalysts, diff table completeness vs `pyats` parsed output |
| pfSense/FreeBSD support | Believed **out of scope** for SuzieQ entirely. If so, the firewall stays a metrics/logs-only citizen and the docs must say so | Attempt inventory entry; record result |
| Upstream health | OSS `netenglabs/suzieq` PyPI/stable-release signals cluster around May 2025 (~14 months stale as of now), while differentiated work (NetBox bidirectional sync et al.) moves into **SuzieQ Enterprise** under Stardust Systems. A slow OSS tier with features migrating to a paid edition is a poor dependency for a product you intend to sell | Check actual commit/issue activity on the repo, not search snippets. If genuinely dormant, pin a known-good version and record it as accepted risk |
| Poller resource footprint at target scale | Sizing guidance for the component README | Measure RSS + parquet growth/day at N devices |

If IOS-XE coverage proves thin, this phase still has value on
multi-vendor/fabric deployments but should be documented as vendor-conditional.

## Integration point 1: one inventory, four renders

The cheapest and most important decision. `device_telemetry.snmp.targets`
already carries `name`, `ip`, `role`, `vendor`, `template`, and
[`telemetry-setup.md`](./telemetry-setup.md) already defines
`manual | nautobot | netbox | from-yaml` input modes feeding it. SuzieQ needs
the same devices in its own inventory format.

So extend `render-convergence-telemetry.py` with a fourth output rather than
introducing a second inventory:

```text
convergence.yaml  (single source of truth for the device list)
        │
        ├─→ Prometheus scrape fragment        (existing)
        ├─→ OTel SNMP receiver blocks         (existing, T154)
        ├─→ device config checklist           (existing)
        └─→ SuzieQ inventory + namespace map  (NEW — T161)
```

Same managed-section markers, same `convergence-telemetry-apply.sh`, same
idempotency contract, and `check-config-drift.sh` extends to cover it. Nautobot
mode then feeds SuzieQ for free with no manual IP typing and no drift between
the metrics inventory and the state inventory.

New config block, additive:

```yaml
device_telemetry:
  snmp:
    # ... unchanged ...
  state:
    suzieq:
      enabled: false          # scale tier — default off
      namespace: home         # SuzieQ namespace; multi-site → one per site
      poll_period: 5m
      retention_days: 90      # parquet lake retention
      # credentials: env only — SUZIEQ_DEVICE_USER / SUZIEQ_DEVICE_KEY_PATH
      # transport: ssh (SNMP collection MUST stay off — see FR-045)
      exclude_roles: [firewall]   # e.g. if pfSense proves unsupported
```

**Inventory reuse is not optional.** A separate SuzieQ inventory would drift
from the SNMP/syslog inventory within one change cycle, and the two would then
disagree about what the fleet is — which is the failure mode the Phase 10 apply
pipeline exists to prevent.

## Integration point 2: complements FR-036, does not violate it

FR-036 mandates a single OpenTelemetry Collector for device **ingest**, meaning
syslog and SNMP. SuzieQ collects a different data class over a different
transport (SSH/REST), so it is not a second ingest hub.

That distinction must be written down, because the next person reading
`otel-convergence.md` will otherwise correctly conclude that adding SuzieQ
reverses the collector-consolidation decision.

The hard constraint: **SuzieQ's own SNMP collection path stays off.** Exactly
one thing polls SNMP in this architecture and it is the OTel Collector. Two SNMP
pollers against the same fleet means duplicated device load, duplicated
credentials, and two sources of truth for interface state. Pin SuzieQ to
SSH/REST in the rendered config, and assert it in the smoke test (FR-045).

## Integration point 3: credential blast radius — the real cost

This is the strongest objection to the whole phase and it is not solvable, only
managed. Today the stack needs:

| Today | Grants |
|---|---|
| SNMP read-only community | read of a fixed OID set |
| Syslog destination | nothing (devices push) |
| Blackbox / UniFi API key | HTTP probe / controller read |

SuzieQ needs **login credentials to every device in the fleet**, held by a
long-running poller process. That is a material escalation in blast radius, and
on K3s it becomes a Secret containing device logins.

Required controls:

- Dedicated **read-only service account** per platform. Never a shared admin
  credential, never the account a human uses.
- Credentials via env / Vault references only. The **rendered inventory must
  never contain a secret** — same rule as `SNMP_COMMUNITY` today.
- **Per-namespace credential separation** so one compromised namespace is not
  the whole estate. This is the main reason to map site → namespace rather than
  running one flat namespace.
- The wizard must **state plainly** what it is asking for before prompting, so
  enabling this is an informed decision rather than a surprise.
- Reachability path reviewed against the operator's network-change-safety rules
  before deployment. The poller is read-only by design, but it is a new
  persistent SSH consumer on the management path and its account scope deserves
  explicit sign-off. In this environment the management network is explicitly
  off-limits for configuration change, so the poller's account and reachability
  must be provisioned by the operator rather than by tooling.

## Integration point 4: where it pays for itself — T1 and T2

This is the part that justifies the phase, and it is a cost **reduction**, not
just added capability.

Today, "what was the L2/L3 state around this alert" forces escalation to pyATS
or a domain member: SSH to devices, at investigation time, retrieving current
state that may have already healed. SuzieQ answers the same question from the
lake in one read-only call — no device touch, no member handoff, and the answer
is historically correct rather than post-hoc.

**Thin T2 profile.** Add `suzieq-mcp__*` to `tools.allow` in
`deploy/convergence/config/alert-agent.example.json`. It fits the FR-018 thin
profile precisely: read-only, single-purpose, no config authority.

**T1 becomes genuinely useful for the first time.** T1 permits
`max_tools: 0–1` and `max_completion_tokens: 4000`. A single bounded
`suzieq_show view=changes start_time=-15m columns=<pinned>` fits inside that
envelope. Today T1 is a summarizer with no data access, so most alerts are
either blind at T0 or expensive at T2. SuzieQ gives a large class of alerts real
state context at T1 pricing — which is the cheapest capability gain available in
the current design.

This depends entirely on T158. Without payload caps, the same call is a context
bomb and T1's token ceiling is meaningless.

**Skill discipline.** `workspace/skills/suzieq-observability` must be rewritten
to enforce, not merely permit:

- always a bounded `start_time` (relative windows), never an open query
- `view=changes` preferred over `latest` over full-table dumps
- explicit `columns` on every call — never rely on the all-columns default
- `summarize` first to size a problem, `show` only to inspect a narrowed set

## Integration point 5: staleness is the failure mode that matters

**A stale SuzieQ lake is worse than no SuzieQ.** If the poller has been dead for
a week, the agent will confidently report week-old adjacency state as current and
produce a wrong root cause with high conviction — then write it to the diary and
into RAG as a prior. That contaminates future investigations.

Two required guards:

1. **Poller health is alertable.** Scrape the `sqPoller` table into Prometheus
   and ship `SuzieQPollerDown` / `SuzieQPollerStale` in the standard alert pack,
   with `investigate` labels per
   [`docs/CONVERGENCE-ALERT-SAFETY.md`](../../docs/CONVERGENCE-ALERT-SAFETY.md).
2. **Every MCP response carries data freshness.** The server stamps the newest
   timestamp per table/device into the response envelope, so the model can see
   it is reasoning over old data instead of assuming currency. This is a change
   to the MCP server, bundled with T158.

## Integration point 6: what it unlocks beyond triage

Three capabilities the current stack cannot provide at all:

| Capability | Tool | Use |
|---|---|---|
| Alert enrichment with observed state | `suzieq_show` | alert-receiver attaches state delta at ingest, before any LLM decision |
| Pre/post change validation | `suzieq_assert` | wrap golden-config pushes; assert BGP/OSPF/interface health before and after |
| Reachability triage across a fabric | `suzieq_path` | forwarding-path trace without hop-by-hop device login |

`suzieq_assert` is the most interesting of the three, because it pairs directly
with `nautobot-golden-config-mcp` remediation: assert observed health, push
intended config, assert again. That closes a validation gap the current stack
handles by hand.

## Deployment shape

Follows the `device-snmp` adapter pattern exactly:

```text
deploy/convergence/adapters/suzieq/
  README.md                  # scale guidance, credential model, sizing
  inventory.yml.tmpl         # rendered from convergence.yaml
  suzieq-cfg.yml.tmpl        # poller config; SNMP path pinned off
docker-compose.yml           # profile ["suzieq"]: poller + REST API
                             # named volume for the parquet lake
k8s/components/suzieq/       # Deployment(s) + PVC + Secret ref + Service
```

Ship Docker and K3s **together**. T156 found the K3s overlay three generations
behind Docker and shipping a broken stack; deferring K3s parity again repeats a
known failure.

## Scale threshold guidance (documented, not enforced)

Turn it on when **any** of these holds:

- more than ~25 polled devices
- any BGP / EVPN / VXLAN / MLAG fabric
- multi-site (namespace-per-site becomes the credential boundary)
- an existing SuzieQ deployment in the customer environment

Below that, the OTel SNMP path plus on-demand pyATS already covers it and SuzieQ
is net negative: a fourth store, a new credential surface, and a poller to keep
alive for questions a 3-switch network does not raise.

## Risks

| Risk | Mitigation |
|---|---|
| **Unbounded tool payloads blow the context window** | T158 lands first: `max_rows` default ~200, byte ceiling, per-table default columns, visible truncation metadata. SuzieQ stays off the T2 allowlist until then. |
| **Truncation hides data and the model concludes the table is small** | Truncation must be explicit in the response envelope (`truncated: true`, `rows_returned`, `rows_available`), never a silent slice. Same principle as FR-035's no-silent-drop rule. |
| **Stale lake produces confident wrong answers that poison RAG** | `sqPoller` scrape + `SuzieQPollerStale` alert + per-response freshness stamps (T164, T158). |
| **Device credentials in a long-running poller** | Read-only service account, env/Vault only, per-namespace separation, wizard disclosure, reachability sign-off. Accepted cost, explicitly recorded. |
| **Two SNMP pollers against one fleet** | SuzieQ SNMP path pinned off in the rendered config; asserted in `smoke-suzieq.sh` (FR-045). |
| **Inventory drift between metrics and state planes** | Single inventory, four renders, one apply script, extended drift guard. No second inventory permitted. |
| **IOS-XE table coverage weaker than assumed** | PR0 measures it against lab Catalysts before any deploy work. If thin, phase becomes vendor-conditional and the docs say so. |
| **Upstream OSS tier dormant / features moving to Enterprise** | PR0 verifies real repo activity. If dormant, pin a known-good version, record accepted risk, and do not let any provisioned board panel depend on SuzieQ (FR-031 already forbids this for non-installable collectors — SuzieQ *is* installable here, but a dormant dependency is a shipping risk worth stating). |
| **`suzieq` in `PROFILE_RECOMMENDED` today is a broken client** | T159 gates it on `SUZIEQ_API_URL` or removes it from the profile. Independent of the rest of this phase. |

## Non-goals

- Replacing the OTel Collector, or moving any SNMP/syslog collection to SuzieQ.
- Replacing pyATS. SuzieQ answers history; pyATS answers *now* and runs commands.
  Deep device work still escalates to the pyATS domain member.
- Auto-remediation from `suzieq_assert` results. Assertions inform; they do not act.
- SuzieQ Enterprise features (NetBox bidirectional sync, etc.).
- Making SuzieQ a default Convergence component, or a dependency of any
  provisioned Grafana board.
- Backfilling historical state. The lake starts empty at deploy.

## Phased delivery

Hardening first: it is the prerequisite for every downstream integration and it
stands alone as a bug fix.

| Phase | Tasks | Ends with |
|---|---|---|
| **0 Spec + measure** | T158–T160 | This doc + spec US12/FR-043–FR-050/SC-020–SC-023; MCP payload caps + freshness stamps shipped; broken-profile gate fixed; IOS-XE/pfSense coverage and upstream health measured |
| **1 Inventory render** | T161–T162 | `render-convergence-telemetry.py` emits SuzieQ inventory from the existing target list; drift guard extended; apply idempotent |
| **2 Docker adapter** | T163–T165 | `--profile suzieq` brings up poller + REST; `sqPoller` scraped; staleness alerts in the pack |
| **3 K3s parity** | T166 | `components/suzieq` with PVC + Secret; all overlays build and dry-run clean |
| **4 Agent wiring** | T167–T168 | `suzieq-mcp__*` in the thin `alert` allowlist; skill rewritten for bounded queries; T1 state-context path documented |
| **5 Wizard + installer** | T169 | `convergence-suzieq` catalog component, credential disclosure prompt, scale guidance in quickstart |
| **6 Assert/validation** | T170 | `suzieq_assert` paired with golden-config push as a documented pre/post-change workflow |

Phases 1–6 are all gated on Phase 0. Nothing touches the investigation path
before T158.

## Tasks

See `tasks.md` Phase 12 (T158–T170).
