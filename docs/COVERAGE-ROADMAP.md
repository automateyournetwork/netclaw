# NetClaw Coverage Roadmap

**Created:** 2026-07-30
**Purpose:** Single reference for closing identified capability gaps in NetClaw's MCP/skill coverage.
**Method:** One spec at a time, in order. Fix the foundation (R0) before adding anything new.

Derived from a landscape scan (2026-07-30) of vendor/community MCP registries, `awesome-mcp-servers`,
Itential's 56-server network-automation guide, Cisco/Juniper/HPE official releases, `anthropics/skills`,
and the IETF datatracker.

---

## How to use this document

1. Work **top to bottom**. Roadmap items are ordered by dependency, then by value-per-effort.
2. One roadmap item = one spec = one branch. Do not batch.
3. When you cut the branch, fill in the **Spec #** column in the status board below.
4. Tick the checkboxes inside a roadmap item as you complete them. An item is `DONE`
   only when every checkbox under it is ticked.
5. Move the item's row in the status board to reflect its state.

> **Shared-tree warning:** other agents switch branches in this checkout. Verify the branch before
> committing, and remember new `mcp-servers/` subdirectories need a `.gitignore` negation entry.

### Status legend

| Mark | Meaning |
|------|---------|
| `NOT STARTED` | No spec, no branch |
| `IN FLIGHT` | Spec written and/or branch open |
| `DONE` | All checkboxes ticked, merged to `main` |
| `DEFERRED` | Consciously postponed — reason recorded on the item |
| `DROPPED` | Assessed and rejected — reason recorded on the item |

---

## Where we are — tally as of 2026-08-05

**25 specs have landed since 072.** Of the 25 roadmap items (R0–R24), **16 are closed** in some
form and **8 remain unstarted**, with one blocked on external access.

| Disposition | Count | Items |
|---|---|---|
| **DONE** | **16** | R0, R0a, R0b, R1, R2, R3, R8, R9, R11, R13, R14, R15, R17, R18, R23, R24, **R25** |
| **DONE, narrowed** | **1** | **R12** — Elastic only; Dynatrace and New Relic still open |
| **CLOSED — not needed** | **1** | **R22** — diagram coverage already satisfied; Excalidraw is an aesthetic, not a capability |
| **DEFERRED** | **1** | **R10** — ntopng; ClickHouse flow history is Enterprise M+ only |
| **BLOCKED — measured** | **1** | **R5** — Mist adoption rejected at 2.36× the ceiling; build specified and gated on a populated org |
| **NOT STARTED** | **7** | R4, R6, R7, R16, R19, R20, R21 |

Not roadmap items, delivered alongside: **087** Catalyst Center and **089** Meraki (operator
requests), **088** the startup surface, **093** the package-reference surface, **096**'s spec-artifact
gate. Specs **085** and **086** are docs-only (the IETF survey feeding R23, and the R10/R17
deferral) and have no spec directory — the numbering gap is expected, not a loss.

### The sequencing rule this project learned the hard way

Three separate items stalled on the same thing in one week: **can this be verified today, with the
access we actually have?**

- **R5** — org obtained, credential working, adoption measured and rejected. The *build* is blocked
  because the org has zero devices, so the failure mode it must prevent cannot be exercised.
- **R12** — Dynatrace and New Relic are SaaS-only with no self-hostable path, so R12 shipped as
  Elastic alone rather than three-quarters unverified.
- **R10** — the free edition cannot do the job at all.

**So prioritise by verifiability first, value second.** An item that ships unverified is not a
closed item; it is a claim. R3's FortiManager and FortiAnalyzer planes are the standing example —
shipped deliberately unverified, and still unverified.

### What is left, in priority order

**Tier A — buildable and verifiable today, no vendor gate**

| Item | Why now |
|---|---|
| ~~**R24** Open-territory triage~~ | **DONE 2026-08-05** — ran first exactly as intended, and produced R25 below |
| ~~**R25** Arista ANTA~~ | **DONE 2026-08-05** — the triage's pick, built and verified live the same day. Manifest was indeed the design risk: 208 tests, 4 tools, 1,272 tokens |
| **R21** GitOps — ArgoCD / Flux | Fully self-hostable; needs a `kind`/`k3s` cluster, which also revives R14's Kubernetes integration. Real data the operator controls end to end |
| **R20** Notion + Linear | Free self-serve tiers, official MCPs, zero infrastructure. Fast to land; lower network-engineering value |
| **R19** Google Workspace | Self-serve with an existing Google account. Composes with R18 so generated documents can land in Drive |

**Tier B — blocked on access, not on effort**

| Item | Gate |
|---|---|
| **R5** build | A Mist org with at least one live AP or switch |
| **R6** Aruba Central / ClearPass / GreenLake | A GreenLake tenant **and devices** — the same empty-tenant problem R5 hit. Still paired with R5 |
| **R4** Palo Alto PAN-OS / Panorama | A PAN-OS VM-Series image (support-account gated). `vrnetlab/paloalto/pan` build harness is present; **no image on disk** |
| **R7** Nexus Dashboard / Intersight / UCS | Cisco entitlement. Intersight has a free tier and DevNet sandboxes exist — **the most likely Tier B item to become Tier A** |
| **R16** vSphere / NSX | A vCenter |
| **R12** remainder | Dynatrace and New Relic tenants |

**Do not start a Tier B item without first confirming the access exists.** That check costs
minutes; discovering it after the spec is written costs a day, which is exactly what R5 cost.

---

## Status board

### Foundation (blocks everything else)

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R0** | MCP config reconciliation — repo vs live vs vendored | [075](../specs/075-mcp-config-reconciliation/spec.md) | `DONE` |
| **R0b** | Dead registered servers + PEP 668 install path | [090](../specs/090-fix-dead-servers/spec.md) | `DONE` — 7 servers could not start (22 skills routed to them) while reconcile exited 0. 6 fixed, 1 excepted (RADKit ships code-signed wheels outside PyPI), `startup` promoted to a **hard gate**. Root cause: `netclaw_pip_install` had no PEP 668 handling while 56 call sites hid the failure behind `--break-system-packages 2>/dev/null \|\| log_warn`. Also corrected spec 088's wrong claim that `prisma_sase` was unavailable — it was a PEP 668 error read as an availability error |
| **R0a** | Dependency-pin hazards | [077](../specs/077-dependency-pin-hazards/spec.md) | `DONE` — 41/41. 25 pins bounded across 20 servers, 130 bare pip calls routed through one helper, GAIT's unbounded install fixed, new `dependencies` gate surface |

> ### R0a — two latent breakages that make fresh installs fail
>
> Found while implementing R1 (spec 076 research R7 and R14). Neither affects an existing working
> install, which is exactly why both went unnoticed — they break *new* installs only.
>
> **1. `mcp 2.0.0` removed `mcp.server.fastmcp`.** Verified: the 2.0.0 wheel contains **zero**
> `mcp/server/fastmcp/` files, and does not declare `fastmcp` as a dependency, so there is no
> re-export. **Seven** servers have an unbounded pin *and* import that module, so all seven resolve a
> breaking major on a fresh install today. Audited 2026-07-31 — an earlier count of this list wrongly
> treated exact `==` pins as unbounded, so the composition below is the corrected one:
>
> | Server | Current pin | Hazard |
> |---|---|---|
> | `claroty-mcp` | `mcp>=1.0.0` | mcp 2.x removed the module |
> | `protocol-mcp` | `mcp>=1.0.0` | mcp 2.x |
> | `suzieq-mcp` | `mcp>=1.0.0` | mcp 2.x |
> | `nautobot-mcp-v2` | `mcp>=1.0.0` | mcp 2.x |
> | `uml-mcp` | `mcp>=1.2.0` | mcp 2.x |
> | `thousandeyes-mcp-community` | `mcp>=1.13` | mcp 2.x |
> | **`n2n-mcp`** | `fastmcp>=0.1.0` | **standalone `fastmcp` major drift — and it is one of the 7 live servers, backing the federation** |
>
> Already safe, and confirming the fix pattern works: `f5-mcp-server` (`mcp==1.4.1`),
> `meraki-magic-mcp-community` (`fastmcp==2.2.10`), `multivendor-cli-mcp` (`mcp>=1.2.0,<2`).
>
> Fix: pin `mcp>=…,<2` in each, or migrate to the standalone `fastmcp` distribution. Spec 076 already
> pins `<2` for its own server, so the pattern is established.
>
> **2. `pip3` and `python3` can be different interpreters.** On the development host, `pip3` targets a
> stranded Python 3.13 `site-packages` while `python3` is 3.14.4 — carrying two different
> `cryptography` versions. Audited: **188 bare pip invocations (143 `pip3`, 45 `pip`), only 1 interpreter-scoped.** Any bare invocation lands
> where the servers cannot import from. Same defect class as the hardcoded interpreter paths R0 fixed.
>
> **3. `python3 -m venv` fails outright** where `ensurepip` is unavailable (Python 3.14 here, because
> `python3.14-venv` is not installed and needs root). Audited: **2 places** create venvs this way —
> `scripts/gait-venv-setup.sh` and `scripts/lib/install-steps.sh`. GAIT is the audit trail Principle IV
> makes non-negotiable, so its venv failing is not cosmetic. Spec 076 works around it with `virtualenv`.
>
> **Why next**: R2–R24 each add a server, and every one inherits both hazards. Fixing them once is
> cheaper than seven times, and a broken fresh install undermines R0's whole "available to people when
> they install their own risk" goal.

> **R0 complete 2026-07-30, with two premises corrected.** Most "unregistered" servers were
> deliberate on-demand installs already tracked in a 60-entry `EXTERNAL_INTEGRATIONS` list. Both
> verifiers already exited `1` correctly — the earlier "exit 0" reading was a `| tail` pipe artifact;
> the real gap was that **nothing invoked them**. Genuinely broken: 3 Nautobot registrations
> hardcoded to `/home/ubuntu/netclaw/`, 9 wrong documented counts, 2 silently unchecked claims.
> True counts: **199 skills, 149 integrations**. See the R0 Outcome section below.

### Tier 1 — Multivendor holes where a mature MCP already exists

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R1** | Generic multivendor CLI driver (Nornir/Netmiko/NAPALM) | [076](../specs/076-multivendor-cli-driver/spec.md) | `DONE` — 94/94. ~90 platform families reachable; 2 verified live (SR Linux native CLI, FRR shell). Read-only default, server-side filter, 3-tier inventory, gated writes with real ServiceNow CR checking |
| **R2** | Cisco PSIRT vulnerability intelligence | [078](../specs/078-cisco-psirt-vulnerability/spec.md) | `DONE` — 52/52. **Rescoped from four API families to one**: Bug/EoX/Case/Serial all return 403 under the API Console grant, CX Cloud 504. All 7 PSIRT OSTypes live-verified; `iosxr` is not an OSType (404). Full chain proven on live CML: pyATS read 17.16.1a → 26 advisories, 1 Critical |
| **R3** | Fortinet (FortiOS / FortiManager / FortiAnalyzer) | [080](../specs/080-fortinet-coverage/spec.md) | `DONE` — 21 tools, 3 planes, 2,486/5,000 token manifest. Device plane live-verified from Slack on FortiOS 7.6.7; manager/analyzer implemented, unverified. **Built, not adopted** — no candidate emits a plane field, and their manifests are 69–204 tools each |
| **R4** | Palo Alto PAN-OS / Panorama NGFW | — | `NOT STARTED` |
| **R5** | Juniper Mist (official) + Apstra | [095](../specs/095-juniper-mist/spec.md) | **`BLOCKED — measured`** — measured 2026-08-05 against the live endpoint with the operator's own org. **Adoption rejected on the ceiling: 7 tools, 11,783 tokens, 2.36× over**, and `config/openclaw.json` has no tool-filtering key across 101 servers, so a subset cannot be loaded. The opposite failure mode from every prior rejection — not too many tools, but **~1,678 tokens per tool**. Build path specified (GET-only client, ≤1,500-token target, 087 shape) and **gated on a populated org**: the verification org has 1 site and 0 devices, so no assurance path can be exercised. Three durable findings: the **chars/4 convention under-reports by 17%** near the ceiling; `get_mist_insights` requires a `query_type` its schema never declares (silently dropped, then reported missing); and `sites_sle` on an empty org returns `count: 1` with no metrics — **no telemetry and no problems are the same shape** |
| **R6** | HPE Aruba Central / ClearPass / EdgeConnect / GreenLake | — | `NOT STARTED` |
| **R7** | Cisco Nexus Dashboard / Intersight / UCS | — | `NOT STARTED` |
| — | Cisco Catalyst Center (official) — operator request, not an R item | [087](../specs/087-catalyst-center-official/spec.md) | `DONE` — 514 read ops via 8 dispatchers + find/describe, 1,821/5,000 tokens. Built a client over Cisco's catalogue because the official server's 515 tools bust the ceiling |
| — | Cisco Meraki (official) — operator request, not an R item | [089](../specs/089-meraki-official/spec.md) | `DONE` — **adopted, zero code**: Cisco's remote MCP, 2 tools, 494 read-only capabilities, 1,561/5,000 tokens. Read-only is structural (431 mutating ops absent from the catalogue; 10/10 verified). Retired the dead community `meraki-magic-mcp`, taking spec 088's startup findings 7 → 6. **Found that 54 of 80 method names the old skills documented did not exist in the Meraki API** — now guarded by a sixth reconcile surface |

### Tier 2 — The internet / external plane

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R8** | Globalping — outside-in probe measurement (remote MCP) | [079](../specs/079-globalping-probes/spec.md) | `DONE` — 36/36. NetClaw's first vantage point **outside** its own domain. 5 measurement tools from ~4,800 probes; zero install. Three-way distinction enforced: `no_probes_found` = never ran, 0-of-N = unreachable, internal = refused locally. **Budget is per probe, not per call** — my first research pass got this backwards and a controlled test corrected it |
| **R9** | BGP & registry intelligence (RPKI / RDAP / PeeringDB / RIPE Atlas) | [081](../specs/081-bgp-registry-intel/spec.md) | `DONE` — **10/10 tools live-verified**, 1,376/5,000 token manifest. No credentials, no lab, no licence. Core discipline: **RPKI `not-found` is not `invalid`** — most of the internet is unsigned |

### Tier 3 — Monitoring and traffic layers

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R10** | ntopng — flow analytics platform | — | **`DEFERRED`** — investigated 2026-08-04. **The premise is false for the free edition**: ClickHouse flow history is hard-gated to Enterprise M+ (€699.95), verified in ntop's own `Prefs.cpp:3381`. Community's 12 MCP tools also require an **admin** token and bust the ceiling once the 5,338-token `instructions` payload is counted |
| **R11** | SNMP-poller NMS (Zabbix / LibreNMS / Netdata) | [083](../specs/083-zabbix-nms/spec.md) | `DONE` — **Zabbix only**, adopted not built (3 tools, 589/5,000 tokens). NetClaw's first polled-history source. Runs in a dedicated venv (fastmcp 3.x vs five servers pinning `<3`). Both silent-wrong-answer traps reproduced against live 7.0.29 |
| **R12** | APM + log platforms (Dynatrace / New Relic / Elastic) | [096](../specs/096-elastic-logs/spec.md) | **`DONE — Elastic only`** — adopted, zero code. 5 tools, **1,094/5,000 tokens**, verified against a live Elasticsearch 9.2.0 (`basic` licence) with 25,000 indexed documents. **Dynatrace and New Relic remain open** — SaaS-only, no self-hostable verification path, the same access blocker that gated R5. Adopted a **deprecated** upstream deliberately: the successor (Agent Builder MCP endpoint) is **Enterprise-tier on self-managed**, so the supported path is paywalled while this one is Apache-2.0 and already published; pinned by digest so a security-only update cannot shift answers. Silent wrong answer reproduced and blocked: Elasticsearch caps `hits.total` at 10,000 and marks it `relation:"gte"`, but **the server discards the qualifier** — 10,075 real documents reported as `Total results: 10000`, an error that is unbounded (a million-doc index still says 10,000). Mitigations verified: `esql`, or `search` + `track_total_hits: true` |
| **R13** | NSM / IDS (Zeek / Suricata / Arkime) + packet-buddy audit | [091](../specs/091-nsm-zeek-suricata/spec.md) | `DONE` — **built**, read-only offline PCAP analysis. Zeek 8.2.1 + Suricata 8.0.6 from digest-pinned containers, 6 tools / 934 tokens, 19 assertions. **Arkime rejected** (mandatory OpenSearch + ~12–16 GB = a platform, not a tool). Two silent wrong answers reproduced live and structurally blocked: stock Suricata loads **0 signatures** and reports 0 alerts behind two non-fatal warnings (52,205 after update); Zeek **discards invalid-checksum packets by default**, losing `http.log` entirely and miscounting `conn.log` (3 rows vs 2) — which affects NetClaw's **own** capture skills' output |

### Tier 4 — The layer beneath the network

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R14** | Kubernetes (pods/services/ingress/NetworkPolicy) | [084](../specs/084-k8s-readonly/spec.md) | `DONE` — **read-only**, adopted `containers/kubernetes-mcp-server` (Apache-2.0 Go binary, pinned + checksummed). 7 tools / 1,643 tokens; the upstream **default busts the ceiling**. Helm and all writes deliberately out of scope. The upstream's silent RBAC narrowing was **reproduced live** and is mitigated by a mandated cluster-wide-read SA plus a skill preflight |
| **R15** | Redfish / BMC out-of-band (iDRAC / iLO / XClarity) | [094](../specs/094-redfish-bmc/spec.md) | `DONE` — **built** (both candidates unvendorable: one has NO licence file, the other NOASSERTION), read-only, 6 tools / 728 tokens, 15 assertions, verified against the **DMTF Redfish mockup** so no hardware was needed. Core discipline: the box-vs-network distinction is **symmetric** — a BMC timeout establishes NOTHING about the host and can never be emitted as a downed host, while `PowerState: Off` IS a fact. Power control deliberately unimplemented; the client issues no verb but GET |
| **R16** | VMware vSphere / NSX (build, not adopt) | — | `NOT STARTED` |
| **R17** | Database query layer (Postgres / ClickHouse / DuckDB / SQLite) | [092](../specs/092-duckdb-analysis/spec.md) | `DONE` — **DuckDB only**, read-only, 3 tools, 32 assertions. Unblocked exactly as this roadmap predicted: R13 produced the Zeek/Suricata exports first. Containment is **DuckDB's own**, not a regex — datasets are materialised, then `enable_external_access=false` + `lock_configuration=true` close every filesystem and network path irreversibly, so memory/RAG/federation/GAIT are unreachable by construction (8 escape attempts verified to raise). ClickHouse still out: its rationale died with R10 |

### Tier 5 — Productivity and human deliverables

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R18** | Document generation — docx / pptx / xlsx / pdf | [082](../specs/082-document-generation/spec.md) | `DONE` — 6 tools, 2 skills, 1,232/5,000 token manifest, 240 assertions. **All four formats live-verified from a real FortiGate and opened.** Built, not vendored — the upstream skills are demonstration-only, not Apache-2.0. Core discipline: **a document must never fabricate to fill a blank** |
| **R19** | Google Workspace (official) | — | `NOT STARTED` |
| **R20** | Notion + Linear (official) | — | `NOT STARTED` |
| **R21** | GitOps + Azure DevOps (ArgoCD / Flux) | — | `NOT STARTED` |
| **R22** | Diagram MCPs — Excalidraw + draw.io | [093](../specs/093-package-reference-check/spec.md) | **`CLOSED — already satisfied`** — audited 2026-08-04 after the operator questioned the premise, and they were right. `drawio-diagram` already ships native `.drawio` files with CLI export to PNG/SVG/PDF; `uml-diagram` covers **27+ types via Kroki** (Mermaid, D2, Graphviz, C4, BPMN, ER, sequence); plus `markmap-viz`, `aws-architecture-diagram`, `canvas-network-viz`, `threejs-network-viz`, `ue5-network-viz`, `blender-3d-viz`. Excalidraw adds a hand-drawn **aesthetic**, not a capability. The audit did find a real defect — see 093 |

### Strategic (not tooling)

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R23** | IETF MCP-for-network-management landscape → NCFED `-01` input | [survey](ietf/IETF-MCP-LANDSCAPE-2026-08.md) | `DONE` — surveyed 2026-08-04. **One of the four named drafts is EXPIRED**; the count went *down* to 13; and the roadmap missed the `agentproto` **WG-forming BOF** (154–51 for a WG, scope rejected 38–124). 8 recommendations seeded into the `-01` backlog |

### Open territory (build candidates — assess before scheduling)

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R24** | Open-territory triage — pick flag-planting targets | [097](../specs/097-open-territory-triage/spec.md) | `DONE` — all 22 candidates dispositioned ([TRIAGE.md](../specs/097-open-territory-triage/TRIAGE.md)): **4 `COVERED`** (all absorbed by R1, unnoticed until now — only SR Linux verified live), **1 `SELECTED`** (Arista ANTA → R25), **12 `DEFERRED`**, **5 `DROPPED`**. Two premises were stale: **Megaport is no longer unclaimed** (an official read-only MCP exists in open beta), and MikroTik's "adopt a dedicated MCP" entry predates R1, which now reaches it |
| **R25** | Arista ANTA — structured network-state validation | [098](../specs/098-arista-anta-validation/spec.md) | `DONE` — **built**, read-only, **4 tools reaching a 208-test catalogue for 1,272/5,000 tokens** (one tool per test would be ~58,000, 11.6× over). Verified live against `clab-mandible-veos1` (vEOS-lab 4.36.1F) over eAPI. Runs in **its own venv, and not by preference**: ANTA moves `cryptography` 46.0.5 → 50.0.0 and four installed distributions depend on it unbounded, including the federation TLS stack — caught by a dry-run *before* installing, per spec 076. **Silent wrong answer reproduced and blocked**: ANTA reports a test for an *unconfigured* feature as a **failure** — `VerifyBGPPeerCount` returns "BGP inactive" as a failure on a switch with no BGP — so the server reclassifies to `not_applicable` with a deliberately narrow rule that never hides a real failure. No health percentage is emitted: `passed/total` is meaningless with `not_applicable` in the denominator |

---

# R0 — MCP config reconciliation

> **Complete.** R1–R24 are unblocked. Every one of them must follow `docs/ADDING-AN-MCP.md`
> and pass `python3 scripts/reconcile-mcp.py` before merge.

**Status:** `DONE` (2026-07-30, spec 075)
**Blocks:** every other item in this roadmap — now unblocked
**Type:** foundation / config hygiene — no new capability

## Why this is first

Every "add server X" item below writes to the same config surface. If that surface is already
inconsistent, each addition compounds the drift and we cannot tell whether a new capability is
actually obtainable by someone installing their own risk.

## Outcome (completed 2026-07-30)

R0 shipped as **spec 075**. Two of its three originating premises were wrong, and saying so
plainly matters more than looking consistent — the corrections are the most useful thing R0
produced.

### What was claimed vs. what was true

| Original claim | Reality |
|---|---|
| 20 vendored servers are "silently unregistered" (Bucket A) | Mostly **deliberate**. `scripts/verify-inventory-counts.py` already maintained a 60-entry `EXTERNAL_INTEGRATIONS` list covering pyATS, NetBox, ServiceNow, ACI, ISE, F5 and others as intentional on-demand installs. `pyATS_MCP` being absent from the config is by design. |
| Both verifiers report `FAIL` and exit 0, so nothing enforces them | **Measurement error.** Both exit `1` correctly. The exit codes had been read through a `\| tail` pipe, which reports the pipe's status. The real gap: **nothing invoked them** — `.github/workflows/` held only `skill-review.yml`. |
| 19 registered servers have no installer coverage, so the installer cannot install them | **Declaration gaps, not installer gaps.** All 19 were installable; catalog ids `aap`, `aws`, `gcp`, `fmc`, `meraki`, `memory-mcp`, `te-community`, `te-official` all existed. The checker simply lacked mapping rules. Fixed with **8 declarations, zero new install functions**. |
| Bucket C: 82 servers declared but not live | **Descoped.** The maintainer's ruling: *"let's not worry about the live config as long as all 89 are available for people when they install their own risk."* Live-gateway state is explicitly out of scope. |

### What was genuinely broken

- **3 Nautobot registrations hardcoded to `/home/ubuntu/netclaw/`** — a path on no machine,
  including the maintainer's. Broken for every installer. This was the only user-facing breakage,
  and reframing the goal around fresh-install correctness is what surfaced it.
- **9 wrong documented counts** across `README.md` and `SOUL.md`. True values: **199 skills,
  149 MCP integrations**.
- **2 documentation claims silently unchecked** — their prose had been reworded, so the checker
  stopped matching them and reported only an advisory note. Retired with a documented reason
  (spec 049 made the installer selective, so a fixed "deploys N skills" claim is now false).
- **`cml-mcp` packed arguments into its command string**; normalised to `command` + `args`.

### What shipped

| Artifact | Purpose |
|---|---|
| `scripts/reconcile-mcp.py` | Single entry point across all surfaces (the fix for "nothing ran the checks") |
| `scripts/check-mcp-portability.py` | Catches machine-specific paths; distinguishes `/usr/bin/python3` (fine) from `/home/ubuntu/...` (fatal) |
| `.github/workflows/mcp-reconciliation.yml` | CI hard-fail. Deliberately never uses `--warn-only` |
| `tests/reconcile/run-tests.sh` | 14 exit-code contract tests, no framework, no dependencies |
| `docs/ADDING-AN-MCP.md` | The one procedure R1–R24 each follow |
| `verify-catalog-coverage.py` | +8 mapping declarations, +vendored-state completeness |
| `verify-inventory-counts.py` | Unlocatable claims are now failures, not notes |

### One open finding

**EVE-NG** is vendored (`mcp-servers/eve-ng-mcp-server`) and has 5 skills, but appears in neither
`EXTERNAL_INTEGRATIONS` nor `scripts/lib/catalog.sh`. It is therefore missing from the integration
count and cannot be installed by the modular installer. Recorded in `VENDORED_STATE_REASONS` as an
explicit open finding rather than silently absorbed, because resolving it raises the MCP count to
150 and needs a catalog entry plus install function — a scope decision, not a cleanup.

### Durable rule for R1–R24

Follow **`docs/ADDING-AN-MCP.md`**, then run `python3 scripts/reconcile-mcp.py` before pushing. CI
runs the same command and fails the merge on non-zero. And never read an exit code through a pipe.

# Tier 1 — Multivendor holes where a mature MCP already exists

Common to every Tier 1 item:

- [ ] Read the upstream source before adopting; note license, auth model, and whether it is
      read-only or write-capable
- [ ] Prefer read-only or explicitly-gated write paths; route writes through the existing
      approval/HumanRail path
- [ ] Run `defenseclaw skill scan` / CodeGuard on adopted third-party code
- [ ] Register via the R0 procedure and verify it reaches the live agent
- [ ] Write or update the accompanying skill(s) so the capability is discoverable
- [ ] Add the server to the docs inventory and the installer's component list

---

## R1 — Generic multivendor CLI driver (Nornir / Netmiko / NAPALM)

**Status:** `NOT STARTED` · **Recommended first Tier 1 item**

Biggest coverage-per-line item on the roadmap. Current device reach is pyATS + junos + gnmi
+ RADKit. There is no "SSH to anything" tool. This one server adds MikroTik, VyOS, SONiC,
Nokia SR Linux, Extreme, Huawei, Dell, Ubiquiti EdgeOS and ~90 more platforms.

**Candidates**
- `sydasif/nornir-mcp-server` — NAPALM normalized getters + Netmiko CLI exec; ships command
  blacklisting, Pydantic input validation, backup-path restriction
- `ntunes/netmiko-mcp-server` — connection pooling, multi-vendor, concurrent operations

**Checklist**
- [ ] Evaluate both; decide adopt-one, adopt-both, or fork
- [ ] Define the inventory source — reuse NetBox/Nautobot/Infrahub as SoT rather than a new file
- [ ] Define credential handling — route through Vault MCP, not plaintext inventory
- [ ] Harden the command allow/deny list; confirm config-mode commands are gated
- [ ] Establish where this stops and pyATS starts, so skills don't overlap ambiguously
- [ ] Skill(s) covering: normalized getters, safe show-command exec, multi-device fan-out
- [ ] Validate against a real multivendor lab (containerlab/GNS3/EVE-NG) with at least one
      platform NetClaw cannot reach today

---

## R2 — Cisco PSIRT vulnerability intelligence

**Status:** `DONE` — spec [078](../specs/078-cisco-psirt-vulnerability/spec.md), 52/52 tasks.
See the outcome section at the end of this document.

Closes a top-5 real-world netops question NetClaw cannot answer: *is this build affected by
an advisory, past EoL, or hitting a known bug?* NVD CVE and DevNet content search do not cover
Cisco-specific advisories, EoL dates, bug IDs, or TAC cases.

**Candidate considered:** `sieteunoseis/mcp-cisco-support` — 46 tools across 8 families.
**Not adopted.** Seven of its eight families are unreachable with an API Console grant (403/504),
so most of that tool surface would have been dead weight in the manifest. NetClaw ships its own
6-tool server against the one family that answers.

**Checklist**
- [x] Obtain Cisco API credentials (Support APIs and PSIRT openVuln are separate entitlements)
      — and they are: PSIRT works, the Support APIs return **403** under the same grant
- [x] Handle rate limits — 5/sec and 30/min, de-dup → cache → pace → back off, in that order
- [x] Decide which of the 8 API families to enable — **one is reachable**, not eight
- [x] Wire results into the existing `nvd-cve` skill flow rather than duplicating it — the
      boundary is documented in both directions, and either may be legitimately empty
- [x] Skill: version-to-advisory check ✅ — **EoL/EoS and serial-to-entitlement are 403, dropped**
- [x] Cross-link with pyATS version collection so the question is answerable end-to-end from a
      live device — verified on live CML routers, no version typed by a human

---

## R3 — Fortinet (FortiOS / FortiManager / FortiAnalyzer)

**Status:** `DONE` — spec [080](../specs/080-fortinet-coverage/spec.md). 21 tools across three planes,
manifest **2,486 / 5,000 tokens**. Device plane **live-verified** end to end from Slack against a licensed
FortiGate-VM (FortiOS 7.6.7); manager and analyzer planes implemented but **not exercised** — see
[VERIFICATION.md](../specs/080-fortinet-coverage/VERIFICATION.md).

**The premise was worse than "no server".** `fortimanager-ops` shipped `user-invocable: true`, declaring
env vars and naming `jmpijll/fortimanager-mcp` — never vendored, never registered, not installable. Not a
gap but a **claim**: an agent would route a firewall question to it and find out mid-investigation. The
installer even cloned that repo, and an iN2N member ran against the phantom command.

**Build, not adopt** — four independent disqualifications, any one sufficient: no candidate emits the
`plane` field; manifests are 106 / 69 / 204+ tools against a 5,000-token ceiling; only `ivillagomez`
enforces read-only while `rstierli/fortimanager-mcp` exposes **package install ungated**; none has any
concept of a change record. All four remain useful as MIT endpoint reference — `paoloamato2`'s five
generic pass-throughs proved a small manifest can carry full coverage, and `rstierli`'s offset pagination
avoided a real `tid`-expiry bug.

**Three planes, and they are not substitutes** — manager = intent, device = observed state, analyzer =
observed traffic. FortiManager and FortiAnalyzer share one `/jsonrpc` client (the roadmap listed them as
separate items; they are one transport). `fgt_compare_with_manager` reports `only_in_device` rules as
candidate out-of-band changes — invisible from either plane alone.

**Checklist**
- [x] Entry point decided — **all three planes**, one skill each per Principle VII
- [x] Token cost assessed — built ~21 parameterised tools instead of adopting 380; measured, with a
      build-failing ceiling test
- [x] Read-only default; writes need **two** gates — human approval AND an approved ServiceNow CR, with
      distinct refusal outcomes so they cannot be conflated
- [x] `fortimanager-ops` back-filled (v2.0.0) against a server that actually ships
- [x] Skills: policy audit, VPN tunnel status (phase 1/2 separate), FortiAnalyzer log query
- [x] Stale iN2N member repaired; installer no longer clones the phantom repo

**What it cost, and what that bought**

Most of a day went to licensing, and three FortiGate VMs were destroyed before the cause was understood:
a **VM licence is bound to a serial and the unit adopts it on apply** — applying one issued for a
different serial does not fail cleanly, it sets the unit to `FGVM00UNLICENSED` and wipes the working
evaluation licence. Two further findings worth keeping:

- **An unregistered FortiGate blocks the entire management plane.** Every REST request returns 401
  regardless of token validity, admin profile or trusthost — proven by widening trusthost to `0.0.0.0/0`
  and packet-capturing the source. The GUI login-loops for the same reason. Only `License Status:
  Invalid → Valid` changed the behaviour.
- **FortiOS 8.0.0 GA has a web-GUI logout loop** on the 1 vCPU trial profile (`VM resource exceeds
  license limit` → `httpsd` restarts). SSH and REST unaffected; 7.4/7.6 are fine.

**A gap in `docs/ADDING-AN-MCP.md` this feature exposed:** an **iN2N member is a separate claw** with its
own config, `.env`, workspace and Border-registered scope, and **the Border caches the member roster in
memory**. Registering a server on the Border does nothing for members. That is four artifacts beyond the
documented checklist plus a `netclaw-mesh` restart — the same class of gap spec 075 was created to close,
and it made the first three live Slack attempts fail with `IN2N_ERR_NO_CAPABLE_MEMBER`.

**Deferred:** an IPsec tunnel to exercise the populated phase-1/phase-2 shape; FortiManager-VM and
FortiAnalyzer-VM (separate 15-day trials) to verify 12 of the 21 tools; a ServiceNow instance for gate 2.

---

## R4 — Palo Alto PAN-OS / Panorama NGFW

**Status:** `NOT STARTED`

`paloalto-panorama` skill exists with no server. Prisma SD-WAN/SASE is covered; the NGFW is not.

**Candidate:** `cdot65/pan-os-mcp` — XML API via the Python MCP SDK.

**Checklist**
- [ ] Assess XML API coverage vs what the `paloalto-panorama` skill claims
- [ ] Decide device-vs-Panorama scope
- [ ] API key handling via Vault
- [ ] Read-only first; commit/candidate-config writes gated
- [ ] Consider whether `fwrule-mcp` overlaps and how they compose

---

## R5 — Juniper Mist (official) + Apstra

**Status:** `BLOCKED — measured` · [spec 095](../specs/095-juniper-mist/spec.md) ·
[measurements](../specs/095-juniper-mist/VERIFICATION.md)

`junos-mcp-server` covers devices. Nothing covers Mist wired/wireless assurance or Marvis.
Juniper ships an **official** Mist MCP server (Claude Desktop beta) — **measured and rejected**.

> **Adoption is not available.** `https://mcp.ai.juniper.net/mcp/mist` exposes 7 tools costing
> **11,783 tokens against the 5,000 ceiling (2.36×)**, counted with `count_tokens`, not estimated.
> No tool-filtering key exists in `config/openclaw.json` across 101 registered servers, so a
> cheaper subset cannot be loaded. Re-check with `python3 scripts/probe-mist-mcp.py --count`.

> **The build is gated, not merely unstarted.** The verification org has **1 site, 0 devices**.
> `sites_sle` there returns `count: 1` with no metrics — a site with no telemetry and a site with
> no problems are indistinguishable in the response. Assurance skills whose central failure mode
> cannot be exercised are not built; see spec 095's exit conditions.

**Checklist**
- [x] Measure the official server against the ceiling — **11,783, rejected**
- [x] Mist API token + org ID handling — `Bearer` only, `X-Mist-Base-URL` mandatory for regional
      clouds, per-call `org_id` required (the `X-Mist-Org-ID` header does not supply it)
- [ ] Obtain a populated org (Juniper SE demo org, or hardware — `trial_enabled: true` already)
- [ ] Build the GET-only client (≤1,500-token manifest, 4 dispatchers, 087 shape)
- [ ] Skills: wireless assurance, client troubleshooting, Marvis query, SLE review — **after** the
      above, so the empty-vs-healthy trap can be reproduced and blocked
- [ ] Assess Apstra separately (community only) — DC fabric intent; may fold into R6 if the
      unified HPE server covers it adequately

---

## R6 — HPE Aruba Central / ClearPass / EdgeConnect / GreenLake

**Status:** `NOT STARTED`

Only `aruba-cx` (switch CLI) exists today. One server covers a whole vendor cloud stack.

**Candidates**
- `nowireless4u/hpe-networking-mcp` — unified: Mist + Aruba Central + GreenLake + ClearPass
  + Apstra + Axis Atmos + AOS 8 + UXI + EdgeConnect, one container
- `secure-ssid/centralmcp` — low-token Aruba Central + GreenLake + EdgeConnect + UXI, with
  RAG/OpenAPI lookup

**Checklist**
- [ ] Decide unified-vs-focused. Note the unified server overlaps R5 (Mist) and Apstra —
      sequence R5/R6 together to avoid double-registering Mist
- [ ] Evaluate the low-token design of `centralmcp` against NetClaw's token budget work
- [ ] Multi-tenant / multi-account credential model
- [ ] Skills: Aruba Central inventory + health, ClearPass policy/auth troubleshooting,
      EdgeConnect SD-WAN status, UXI sensor results

---

## R7 — Cisco Nexus Dashboard / Intersight / UCS

**Status:** `NOT STARTED`

ACI ships as a deliberate on-demand integration — `ACI_MCP` is vendored and tracked in
`EXTERNAL_INTEGRATIONS` with catalog id `aci`, so R0 correctly left it as-is and it is **not** an
unregistered gap. Nexus Dashboard and Intersight/UCS are absent entirely.

**Candidates**
- `beye91/nexus-dashboard-mcp` — read-only ND API + read-only NX-OS commands + log fetch
- Community Intersight MCP server
- **Reference read:** Cisco's own Network MCP Docker Suite (Meraki, Catalyst Center, IOS XE,
  NetBox, ISE, ThousandEyes, Splunk) — heavy overlap with NetClaw, useful as a packaging
  and validation reference rather than an adoption target

**Checklist**
- [ ] Confirm R0 resolved `ACI_MCP` registration before adding Nexus Dashboard, to avoid
      two overlapping DC-fabric surfaces
- [ ] Adopt Nexus Dashboard MCP; scope to read-only initially
- [ ] Assess Intersight/UCS as a separate decision — it is compute + fabric interconnect,
      arguably closer to R15 (BMC/out-of-band) than to Tier 1 networking
- [ ] Review the Cisco Docker Suite's packaging approach against NetClaw's installer

---

# Tier 2 — The internet / external plane

NetClaw has **zero** external-vantage or BGP-intelligence capability today: no ASN lookup,
no route-origin validation, no peering data, no abuse contacts, no third-party reachability.
This is a whole missing domain, not a missing tool.

## R8 — Globalping

**Status:** `DONE` — spec [079](../specs/079-globalping-probes/spec.md), 36/36 tasks.
See the outcome section at the end of this document. · *Was: highest value-per-effort item in the scan — and
it held up: no server written, one skill, one registration.*

Official jsDelivr remote MCP at `https://mcp.globalping.dev/mcp`. Ping, traceroute, DNS, MTR,
HTTP from thousands of global probes. Free. OAuth or API token. Zero install.

**Checklist**
- [x] Register the remote MCP endpoint (no vendored code — followed the Datadog / DevNet pattern)
- [x] Auth: **token**, bearer header; endpoint 401s without one. 500/hour authenticated vs 250/hour
      anonymous per IP — and **charged per probe, not per call**
- [x] Skill: external reachability, "is it us or the internet", geographic latency comparison, DNS
      propagation — plus the three-way "nothing came back" distinction the checklist did not anticipate
- [x] Compose with ThousandEyes **and** gtrace, positioned by *direction of measurement* rather than
      feature list

## R9 — BGP & registry intelligence (RPKI / RDAP / PeeringDB / RIPE Atlas)

**Status:** `DONE` — spec [081](../specs/081-bgp-registry-intel/spec.md). 10 tools, **all 10
live-verified**, manifest 1,376/5,000 tokens. See
[VERIFICATION.md](../specs/081-bgp-registry-intel/VERIFICATION.md).

**The other half of the external plane.** R8 (Globalping) *measures* toward a target; R9 *looks up* who owns
a resource, whether an announcement is authorised, and where a network peers. Together they complete
NetClaw's view outside its own administrative domain.

**Chosen for this slot because it has no external dependency.** Every source is a public unauthenticated
API — verified reachable *before* the spec was written, and again in Phase 0. That was a direct response to
R3, which discovered its lab problem at implementation time and lost most of a day, and to R4, which is
still waiting on a human-reviewed vendor trial. **This is the first item since R8 with no lab, licence,
trial or credential on the critical path** — and the first NetClaw integration with no secret to leak.

**The distinction, and it is the whole feature: RPKI `not-found` is not `invalid`.** Most of the internet
has no ROA. Reporting unsigned space as a finding would manufacture false incidents at scale. Four states,
all *observed* rather than read from documentation:

| Query | `state` | `reason` | Finding? |
|---|---|---|---|
| `AS13335` + `1.1.1.0/24` | `valid` | — | no |
| `AS13335` + `8.8.8.0/24` | `invalid` | `as` | **yes** |
| `AS15169` + `8.8.8.128/25` | `invalid` | `length` | **yes** |
| `AS3356` + `4.0.0.0/9` | `not_found` | — | no |

Fourth in the series after R2's *"no advisories ≠ not vulnerable"*, R8's *"no probes ≠ outage"* and R3's
*"no logs ≠ rule unused"*. `validation_unavailable` is a fifth outcome — **an unreachable validator is not
unsigned space**, the same distinction one level down.

**Build, not adopt.** `duksh/peerglass` covers similar ground with **42 tools across 9 phases** including
DNS-censorship detection, TLS/CT-log inspection and satellite tracking — a charter NetClaw did not choose,
and the wrong order of magnitude against a 5,000-token ceiling. It did independently arrive at three of this
spec's clarified decisions (TTL caching 5 min–24 h, per-result attribution, read-only), which is reassuring
convergent evidence.

**Phase 0 improved the spec.** The spec assumed RIPEstat; `rpki-validator.ripe.net` proved better on three
measured counts — RFC 6811 vocabulary natively (`not-found`, not `unknown`), `state` and `reason` as
separate fields rather than fused into `invalid_asn`, and the VRPs that drove the verdict returned.

**Checklist**
- [x] RPKI origin validation — four states, VRPs included, validator named, never corroborated
- [x] RDAP via IANA bootstrap → responsible RIR → `rdap.org` fallback, registry named on every result
- [x] PeeringDB — self-reported caveat on every result
- [x] RIPEstat routing status — collector basis stated, never called a leak
- [x] RIPE Atlas **narrowed** to anchors + per-AS probe counts; general probe availability stays with R8
- [x] Read-only throughout; no write path, therefore no gate to design
- [x] 4 req/s per source, **true sliding window**, strictly serial. Self-imposed and documented as such

**Two findings from implementation worth keeping**

1. **The rate limiter was genuinely too weak, and a test caught it.** A minimum-250 ms-gap implementation
   measured **4.53 req/s** because N requests spaced 250 ms apart put five inside one second. Replaced with
   a true sliding window. A second failure at 4.89/s then turned out to be the *test* measuring the wrong
   thing — `total/elapsed` is not "requests per window". The test caught a real bug; the fixed code caught a
   bad test.
2. **ARIN is not broken.** Phase 0 recorded a connection reset from `rdap.arin.net` on one `curl`; through
   the implemented bootstrap path it returned 200. The reset was transient and the docs were corrected —
   a single observation is not a property of a registry.

**Deferred:** genuine RPKI corroboration needs a **non-Routinator** relying party (both reachable
validators are RIPE NCC Routinator, so comparing them would be theatre); IRR/RPSL objects and BGP
communities are a distinct data model and belong to their own item.

---

## R10 — ntopng

**Status:** **`DEFERRED`** — investigated 2026-08-04, not built. Five independent blockers.

The original entry read: *"Official ntop MCP server (documented in ntopng 6.7). Queries ClickHouse flow
history, live host stats, alerts."* The MCP server is real. **The ClickHouse premise is not, on any edition
a lab would run.**

### Blocker 1 — ClickHouse flow history is Enterprise M+ (€699.95)

Not a docs ambiguity. A compile-time gate in ntop's own source, `src/Prefs.cpp:3381`:

```cpp
bool Prefs::do_dump_flows_on_clickhouse() {
  return (ntop->getPro()->is_enterprise_m_edition() ||
          ntop->getPro()->is_nedge_enterprise_edition())
    && dump_flows_on_clickhouse;
}
```

Startup validation refuses it outright: *"-F clickhouse is available only on Enterprise"*. The licensing
table agrees — *"High performance flow export to ClickHouse and explorer"* is ✗ Community, ✗ Pro,
✓ Enterprise M+. Even plain "export expired flows to database" is Pro+.

**Worse, it fails open.** With the ClickHouse client absent or the licence missing, ntopng logs a warning,
silently sets `dump_flows_on_clickhouse = false`, and **starts healthy**. MCP works. Storage was never
enabled. That is precisely the silent-misconfiguration failure this project rejects candidates over.

### Blocker 2 — the manifest busts the ceiling once you count `instructions`

Measured against a live unlicensed 6.7-dev instance: **12 tools, 2,157-token manifest** — which passes.
But `initialize` returns an `instructions` payload of **21,351 characters ≈ 5,338 tokens** — a full agent
system prompt. Real cost **≈ 7,400 tokens**, over the 5,000 ceiling on its own.

The payload also instructs the model to *"always wrap timestamp columns in formatDateTime(...)"* when
*"querying data from clickhouse db"* — on an edition where **no ClickHouse tool exists**, inviting
hallucinated SQL.

### Blocker 3 — it requires an ADMIN token, and the docs are wrong about it

`scripts/lua/rest/v2/exec/llm/mcp.lua` returns **403 Forbidden: administrator role required** unless
`isAdministrator()`. The documentation claims read-only keys suffice. They do not — a read-only token gets
no MCP access at all.

Every NetClaw integration adopted so far runs read-only by construction. This one cannot: handing an agent
an ntopng **admin** token to read live host stats is a posture regression, and one of the 12 tools is a
write (`add_active_monitoring_script`).

Compounding it: the **official compose ships `--disable-login`**, under which `isUserAdministrator()`
returns true unconditionally — copying it exposes an **unauthenticated, write-capable MCP endpoint**.

### Blocker 4 — an empty answer is uninterpretable

Six of the twelve tools return a success string for no-data. Measured:

| Call | Response | `isError` |
|---|---|---|
| `get_host_info`, host with no flows | `"No data found for host …"` | **false** |
| `get_live_flows_for_host`, unknown host | `"No active flows found for …"` | **false** |
| `get_country_stats` | bare CSV header, zero rows | **false** |

And the interface a query ran against is **neither selectable nor visible**: `ifid` is documented but the
C++ only honours it from a POST body MCP never sends, so the interface resolves from a **Redis per-user
preference set in the web UI**. In a multi-interface lab *"No active flows found"* usually means *"you
queried the wrong interface"* — with no way to choose one and no way to learn which answered.

Nothing distinguishes **not collecting** from **no traffic**.

### Blocker 5 — no native NetFlow/IPFIX collector, in any edition

ntopng ingests flows only over **ZMQ from nProbe**. nProbe is **separately licensed** (€299.95); its
unlicensed demo degrades after ~5 minutes. Community *can* accept a ZMQ collector interface (verified
unlicensed) and *can* sniff an interface directly — but the FRR/FortiGate NetFlow export this item was
meant to consume needs either paid nProbe or `netflow2ng` (MIT, **v9 only**, self-described Home/SOHO).

### The alternatives are dead ends

`marcoeg/mcp-server-ntopng` (20 tools) and `marcoeg/mcp-ntopng` (6 tools) both query ClickHouse directly —
inheriting the same Enterprise M+ requirement — are **17 months stale** (last commits March 2025), and pin
`fastmcp>=0.4.1` **unbounded**, resolving to 3.x and reproducing spec 083's blocker exactly.

### What would change this

A licensed Enterprise M+ ntopng, or a decision to accept live-state-only monitoring with an admin token.
Neither is a lab proposition. **If ntopng is ever revisited, the honest scope is 12 read-only-ish live-state
tools on the 6.7-dev image — no flow history, no ClickHouse, no alert tooling — and the `instructions`
payload must be suppressible first.**

## R11 — SNMP-poller NMS (Zabbix / LibreNMS / Netdata)

**Status:** `DONE` — spec [083](../specs/083-zabbix-nms/spec.md)

Prometheus, Grafana, Datadog, Splunk, Auvik, ThousandEyes are covered. There was **no
SNMP-poller NMS at all** — and therefore no polled history anywhere in NetClaw.

**Checklist**
- [x] Pick target(s) — **Zabbix only.** See the landscape below
- [x] Netdata assessed → **not in this category** (agent/push, not SNMP-polling). **Correction to this
      roadmap's earlier claim:** MCP is built into the **free open-source agent** (v2.6.0+,
      `http://host:19999/mcp`), not only a paid "Cloud MCP". The Cloud endpoint is the paid
      cross-infrastructure view. That makes Netdata a **separate near-zero-effort item**, not part of R11
- [x] Observium assessed → **`DEFERRED`.** Its one MCP server (`kdesch5000/observium-mcp`, 10 tools) was
      created and abandoned on the same day and **bypasses the Observium API entirely**, requiring direct
      MySQL credentials plus filesystem access to the RRD directory
- [x] Skills: interface utilization history, threshold/alert review, device availability — delivered as
      `zabbix-metrics-history`, `zabbix-problem-review`, `zabbix-availability`

**Landscape, measured by cloning and scanning — not read off READMEs**

| Candidate | Tools | Licence | Outcome |
|---|---|---|---|
| `mpeirone/zabbix-mcp-server` | **3** (589 tokens) | GPL-3.0 | **adopted, unmodified** |
| `mhajder/zabbix-mcp` | 53 | MIT | rejected — surface |
| `mhajder/librenms-mcp` | 111 | MIT | **LibreNMS deferred** — busts the ceiling |
| `initMAX/zabbix-mcp-server` | 237 | AGPL-3.0 | rejected — surface + copyleft |
| 2 JS servers | — | one has **no licence** | abandoned 2025 |

> **There is no official Zabbix LLC MCP server.** `mcpservers.org` labels initMAX "Official Zabbix MCP
> Server" — **that label is wrong**; initMAX is a Zabbix Premium Partner. Zabbix's own AI direction is
> WebMCP, a browser standard, not an adoptable server.

**Decisions worth not re-litigating**
- **Adopt, not build** — the first time on this roadmap. The 3-tool passthrough is essentially the design
  NetClaw would have produced
- **Dedicated virtualenv, mandatory** — needs fastmcp 3.x while `netbox-mcp-server`,
  `CiscoFMC-MCP-server-community`, `Wikipedia_MCP`, `rag-mcp` and `ISE_MCP` all pin `<3`
- **Strictly read-only, no write path.** Adopt-as-is leaves nowhere to insert NetClaw's two gates, so writes
  were deferred rather than shipped ungated
- **The distinctions are enforced by SKILL, not structure** — the first NetClaw integration where that is
  true, and the accepted cost of adopting a generic passthrough

## R12 — APM + log platforms (Dynatrace / New Relic / Elastic)

**Status:** `DONE — Elastic only` · [spec 096](../specs/096-elastic-logs/spec.md).
**Dynatrace and New Relic remain open.**

Both APM vendors appear on Itential's 56-server list; NetClaw has neither. Elasticsearch was
absent and is extremely common for netops logging.

> **Scoped to the verifiable target**, the same cut R11 made (Zabbix only) and R17 made (DuckDB
> only). Both APM vendors are SaaS with no self-hostable path, so they would ship unverified —
> the blocker that gated R5 the same day. Elastic runs locally on a free `basic` licence, so its
> traps are reproducible.

> **The correction that shaped this item.** An initial claim that NetClaw had "no log search at
> all" was wrong: `splunk-mcp` (3 skills), `datadog-logs`, `gcp-logging-mcp` and `grafana-mcp`
> were already registered. What was missing is an **Elasticsearch backend**. Note also that
> `SPLUNK_HOST`/`SPLUNK_TOKEN` are unset in this environment and the endpoint is unreachable, so
> the Splunk skills currently point at nothing — which is why FR-004's backend boundaries matter
> more here than for a greenfield integration.

**Checklist**
- [x] Assess Dynatrace and New Relic official MCP availability — **deferred, SaaS-only**
- [x] Elastic/Elasticsearch MCP — **adopted**, 5 tools, 1,094/5,000 tokens, digest-pinned
- [x] Define the boundary against existing Splunk / Datadog / Grafana skills — FR-004, stated in
      the skill, SOUL.md and the data model: selection is by **where the data lives**, never by
      question shape; if unknown, ask
- [ ] Dynatrace — revisit if a tenant becomes available
- [ ] New Relic — revisit if a tenant becomes available

## R13 — NSM / IDS (Zeek / Suricata / Arkime) + packet-buddy audit

**Status:** `NOT STARTED`

The network-security-monitoring layer is entirely absent.

**Checklist**
- [ ] Audit the existing `packet-buddy-mcp` against `0xKoda/WireMCP` and SharkMCP
      (tshark, 20 tools) — there may be capability NetClaw is missing in its own server
- [ ] Assess Zeek (metadata), Suricata (IDS), Arkime (indexed full-packet search) —
      a typical stack uses all three
- [ ] Decide adopt vs build; these may need building
- [ ] Skills: session pivot, IDS alert triage, retrospective packet search

---

# Tier 4 — The layer beneath the network

## R14 — Kubernetes

**Status:** `DONE` — spec [084](../specs/084-k8s-readonly/spec.md)

`kubeshark` gave traffic visibility; NetClaw could not read a pod, service, ingress or NetworkPolicy.

**Checklist**
- [x] Pick a server; **start read-only** — done, and read-only turned out to be what makes adoption
      *possible*: the upstream default is 21 tools / 5,716 tokens and busts the manifest ceiling
- [x] kubeconfig / context handling and RBAC scoping — an **explicit, token-only** kubeconfig for a
      dedicated cluster-wide-read ServiceAccount. Never the ambient `current-context`, which may be
      production
- [x] Skills: NetworkPolicy review, service/ingress path tracing — delivered. **CNI health** partially:
      the objects are readable, vendor semantics are not (see follow-on)
- [x] Compose with `kubeshark` — the boundary is stated in all three skills: observed traffic vs declared
      configuration, and *reachable is not permitted*
- [ ] **Cilium/Calico CNI-specific tooling** — follow-on. Their CRDs are readable as objects through the
      generic resource tools; their *semantics* are not interpreted

**Landscape, measured by building and running each candidate**

| Candidate | Tools | Licence | Outcome |
|---|---|---|---|
| `containers/kubernetes-mcp-server` (Red Hat) | **7** trimmed / 21 default | Apache-2.0 | **adopted** |
| `Flux159/mcp-server-kubernetes` | 8 read-only / 23 default | MIT | fallback — see caution |
| `patrickdappollonio/mcp-kubernetes-ro` | 10 | MIT | good design, 23★, single maintainer |
| `rohitg00/kubectl-mcp-server` | **313** | MIT | **rejected twice over** |

> **`rohitg00` is disqualified twice**: 313 tools *and* it pins `fastmcp>=3.0.0b1` — spec 083's blocker
> reproduced exactly.
>
> **`Flux159` carries GHSA-cr22-wjx7-2w6m (High)** — read-only filtering was *bypassable*: tools hidden
> from `tools/list` were still callable. That is the exact mechanism one would depend on to fit the ceiling.
>
> **There is no official Kubernetes or CNCF MCP server.** `org:kubernetes mcp` → 0 repos; `org:cncf mcp` → 0.

**The finding worth carrying forward:** the Kubernetes API is *honest* — it returns a correct 403 on an
unauthorised cluster-wide list. The adopted server converts that into a plausible one-namespace answer with
no error (`resources.go:34-38`, permission error discarded). Reproduced live in NetClaw's own test suite.

## R15 — Redfish / BMC out-of-band

**Status:** `NOT STARTED`

Directly answers "is the box dead or is it the network" — a distinction NetClaw cannot make today.

**Candidates**
- `fredriksknese/mcp-redfish` — Dell iDRAC, HPE iLO, Supermicro, Lenovo XClarity
- `carlosedp/redfish-mcp-server`

Covers systems, chassis/thermal/power, BMC managers, storage controllers, event logs,
firmware inventory.

**Checklist**
- [ ] Adopt one; read-only first (power *control* is a write action needing approval)
- [ ] BMC credential handling via Vault
- [ ] Skills: hardware health check, thermal/power review, firmware inventory, SEL log triage
- [ ] Consider folding Cisco UCS/Intersight (R7) here instead of Tier 1

## R16 — VMware vSphere / NSX

**Status:** `NOT STARTED` · **Build, not adopt**

No mature MCP found in the scan. Significant gap given how much east-west networking lives
in NSX.

**Checklist**
- [ ] Re-scan for an MCP before committing to build — this may have changed
- [ ] If building: scope tightly to read-only inventory + NSX logical topology + DFW rules
- [ ] Assess against existing `fwrule-mcp` for DFW rule analysis reuse

## R17 — Database query layer

**Status:** `NOT STARTED` · **⚠️ premise weakened — read this before starting**

SuzieQ, ntopng, Arkime, and NetBox all sit on databases worth querying directly. DuckDB over
files is an excellent analysis substrate for exports.

> **Surveyed 2026-08-04: there is currently nothing to query.** Measured on the development host:
> `*.parquet` anywhere = **0 files**; SuzieQ parquet = **0**; `workspace/output/` holds documents and
> diagrams only; DuckDB and ClickHouse are **not installed**.
>
> And the **ClickHouse half of the rationale is gone**: ClickHouse arrives with ntopng, which is now
> **`DEFERRED`** because ClickHouse flow storage is Enterprise M+ only.
>
> Excluding the memory and RAG stores (below), what remains is `federation.db` (~700 KB) and the GAIT
> JSONL logs. Real, but thin — and *"ad-hoc analysis over exported network data"* has no data behind it.
>
> **Sequencing conclusion: R17 should follow whichever item first produces bulk exports** — R13
> (Zeek/Suricata logs) is now the most likely candidate, since R10 is deferred. Building the query layer
> first would ship a query engine with nothing to point at.

**Checklist**
- [ ] Decide scope: read-only analyst access, not a general write surface
- [ ] Prioritize DuckDB (file/export analysis) — **ClickHouse is no longer a near-term target** (R10 deferred)
- [ ] Strict read-only enforcement and query timeouts
- [ ] **Must not** expose `~/.openclaw/memory/` or `~/.openclaw/rag/rag.db`. *Precision on the citation:*
      spec 062's FR-030 binds **`rag-mcp`** not to read the Memory store; it is not literally a ban on other
      features reading `rag.db`. This roadmap imposes the wider constraint, on 062's isolation principle —
      a generic SQL surface over either store would be a backdoor. Honour it either way
- [ ] Skill: ad-hoc analysis over exported network data — **once such data exists**

---

# Tier 5 — Productivity and human deliverables

## R18 — Document generation (docx / pptx / xlsx / pdf)

**Status:** `DONE` — spec [082](../specs/082-document-generation/spec.md), merged in PR #211 · **Best effort-to-value ratio on the roadmap**

NetClaw can render Three.js topologies, drawio, markmap, UML, Blender and UE5 — but cannot
produce a change-record `.docx`, an exec `.pptx`, an interface-audit `.xlsx`, or fill a PDF.
Its output lands in front of enterprise humans.

**Source (reference only — see the licence finding):** `anthropics/skills` — `skills/docx`,
`skills/pptx`, `skills/xlsx`, `skills/pdf`.

> **⚠️ Correction, measured 2026-08-03 — "vendor the four official skills" cannot be done.**
> This section originally called R18 a vendor-first item. It is not. The four `anthropics/skills`
> document skills are **source-available and "provided for demonstration and educational purposes
> only"** — *not* Apache-2.0. (The repo's **example** skills are Apache-2.0; the document skills
> specifically are not.) NetClaw ships Apache-2.0 skills, so vendoring them is **not licence-
> compatible**, and spec 082 additionally rules out any installer or runtime fetch for them.
>
> R18 is therefore **build-rather-than-adopt for a licensing reason** — a different situation from
> R1/R3/R9, where the community options were technically inadequate. Upstream remains valuable as
> **reference for which capabilities matter** (tracked changes, find-and-replace, PDF form filling
> and merge/split, template-vs-scratch modes); reading it to decide *what* to build is legitimate,
> copying it is not.

**Checklist** *(revised by spec 082's clarification session)*
- [x] ~~Vendor the four official skills~~ — **struck on licence grounds.** Record the terms
      explicitly, cite upstream as capability reference, and ship **no vendored copy, no installer,
      no runtime fetch**
- [x] Confirm Python deps — **all four already installed** via `rag-mcp` (feature 062):
      `python-docx` 1.2.0, `openpyxl` 3.1.5, `python-pptx` 1.0.2, PyMuPDF 1.28.0. Note that rag-mcp
      declares them **unpinned**, a latent spec-077 hazard (PyMuPDF is imported as `fitz`); spec 082
      adds upper bounds in both places without moving any installed version
- [ ] Define the output location convention (persistent workspace output dir, timestamped,
      never overwritten — matching feature 046)
- [ ] NetClaw-specific wrapper skills: change record, incident report, interface/config audit
      workbook, exec summary deck
- [ ] Compose with existing report-delivery skills (`slack-report-delivery`,
      `webex-report-delivery`) so generated documents can actually be sent — **note:** spec 082 puts
      *sending* out of scope (Principle XIV); it writes files, the delivery skills send them

**Scope decisions from spec 082** (so they are not re-litigated):
- One MCP server owns all document writing, stamping generation time, attribution and per-element
  provenance at a single chokepoint; skills own the compositions and contain no writing logic
- Provenance must be **visible** — source column per spreadsheet row, per-figure source in documents
  and decks, plus a sources section in every file. Cell comments and document metadata do **not**
  satisfy it
- `.docx`/`.xlsx`/`.pptx` are built **from scratch**; corporate-template population is a follow-on.
  PDF form filling stays, because a PDF form's fields are explicitly named and machine-readable

## R19 — Google Workspace (official)

**Status:** `NOT STARTED`

Google shipped an official Workspace MCP server in preview (Drive, Gmail, Calendar, Chat).
NetClaw has Atlassian and MS Graph skills but nothing Google-side; many orgs are Google-first.

**Checklist**
- [ ] Adopt the official server; note preview status
- [ ] OAuth scope minimization — request read scopes first
- [ ] Skills mirroring the existing `msgraph-*` set so the agent can work either ecosystem
- [ ] Compose with R18 so generated documents can land in Drive

## R20 — Notion + Linear (official)

**Status:** `NOT STARTED`

Both now have official vendor MCPs.

**Checklist**
- [ ] Adopt both
- [ ] Decide how they relate to the existing ITSM provider abstraction (feature 070) —
      Linear is issue tracking, adjacent to Halo/ServiceNow/Atlassian
- [ ] Skills: knowledge capture to Notion, work-item lifecycle in Linear

## R21 — GitOps + Azure DevOps

**Status:** `NOT STARTED`

GitOps is how network config actually deploys now. NetClaw has Jenkins/GitLab/GitHub/Terraform
but no reconciler. Azure DevOps covers the Microsoft-shop half of the market.

**Checklist**
- [ ] ArgoCD MCP: list clusters, list/diff/sync applications, resource management
- [ ] Assess Flux as an alternative or addition
- [ ] Azure DevOps official MCP server
- [ ] Skills: config drift detection via ArgoCD diff, sync-with-approval, pipeline status
- [ ] Sync operations are writes — route through the approval path

## R22 — Diagram MCPs (Excalidraw + draw.io)

**Status:** `NOT STARTED`

Both appear on Itential's list. NetClaw has drawio as a *skill* only.

**Checklist**
- [ ] Assess whether a draw.io MCP adds anything over the existing `drawio-diagram` skill
- [ ] Excalidraw MCP for hand-drawn-style diagrams
- [ ] Likely low priority — may be `DROPPED` if the existing skill suffices

---

# R23 — IETF MCP-for-network-management landscape

**Status:** `DONE` — surveyed 2026-08-04 · **Strategic, not tooling**

Full survey: **[`docs/ietf/IETF-MCP-LANDSCAPE-2026-08.md`](ietf/IETF-MCP-LANDSCAPE-2026-08.md)**.
Recommendations seeded into `docs/ietf/NCFED-HARDENING-BACKLOG.md`; `AGENTPROTO-POSITIONING.md` corrected.

> **⚠️ This section's original April-2026 draft list was stale. Corrected below.**

**Checklist**
- [x] Read all four drafts — and found **`draft-zw-opsawg-mcp-network-mgmt` is EXPIRED**, one terminal of a
      four-name rename chain in which *every* link is now expired or replaced. There is no active revision of
      that work anywhere. **Do not cite it.**
- [x] Positioning note written — the discovery drafts answer *"where is this domain's endpoint?"*, never
      *"how do two agents come to trust each other?"*. Serra defines **no key pinning** and defers auth to
      OAuth; Morrison pins keys in DNS but **admits it has no revocation**
- [x] Decided on `-01` references — 8 recommendations, in priority order, in the backlog
- [x] Checked opsawg / nmrg — **opsawg has no live MCP work** (all expired; migrated to NMRG and NMOP).
      `draft-yang-nmrg-mcp-nm` reached **`-03`** with six authors across five carriers/vendors, but no
      adoption call was found
- [x] Fed into the `-01` backlog

**Corrected landscape (verified 2026-08-04)**

| Draft | Rev | State |
|---|---|---|
| `draft-zw-opsawg-mcp-network-mgmt` | 00 | **EXPIRED — do not cite** |
| `draft-yang-nmrg-mcp-nm` | **03** | Active to 2027-01-07. The healthy one; cite this |
| `draft-serra-mcp-discovery-uri` | 04 | Active but **expires 2026-09-25** |
| `draft-morrison-mcp-dns-discovery` | **05** | Active. `-05` is a **retraction revision** |

**Active MCP drafts: 13, not "15+".** The count went *down* — the Huawei cluster expired faster than new
drafts arrived. Searching "agent" instead returns **199** active drafts: MCP is a small corner of a much
larger space, and NCFED sits in the larger one.

**What the original entry missed entirely**

- **`agentproto` WG-forming BOF, IETF 126 Vienna, 2026-07-23.** Form a WG: **154–51 yes**. Proposed scope:
  **38–124 — rejected.** The room wants a WG and refused the charter it was handed; the refocus toward
  *context propagation across trust boundaries* is **closer to NCFED's contribution** than the original
  session-layer framing. **Not chartered yet.**
- **`dawn` BOF** ("Discovery of Agents, Workloads, Named Entities"). Its problem statement explicitly
  assumes trust is already established and proposes **no trust model** — precisely NCFED's slot, and a
  better citation target than either MCP discovery draft.
- **`draft-bu-agentproto-security-principal-binding-04`** (2026-08-02) supplies a reusable claims matrix
  authors are meant to fill in. **The cheapest high-credibility `-01` addition available.**
- **The pushback to pre-empt is revocation** — the IETF direction is WIMSE/SPIFFE short-lived credentials
  (`draft-klrc-aiagent-auth-03`), and NCFED's long-lived pinned keys will draw exactly that question.

**Follow-on:** none as tooling. This item is complete as strategy; the work it generated lives in the NCFED
`-01` backlog.

# R24 — Open-territory triage

**Status:** `DONE` · [spec 097](../specs/097-open-territory-triage/spec.md) ·
**[full dispositions → TRIAGE.md](../specs/097-open-territory-triage/TRIAGE.md)**

All 22 candidates triaged 2026-08-05. The table below is a **summary** — the reasons, evidence and
unblocking conditions live in `TRIAGE.md`, deliberately not duplicated here.

| Disposition | Count | Which |
|---|---|---|
| `COVERED` | **4** | Nokia SR Linux/SR OS, SONiC, VyOS, MikroTik RouterOS — **all absorbed by R1** |
| `SELECTED` | **1** | **Arista ANTA** — see below |
| `DEFERRED` | **12** | gNOI, Ciena, Infinera, Nokia NSP, Netskope, Cato, Versa, Aviatrix, Alkira, Megaport, Hamina, UniFi |
| `DROPPED` | **5** | netlab, Oxidized/Netpicker, Open5GS, free5GC, Ekahau |

> **R1 absorbed four of the 22 and nobody noticed.** R24 was written 2026-07-30; R1 merged after it
> and the list was never re-checked — which is exactly what R24's own first checklist item asked
> for. Only **one** of those four (SR Linux) is verified live; the other three are claimed on the
> strength of the driver's platform table, and the triage records that distinction rather than
> smoothing it over.

> **Two premises were stale.** **Megaport is no longer "genuinely unclaimed"** — an official MCP
> server now exists (open beta, read-only, staging environment documented), which makes it an
> *adopt* candidate whose manifest cost would decide it. And **MikroTik's "adopt a dedicated MCP"**
> entry predates R1, which now reaches it. Do not trust "unclaimed" for any remaining candidate
> without re-checking.

### The selection — Arista ANTA (new roadmap item **R25**)

The only candidate that is both a capability nothing here has **and** verifiable with access already
on disk.

NetClaw can read state (pyATS, R1, gNMI), read what the manager says (CVP), and read state over time
(SuzieQ, Zabbix). It has **no assertion layer** — nothing that takes a declarative expectation and
returns a structured pass/fail verdict. ANTA is exactly that.

**Access check**: an Arista vEOS image is already on disk (`~/clab-images/`), containerlab is
installed and registered, ANTA is pip-installable, **no vendor account is required.** It is the only
candidate whose verification path needs nothing obtained.

**Known design risk**: ANTA's test catalogue is large. One tool per test would blow the ceiling as
Catalyst Center's 515 tools did — the expected shape is a dispatcher plus discovery (the 087
pattern), and the manifest must be **counted, not estimated** (the R5 lesson).

### Cheapest deferrals to revisit first

**Megaport** (needs only a staging account — the server already exists) and **UniFi** (needs a
self-hostable controller with one adopted device). Both are credential/setup problems, not build
problems.

> The untriaged candidate list that stood here has been replaced by the summary above. It is
> preserved in full, with a disposition and reason for every entry, in
> [TRIAGE.md](../specs/097-open-territory-triage/TRIAGE.md).

**Checklist**
- [x] After R1 lands, re-test which platforms remain genuinely unreachable — **4 of 22 absorbed**
- [x] Pick at most one or two flag-planting targets — **one: Arista ANTA**. The roadmap's own guess
      named Megaport and ANTA as strongest; ANTA held up, Megaport did not (an official MCP now
      exists, and no account is available here)
- [x] Everything else: recorded as `DEFERRED` or `DROPPED` with a reason and, where deferred, the
      condition that would change the answer

---

# R25 — Arista ANTA: structured network-state validation

**Status:** `DONE` · [spec 098](../specs/098-arista-anta-validation/spec.md) — created by [R24's triage](../specs/097-open-territory-triage/TRIAGE.md) and built the same day

The assertion layer NetClaw does not have. Every existing source answers *what is the state*, *what
does the manager say*, or *what was the state over time*. Nothing answers **does the state match
what it should be**, as a structured pass/fail verdict.

**Why this is Tier A**: verifiable with access already on disk — vEOS image present, containerlab
installed, ANTA pip-installable, **no vendor account required**. It is the only R24 candidate whose
verification path needs nothing obtained.

**Checklist**
- [ ] Measure the manifest before designing: ANTA's catalogue is large, and one tool per test would
      repeat Catalyst Center's 12.9× ceiling breach. **Count, do not estimate**
- [ ] Expected shape: dispatcher + discovery (the 087 pattern), not one tool per test
- [ ] Verify live against vEOS in containerlab — the access check that made this selectable
- [ ] Define the boundary against `arista-cvp-mcp` (management plane) and R1 (device CLI): ANTA is
      the *validation* plane and must not duplicate either
- [ ] Read-only: ANTA runs tests, it does not change devices

---

# Recommended execution order

> **Rewritten 2026-08-05.** The original order was written before anything shipped and is now
> history. Everything it sequenced is done. The current order lives in
> [Where we are](#where-we-are--tally-as-of-2026-08-05) at the top of this document; this section
> keeps the record of what was executed and the two rules that emerged from executing it.

## What was executed, in order

`R0` → `R1` → `R18` → `R8` → `R2` → `R3` → `R14` → `R15` → `R13` → `R17` → `R11` → `R9` → `R23`
→ `R12`, with `R0a`/`R0b` inserted when the foundation turned out to be less solid than R0 had
established, and `R10`/`R22`/`R5` closed without building.

## Rule 1 — sequence by verifiability, not by value

Three items stalled on the same question in one week: **can this be verified today, with the access
we actually have?**

R10's free edition could not do the job. R12's APM half is SaaS-only. R5's org is empty. In each
case the item was worth building and could not be *proven*, which is not the same as being built.

**Confirm access before writing the spec.** That check costs minutes. Discovering it afterwards cost
R5 a day.

## Rule 2 — the premise is not a given, it is the first measurement

Four roadmap premises did not survive contact with reality:

| Item | The premise | What measurement found |
|---|---|---|
| **R2** | Four Cisco API families | Three return 403 under the API Console grant — rescoped to PSIRT alone |
| **R10** | ntopng gives flow history | Enterprise M+ only, verified in ntop's own `Prefs.cpp:3381` |
| **R17** | A query layer is needed | Nothing to query until R13 produced exports — resequenced |
| **R22** | Diagram coverage is missing | Already satisfied; Excalidraw is an aesthetic, not a capability |

**Twice the operator questioned the premise and was right** (R22, and the "we have lots of visuals
already" challenge that produced 093's real defect). A roadmap item is a hypothesis, not an
instruction.

## Rule 3 — measure the manifest before deciding adopt-vs-build

The 5,000-token ceiling has decided more designs than any architectural preference:

| Item | Tools | Manifest | Outcome |
|---|---|---|---|
| **R12** Elastic | 5 | **1,094** | adopt as-is |
| **089** Meraki | 2 | **1,561** | adopt as-is |
| **R14** k8s | 21 → 7 | 5,716 → **1,643** | adopt, trimmed |
| **087** Catalyst Center | 515 → 10 | 64,420 → **1,821** | build a dispatcher over the catalogue |
| **R5** Mist | 7 | **11,783** | **reject** — no filtering mechanism exists |
| **093** MS-365 | 188 | **225,355** | adopt only a filtered 12-tool subset |

**Count, do not estimate, within ~20% of the ceiling.** The chars/4 convention under-reported Mist's
manifest by 17% (10,052 estimated vs 11,783 measured) — enough to turn a "fits" into a breach.

---

# Appendix — reproducing the R0 measurements

```bash
cd ~/netclaw

# repo vs live entry counts and drift
python3 - <<'EOF'
import json, os
def servers(d):
    return d.get('mcpServers') or d.get('mcp', {}).get('servers') or {}
repo = servers(json.load(open('config/openclaw.json')))
live = servers(json.load(open(os.path.expanduser('~/.openclaw/openclaw.json'))))
print("repo:", len(repo), "live:", len(live))
print("live not in repo:", sorted(set(live) - set(repo)))
print("repo not in live:", len(set(repo) - set(live)))
EOF

# vendored dirs not referenced by any config path
python3 - <<'EOF'
import json, os, re
repo = json.load(open('config/openclaw.json'))
srv = repo.get('mcpServers') or repo.get('mcp', {}).get('servers') or {}
refd = set(re.findall(r'mcp-servers/([A-Za-z0-9_.\-]+)', json.dumps(srv)))
dirs = {d for d in os.listdir('mcp-servers') if os.path.isdir(f'mcp-servers/{d}')}
for d in sorted(dirs - refd):
    print(" -", d)
EOF
```

---

## Sources

Landscape scan, 2026-07-30.

- [Itential — The Ultimate MCP Guide for Network Automation (56 servers)](https://www.itential.com/resource/guide/the-ultimate-mcp-guide-for-network-automation/)
- [wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers)
- [anthropics/skills](https://github.com/anthropics/skills)
- [Juniper — Mist MCP Server with Claude Desktop (official)](https://www.juniper.net/documentation/us/en/software/mist/mist-aiops/shared-content/topics/concept/juniper-mist-mcp-claude.html)
- [nowireless4u/hpe-networking-mcp](https://github.com/nowireless4u/hpe-networking-mcp) · [secure-ssid/centralmcp](https://github.com/secure-ssid/centralmcp)
- [rstierli/fortimanager-mcp](https://github.com/rstierli/fortimanager-mcp) · [paoloamato2/fortinet-mcp-server](https://mcpservers.org/servers/paoloamato2/fortinet-mcp-server) · [ivillagomez/fortigate-mcp](https://lobehub.com/mcp/ivillagomez-fortigate-mcp)
- [cdot65/pan-os-mcp](https://github.com/cdot65/pan-os-mcp)
- [sydasif/nornir-mcp-server](https://glama.ai/mcp/servers/sydasif/nornir-mcp-server) · [ntunes/netmiko-mcp-server](https://github.com/ntunes/netmiko-mcp-server)
- [sieteunoseis/mcp-cisco-support](https://developer.cisco.com/codeexchange/github/repo/sieteunoseis/mcp-cisco-support/) · [Cisco PSIRT openVuln API](https://developer.cisco.com/docs/psirt/)
- [beye91/nexus-dashboard-mcp](https://mcpservers.org/servers/beye91/nexus-dashboard-mcp) · [Cisco Network MCP Docker Suite](https://gblogs.cisco.com/ch-tech/network-mcp-docker-suite/)
- [jsdelivr/globalping-mcp-server](https://github.com/jsdelivr/globalping-mcp-server)
- [jrelph/ripe-atlas-mcp](https://github.com/jrelph/ripe-atlas-mcp) · [PeerCortex](https://mcpmarket.com/server/peercortex) · [dadepo/whois-mcp](https://www.mcpserverfinder.com/servers/dadepo/whois-mcp)
- [ntopng MCP Server (official)](https://www.ntop.org/ai-powered-network-monitoring-introducing-ntopng-mcp-server/)
- [Flux159/mcp-server-kubernetes](https://github.com/Flux159/mcp-server-kubernetes) · [rohitg00/kubectl-mcp-server](https://github.com/rohitg00/kubectl-mcp-server) · [Red Hat Kubernetes MCP server](https://developers.redhat.com/articles/2025/09/25/kubernetes-mcp-server-ai-powered-cluster-management)
- [fredriksknese/mcp-redfish](https://github.com/fredriksknese/mcp-redfish) · [carlosedp/redfish-mcp-server](https://github.com/carlosedp/redfish-mcp-server)
- [0xKoda/WireMCP](https://github.com/0xKoda/WireMCP)
- [NetBox MCP Server (official)](https://netboxlabs.com/docs/mcp/)
- [Google Workspace MCP server (official, preview)](https://workspace.google.com/blog/product-announcements/10-more-announcements-workspace-at-next-2026)
- [CiscoDevNet/webex-mcp-official](https://developer.cisco.com/codeexchange/github/repo/CiscoDevNet/webex-mcp-official/)
- [draft-zw-opsawg-mcp-network-mgmt](https://www.ietf.org/archive/id/draft-zw-opsawg-mcp-network-mgmt-00.html) · [draft-yang-nmrg-mcp-nm](https://datatracker.ietf.org/doc/draft-yang-nmrg-mcp-nm/) · [draft-serra-mcp-discovery-uri](https://datatracker.ietf.org/doc/draft-serra-mcp-discovery-uri/) · [draft-morrison-mcp-dns-discovery](https://datatracker.ietf.org/doc/draft-morrison-mcp-dns-discovery/) · [MCP at the IETF — overview](https://chatforest.com/guides/mcp-ietf-standardization/)

---

# R1 — Generic multivendor CLI driver (outcome)

**Status:** `DONE` (2026-07-31, spec 076) · 94/94 tasks

## What shipped

`mcp-servers/multivendor-cli-mcp` — 10 tools, read-only by default, reaching platform families no
other NetClaw device server can.

| Verified live | Evidence |
|---|---|
| Nokia SR Linux (native NOS CLI) | `show version`, `show interface brief` real output |
| FRR (shell-hosted, `vtysh`) | real routing table via the `linux` driver |
| IOS-XE normalized read | NAPALM `ios`, real hostname/interfaces — FR-008 exception |
| SR Linux normalization gap | reported as a row with a reason, never omitted — FR-007 |
| Fleet fan-out | `requested == returned` with an unreachable device isolated |
| ServiceNow CR gate | live instance: production + approval but no CR → **blocked** |

**31/31 live integration checks**, 175 platform families driver-documented.

## Both candidate servers were rejected

`sydasif/nornir-mcp-server` is **archived** (June 2026, 2 stars) and reloads `config.yaml` from cwd on
every call, threading its inventory assumption through the request path.
`ntunes/netmiko-mcp-server` has **no command filtering at all** (3 stars, 5 commits). Both store
credentials in YAML. Built on the libraries instead, deliberately porting candidate A's safety design
(prefix allowlist, destructive-token denylist, chaining prevention, path sandboxing) — the part most
easily got wrong.

## Three bugs only real devices found

1. **The filter blocked FRR's only read path.** `vtysh -c "show ip route"` starts with `vtysh`. The
   tempting fix — allowlisting `vtysh` — would have permitted `vtysh -c "configure terminal"`, a config
   escape. Fixed by unwrapping wrappers and judging the inner command.
2. **SR Linux was under-protected.** `nokia_srl` (driver/inventory) ≠ `nokia_srlinux` (denylist table),
   so it missed `tools system configuration`. Fixed with alias normalisation.
3. **Principle III had zero coverage.** `/speckit.analyze` caught it: the plan claimed ITSM gating was
   "inherited from the existing approval path", which was an assertion. Human approval and a
   ServiceNow CR are distinct gates.

## Caveat for R3/R4

netmiko also drives Fortinet, PAN-OS and Check Point, so this server gives **CLI-level** reach to them.
That is not FortiManager's policy packages or Panorama's device groups. R3 and R4 are still needed.

**R3 confirmed this exactly.** Spec 080 shipped the Fortinet API and manager planes alongside — not
replacing — this driver's CLI reach, and all three Fortinet skills state the boundary in both directions.
R4 (Panorama) remains open on the same reasoning.

## Lab

`labs/multivendor-r1/` — containerlab topology (SR Linux, public image, no account) and an FRR+sshd
Dockerfile. The repo's existing `netclaw-*` FRR containers cannot be used: no `sshd`, and they are
live BGP peers.

---

# R0a — Dependency-pin hazards (outcome)

**Status:** `DONE` (2026-07-31, spec 077) · 41/41 tasks

Fresh installs work again, and the three breakage classes now fail loudly. All three broke *new* installs
only, which is why none was noticed.

## What shipped

| Repair | Scale |
|---|---|
| Pins bounded (unbounded + submodule import) | **25 failures across 20 servers**, 15 of them `mcp`/`fastmcp` |
| Bare pip calls routed through `netclaw_pip_install()` | **130** |
| `gait-venv-setup.sh` unbounded `uv pip install gait-ai mcp fastmcp` | bounded — GAIT is the Principle IV audit trail |
| Dead `fastmcp` declarations removed | 2 (`n2n-mcp`, `protocol-mcp`) |
| New gate surface | `dependencies` in `reconcile-mcp.py` — **four surfaces**, all green |
| Contract tests | 23/23, including false-positive guards |

## The finding worth remembering

**My audit found 7 exposed servers. The static scan found 25 failures across 20.** The audit looked for a
pattern it already knew — unbounded `mcp>=` plus a `mcp.server.fastmcp` import. The scan looked for the
*class*: any unbounded pin on any package whose submodule is imported.

A human audit finds what it expects. A static scan finds what is there. That is the whole case for
deriving the check from source rather than from a maintained list.

## Three figure corrections

Recorded in the spec rather than quietly patched, because a spec whose numbers shift silently is not
trustworthy:

1. **"188 bare pip calls" counted comments and log messages.** Real figure: **130** executable.
2. **Hazard 3 had ZERO instances.** Both venv sites were already correct — `gait-venv-setup.sh` uses
   `uv venv` and documents why. The grep matched the comment *explaining* the problem.
3. **`n2n-mcp` needed no migration.** It imports `mcp.server.fastmcp` like the others. The approved
   `fastmcp` 2.x migration would not have fixed it, since fastmcp 2.x provides no `mcp/server/fastmcp`.
   Proceeded with the correct minimal fix instead of executing an instruction premised on my own error.

## One requirement dropped

**FR-006c** (flag declared-but-unimported dependencies) is dropped as unimplementable reliably: a
distribution name is not a module name (`python-dotenv` → `dotenv`), and resolving that needs
`importlib.metadata` against *installed* packages. The first implementation produced **187 findings,
nearly all false** — and a noisy check trains people to ignore it, which is worse than no check.

## Inherited by R2–R24

`docs/ADDING-AN-MCP.md` now carries both rules: bound any pin on a package whose submodule you import,
and never call bare `pip`. The gate enforces both, and an exception requires a stated reason.

---

# R2 — Cisco PSIRT vulnerability intelligence (outcome)

Spec [078](../specs/078-cisco-psirt-vulnerability/spec.md). 52/52 tasks. **109 offline checks, 34 live
API checks, full chain verified on live CML routers.**

## The rescope: eight API families became one

R2 was planned as "Cisco Support APIs (PSIRT / EoX / Bug / Case)". Measuring first — before writing the
spec — cut it to PSIRT alone:

| Family | Result | Consequence |
|---|---|---|
| PSIRT openVuln | **200** | The feature |
| Bug Search | **403** | Dropped |
| EoX | **403** | Dropped — so "is this past EoL?" is still unanswerable |
| Case | **403** | Dropped |
| Serial→Info | **403** | Dropped |
| CX Cloud (7 paths) | **504** | Dropped — needs a separate tenant subscription |

The API Console grant covers PSIRT and nothing else. This is why the community candidate
(`sieteunoseis/mcp-cisco-support`, 46 tools across 8 families) was **not adopted**: seven-eighths of that
tool manifest would have been dead surface, costing tokens on every turn to advertise capabilities that
return 403.

**EoL/EoS lookup remains an open gap.** It was half of R2's original value proposition, and it is not
delivered — not descoped for convenience, but unreachable with the entitlement available.

## `iosxr` is not an OSType

Every version tried (7.5.2, 6.6.3, 24.1.1) returned **404 with an empty body**, against an `iosxe` 200
control in the same session. The six supported families return `INVALID_<OS>_VERSION` for a bad version,
which proves the OS itself was recognised — `iosxr` returns nothing of the kind.

This is worth stating loudly in the skill because NetClaw *can* reach IOS-XR through pyATS, so an
operator will reasonably expect the version check to work. It is refused with a pointer to `check_cve`,
never silently attempted.

## The finding that changed the design: version formats contradict each other

The spec assumed one normalisation rule (`A.B(C)` → `A.B.C`) and that only `iosxe` could be verified.
Probing all seven families live produced something different:

| OSType | Accepted | Rejected |
|---|---|---|
| `iosxe` | `17.3.1`, `17.03.01`, `17.3.1a` | `17.3(1)` |
| `ios` | `15.2(4)E`, `15.2(4)E10` | `15.2.4E` |
| `nxos` | `9.3(5)` | `9.3.5` |
| `asa` | `9.16.1` | `9.16(1)` |
| `ftd` / `fmc` | `7.0.1` | `7.2(0)` |
| `aci` | `15.2(3e)`, `16.0(3e)` | `5.2(3e)`, `5.2.3` |

**The conversion runs in both directions**, chosen per family — `ios` and `nxos` require exactly the form
`iosxe` rejects, and `aci` needs the letter suffix *inside* the parentheses where `ios` needs it outside.
The single global rule the spec drafted would have broken `ios` and `nxos` on **every** call.

It also means all seven normalisers are **verified**, not one. The spec's `normaliser_verified` flag was
designed for a world where six were untestable; they turned out to be testable directly against the API,
and testing them is what exposed the contradiction. The flag stays — a future Cisco OSType will arrive
unverified, and the mechanism that says so has to already exist.

**`aci` wants the switch image version**, not the APIC version: `15.2(3e)` returns advisories, `5.2(3e)`
is rejected. An operator reading the number off an APIC hands over something the API refuses.

## Two bugs the live calls caught that offline tests alone would not have

1. **An unanchored `re.sub` deleted the whole banner.** A `Cisco\s+IOS.*$` alternative meant to strip a
   trailing fragment matched from the first word of a real `show version` line and consumed everything, so
   valid input normalised to nothing.

2. **A trailing `\b` silently truncated `17.3(1)` to `17.3`.** `\b` cannot match after `)` at
   end-of-string, so the regex engine backtracked past the parenthesised build to find *something*. The
   truncated version then queried the API perfectly cleanly and returned a plausible advisory count **for
   a version the device is not running**.

The second is the more instructive one, and it is the entire argument for FR-009a. A wrong-but-parseable
version does not fail — it answers confidently about different software. Normalisation is now anchored:
a candidate that does not match *in its entirety* is rejected rather than salvaged.

## The distinction the feature exists to protect

Five outcomes, and two of them look identical in the data:

- `none_published` — Cisco has published nothing for this version. **Not "the device is secure."**
- `normalisation_failed` / `api_error` — **the question was never asked.**

An empty advisory list reads as a clean bill of health. Collapsing a parse failure into one would tell an
operator a device is safe when nothing was checked. The rule lives inside `normalise.py` rather than the
tool layer, because if the normaliser can emit a version that reaches the API, the confusion is already
possible no matter how careful the tool layer is.

`check_versions` reports `outcome_summary` counts for exactly this reason: before calling a fleet clean,
you have to look at how many devices were never checked.

## Verified end to end on live hardware

pyATS read **IOS-XE 17.16.1a** off a live CML router; PSIRT returned **26 advisories — 14 High, 11 Medium,
1 Critical** (`cisco-sa-http-code-exec-WmfP3h3O`, CVSS 9.0, CVE-2025-20363). The raw `show version` banner
and the Genie-parsed version normalised identically, proving the banner path. No human typed a version.

## Rate budget

5/sec and **30/min shared** — the per-minute limit is the real constraint. Order is contractual:
de-duplicate → cache → pace → back off. Measured: 60 devices on 12 distinct versions cost **12 calls, not
60**. De-duplication is first because it is the largest win; pacing an un-de-duplicated sweep just spreads
the same excess over more minutes.

## A split-toolchain note for later specs

`pyATS`/`genie` on this host are importable **only** from `/usr/local/bin/python3.13`, not
`/usr/bin/python3` (3.14.4) — the stranded site-packages R0a documented. The chain verification therefore
ran as two processes, which is how it works in production anyway (two MCP servers, two interpreters). Any
future spec that wants pyATS and a 3.14-installed server in **one** process will hit this.

## Principle XI artifacts

All eight, explicitly — because PR #204 found three missing after R1 and `reconcile-mcp.py` catches none
of them: catalog entry, **both** `PROFILE_SECURITY` and `PROFILE_CISCO`, install function, portable
registration, **both** HUD entries (node list *and* annotation map), SOUL capability section, README/TOOLS
tables, `.env.example`. `reconcile-mcp.py` exits **0** across all four surfaces.

While adding the README rows, R1's `multivendor-cli` was found to have **no row in either README table**
either — a Principle XI gap the gate cannot see, since it counts catalog and config entries rather than
table rows. Added in this branch.

---

# R8 — Globalping outside-in measurement (outcome)

Spec [079](../specs/079-globalping-probes/spec.md). 36/36 tasks. **48 offline checks, 34 live checks.**

R8 was rated the highest value-per-effort item in the original scan, and that held: **no server was written.**
One remote registration, one skill, eight Principle XI artifacts. The whole feature is a registration plus
prose — which is exactly why the prose had to be right.

## What it closes

Every device-facing integration NetClaw has looks at the network **from inside** the operator's domain. This
is the first that looks **at it from outside** — ~4,800 probes across ~1,390 autonomous systems, measuring
*toward* a public target. It answers "the router is fine, so why can't anyone reach us?", which NetClaw
previously could not address at all.

## The safety semantic: three ways to get nothing back

| Response | Meaning |
|---|---|
| `no_probes_found` (422) | **The measurement never ran.** No probe matched the filter. Says nothing about the target. |
| `finished`, 0-of-N successful | **The target did not answer.** A real finding. |
| Private/internal target | Out of scope — refused **locally, before calling out**. |

The first is the trap: it arrives failure-shaped and, read carelessly, looks like a total outage. An agent
reporting it as one escalates an incident that does not exist. Same class as R2's "no advisories ≠ not
vulnerable", and handled the same way — explicitly named states and a skill that spells out the difference.

The local refusal of private targets is worth noting as a **disclosure control rather than a correctness
one**. Globalping rejects RFC1918/loopback/link-local itself, with good error text. But by the time it does,
an internal address or hostname has already been transmitted to a third party. So NetClaw refuses first.

## The error I made, and the correction

**My first research pass concluded that one call costs one measurement regardless of probe count, and I built
guidance on "breadth is free".** That was wrong.

The mistake: 35 exploratory calls moved the remaining allowance from 500 to 465, and I read the matching
arithmetic as proof of per-call billing. It was a coincidence — most of those calls happened to use
`limit: 1`. I inferred a billing model from an uncontrolled sample.

A controlled test, one call at a time with the budget read either side:

| `limit` | cost |
|---|---|
| 1 | **1** |
| 5 | **5** |
| 20 | **20** |
| a `limits` call | **0** |

**Cost equals probe count.** The wrong conclusion had already propagated into the spec (FR-013a), the skill's
budget section, the task list, the contract, the quickstart and the offline test assertions — all of which
told the agent the opposite of the truth. All were corrected, and the error is recorded in research R4 rather
than overwritten.

Two things worth keeping from this:

1. **The narrative I liked was the tell.** "This spec inverts the previous one's budget strategy" was a
   satisfying story, and satisfying stories are exactly where an uncontrolled inference survives review.
2. The offline suite now asserts the *absence* of the wrong claim, not merely the presence of the right one.
   A stale sentence sitting beside a correct one is worse than either alone.

## The vendor's own documentation is wrong

`AS13335` appears as a location example **in Globalping's own tool schema**, and it never returns probes —
Cloudflare hosts none. Nor does AS15169 (Google). AS3320, AS16509 and AS174 do.

An earlier NetClaw scan had recorded an unresolved "Globalping location syntax bug". That was **two separate
things conflated**: a genuine syntax issue (`London,UK` fails — `+` is the AND separator, not a comma) and a
probe-availability fact (`AS13335` is correct syntax with no probes). Anyone learning the syntax from the
vendor's example tries `AS13335` first, gets `no_probes_found`, and concludes ASN filtering is broken. The
skill names this explicitly so the wrong lesson isn't learned.

Ground truth came from cross-checking `GET /v1/probes`: 4,833 probes, 1,390 distinct ASNs.

## The capability is smaller than the tool count

12 tools advertised; **6 of them take only the `context` argument** (`help`, `authStatus`,
`compareLocations`, `get_more_tools`, `limits`, `locations`). The real capability is **5 measurement tools**.
Worth remembering when comparing integration sizes across the roadmap — a tool count is not a capability
count.

## An unanticipated privacy surface

Every tool declares a required `context` parameter: a 15-25 word natural-language explanation of *why* the
call is being made, which the vendor states is used for "analytics and user intent tracking".

No other NetClaw integration asks for this. Every other one sends only what the operation requires; this one
asks for a description of intent. Two consequences:

- Constitution Principle XIV needed an actual decision rather than a checkmark. Resolved as
  **sanitisation plus disclosure**, not a per-call gate — gating every ping would make the integration
  useless and train operators to click through. NetClaw sends a generic, task-shaped value with no customer
  name, internal hostname, ticket reference or topology detail, and the skill states plainly that the field
  leaves the building so an operator can decline the integration entirely.
- **It is not actually enforced.** Calls with `context` omitted succeed. NetClaw still sends it — relying on
  unenforced-required behaviour would break every call at once if that changed — but the fallback is
  recorded.

Also: `limits` output echoes a short fragment of the token, flagged in the skill so raw output isn't pasted
into a ticket.

## Principle XI artifacts

All eight: catalog entry, `PROFILE_OBSERVABILITY` **and** `PROFILE_RECOMMENDED` (it needs no install and
closes a structural gap), install function, portable registration, **both** HUD entries (node list *and*
annotation map), SOUL capability section, README/TOOLS tables, `.env.example`. `reconcile-mcp.py` exits **0**
across all four surfaces.
