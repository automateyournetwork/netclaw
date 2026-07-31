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

## Status board

### Foundation (blocks everything else)

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R0** | MCP config reconciliation — repo vs live vs vendored | [075](../specs/075-mcp-config-reconciliation/spec.md) | `DONE` |
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
| **R3** | Fortinet (FortiOS / FortiManager / FortiAnalyzer) | — | `NOT STARTED` |
| **R4** | Palo Alto PAN-OS / Panorama NGFW | — | `NOT STARTED` |
| **R5** | Juniper Mist (official) + Apstra | — | `NOT STARTED` |
| **R6** | HPE Aruba Central / ClearPass / EdgeConnect / GreenLake | — | `NOT STARTED` |
| **R7** | Cisco Nexus Dashboard / Intersight / UCS | — | `NOT STARTED` |

### Tier 2 — The internet / external plane

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R8** | Globalping — outside-in probe measurement (remote MCP) | [079](../specs/079-globalping-probes/spec.md) | `DONE` — 36/36. NetClaw's first vantage point **outside** its own domain. 5 measurement tools from ~4,800 probes; zero install. Three-way distinction enforced: `no_probes_found` = never ran, 0-of-N = unreachable, internal = refused locally. **Budget is per probe, not per call** — my first research pass got this backwards and a controlled test corrected it |
| **R9** | BGP & registry intelligence (RPKI / RDAP / PeeringDB / RIPE Atlas) | — | `NOT STARTED` |

### Tier 3 — Monitoring and traffic layers

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R10** | ntopng — flow analytics platform | — | `NOT STARTED` |
| **R11** | SNMP-poller NMS (Zabbix / LibreNMS / Netdata) | — | `NOT STARTED` |
| **R12** | APM + log platforms (Dynatrace / New Relic / Elastic) | — | `NOT STARTED` |
| **R13** | NSM / IDS (Zeek / Suricata / Arkime) + packet-buddy audit | — | `NOT STARTED` |

### Tier 4 — The layer beneath the network

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R14** | Kubernetes (pods/services/ingress/NetworkPolicy + Helm) | — | `NOT STARTED` |
| **R15** | Redfish / BMC out-of-band (iDRAC / iLO / XClarity) | — | `NOT STARTED` |
| **R16** | VMware vSphere / NSX (build, not adopt) | — | `NOT STARTED` |
| **R17** | Database query layer (Postgres / ClickHouse / DuckDB / SQLite) | — | `NOT STARTED` |

### Tier 5 — Productivity and human deliverables

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R18** | Document generation — docx / pptx / xlsx / pdf | — | `NOT STARTED` |
| **R19** | Google Workspace (official) | — | `NOT STARTED` |
| **R20** | Notion + Linear (official) | — | `NOT STARTED` |
| **R21** | GitOps + Azure DevOps (ArgoCD / Flux) | — | `NOT STARTED` |
| **R22** | Diagram MCPs — Excalidraw + draw.io | — | `NOT STARTED` |

### Strategic (not tooling)

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R23** | IETF MCP-for-network-management landscape → NCFED `-01` input | — | `NOT STARTED` |

### Open territory (build candidates — assess before scheduling)

| ID | Title | Spec # | Status |
|----|-------|--------|--------|
| **R24** | Open-territory triage — pick flag-planting targets | — | `NOT STARTED` |

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

**Status:** `NOT STARTED`

Largest single-vendor absence. `fortimanager-ops` skill exists with no server behind it.

**Candidates**
- `ivillagomez/fortigate-mcp` — read-only FortiGate + FortiAnalyzer; best default safety posture
- `rstierli/fortimanager-mcp` — FortiManager JSON-RPC: policies, devices, scripts
- `paoloamato2/fortinet-mcp-server` — entire FortiOS 7.6.6 REST API as 200+ typed tools

All three are community, not Fortinet-endorsed.

**Checklist**
- [ ] Decide the entry point: device-level (FortiGate), manager-level (FortiManager), or both
- [ ] If adopting the 200+ tool server, assess token cost of the tool manifest — this may need
      a filtered/lazy tool surface (see feature 006 token optimization)
- [ ] Start read-only; gate policy writes behind approval
- [ ] Back-fill the existing `fortimanager-ops` skill against the real server
- [ ] Skills: policy audit, VPN tunnel status, FortiAnalyzer log query

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

**Status:** `NOT STARTED`

`junos-mcp-server` covers devices. Nothing covers Mist wired/wireless assurance or Marvis.
Juniper ships an **official** Mist MCP server (Claude Desktop beta).

**Checklist**
- [ ] Adopt the official Juniper Mist MCP server; note its beta status and org scoping
- [ ] Mist API token + org ID handling
- [ ] Skills: wireless assurance, client troubleshooting, Marvis query, SLE review
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

## R9 — BGP & registry intelligence

**Status:** `NOT STARTED`

**Candidates**
- `PeerCortex` — 34 tools consolidating PeeringDB, RIPEstat, RIPE Atlas, RouteViews,
  RPKI validators; also ships a dashboard and REST API
- `jrelph/ripe-atlas-mcp` — RIPE Atlas measurements (credit-based)
- `dadepo/whois-mcp` — WHOIS/RDAP for domains, IPs, ASNs; AS-SET expansion; RIPE route-object
  validation
- Also seen: a 5-RIR RDAP + RPKI + BGP visibility + abuse-contact server

**Checklist**
- [ ] Decide consolidated (PeerCortex) vs composed (atlas + whois + rpki separately)
- [ ] RIPE Atlas credit budget — measurements cost credits, unlike Globalping
- [ ] Compose with the existing `protocol-mcp` / BGP daemon so hijack triage is possible:
      *"this prefix appeared from an unexpected origin — is the ROA valid, who owns it,
      who do I contact"*
- [ ] Skills: prefix ownership, ROV/RPKI check, peering research, hijack triage, abuse contact

---

# Tier 3 — Monitoring and traffic layers

## R10 — ntopng

**Status:** `NOT STARTED`

Official ntop MCP server (documented in ntopng 6.7). Queries ClickHouse flow history, live host
stats, alerts. NetClaw has its own `ipfix-mcp` receiver plus kubeshark/packet-buddy, but no real
flow-analytics platform.

**Checklist**
- [ ] Stand up ntopng (or point at an existing instance) with ClickHouse flow storage
- [ ] Adopt the official MCP server
- [ ] Define the boundary against `ipfix-mcp` — receiver vs analytics platform
- [ ] Skills: top talkers, flow investigation, alert triage, host behavior baseline
- [ ] Note the ClickHouse dependency ties into R17

## R11 — SNMP-poller NMS (Zabbix / LibreNMS / Netdata)

**Status:** `NOT STARTED`

Prometheus, Grafana, Datadog, Splunk, Auvik, ThousandEyes are covered. There is **no
SNMP-poller NMS at all** — and Zabbix/LibreNMS are what a large share of enterprises run.

**Checklist**
- [ ] Pick target(s). Suggested order: Zabbix (largest install base), then LibreNMS
- [ ] Netdata offers an official Cloud MCP — assess as the low-effort entry point
- [ ] Observium: assess, likely `DEFERRED`
- [ ] Skills: interface utilization history, threshold/alert review, device availability

## R12 — APM + log platforms (Dynatrace / New Relic / Elastic)

**Status:** `NOT STARTED`

Both APM vendors appear on Itential's 56-server list; NetClaw has neither. Elasticsearch is
absent and is extremely common for netops logging.

**Checklist**
- [ ] Assess Dynatrace and New Relic official MCP availability
- [ ] Elastic/Elasticsearch MCP — likely higher practical value than either APM for netops
- [ ] Define the boundary against existing Splunk / Datadog / Grafana skills so the agent
      picks the right backend rather than guessing

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

**Status:** `NOT STARTED`

`kubeshark` gives traffic visibility but NetClaw cannot read a pod, service, ingress, or
NetworkPolicy. Hard floor for any container-networking work.

**Candidates**
- `Flux159/mcp-server-kubernetes` — includes Helm operations and write tools
  (`kubectl_apply`, `kubectl_scale`, `kubectl_patch`, `kubectl_rollout`)
- `rohitg00/kubectl-mcp-server` — in the CNCF Landscape
- Red Hat's Kubernetes/OpenShift MCP server

**Checklist**
- [ ] Pick a server; strongly prefer starting read-only given the write tool surface
- [ ] kubeconfig / context handling and RBAC scoping
- [ ] Skills: NetworkPolicy review, service/ingress path tracing, CNI health
- [ ] Compose with `kubeshark` so config and traffic views join up
- [ ] Assess Cilium/Calico CNI-specific tooling as a follow-on

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

**Status:** `NOT STARTED`

SuzieQ, ntopng, Arkime, and NetBox all sit on databases worth querying directly. DuckDB over
files is an excellent analysis substrate for exports.

**Checklist**
- [ ] Decide scope: read-only analyst access, not a general write surface
- [ ] Prioritize DuckDB (file/export analysis) and ClickHouse (ntopng, R10) over generic Postgres
- [ ] Strict read-only enforcement and query timeouts
- [ ] **Must not** expose `~/.openclaw/memory/` or `~/.openclaw/rag/rag.db` — feature 062
      FR-030 keeps those isolated
- [ ] Skill: ad-hoc analysis over exported network data

---

# Tier 5 — Productivity and human deliverables

## R18 — Document generation (docx / pptx / xlsx / pdf)

**Status:** `NOT STARTED` · **Best effort-to-value ratio on the roadmap**

NetClaw can render Three.js topologies, drawio, markmap, UML, Blender and UE5 — but cannot
produce a change-record `.docx`, an exec `.pptx`, an interface-audit `.xlsx`, or fill a PDF.
Its output lands in front of enterprise humans.

**Source:** `anthropics/skills` — `skills/docx`, `skills/pptx`, `skills/xlsx`, `skills/pdf`,
official and source-available.

**Checklist**
- [ ] Vendor the four official skills; note their license terms
- [ ] Confirm Python deps (`python-docx`, `openpyxl`, `python-pptx`, PDF tooling) — several are
      already present for `rag-mcp` (feature 062)
- [ ] Define the output location convention (persistent workspace output dir, timestamped,
      never overwritten — matching feature 046)
- [ ] NetClaw-specific wrapper skills: change record, incident report, interface/config audit
      workbook, exec summary deck
- [ ] Compose with existing report-delivery skills (`slack-report-delivery`,
      `webex-report-delivery`) so generated documents can actually be sent

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

**Status:** `NOT STARTED` · **Strategic, not tooling**

MCP has arrived at the IETF: 15+ active Internet-Drafts as of April 2026, from Cisco, Google,
Huawei, Deutsche Telekom, Orange, Telefónica, and independents. No working group has adopted
any of them and no MCP WG exists yet.

Directly in NetClaw's lane:

| Draft | Relevance |
|---|---|
| `draft-zw-opsawg-mcp-network-mgmt` | "MCP Extensions for Network Equipment Management" |
| `draft-yang-nmrg-mcp-nm` | "Applicability of MCP to Network Management" |
| `draft-serra-mcp-discovery-uri` | `mcp` URI scheme + `/.well-known/mcp-server` discovery |
| `draft-morrison-mcp-dns-discovery` | MCP server discovery via DNS TXT records |

`draft-capobianco-ncfed-00` is already in flight. The discovery drafts in particular overlap the
federation/enrollment problem NCFED solved differently — worth reconciling before `-01`.

**Checklist**
- [ ] Read all four drafts in full
- [ ] Write a positioning note: where NCFED agrees with, diverges from, or could cite each
- [ ] Decide whether NCFED `-01` should reference the discovery drafts, and whether NetClaw's
      TOFU-pinned enrollment is worth contributing back as an alternative
- [ ] Check opsawg / nmrg mailing list activity for adoption signals
- [ ] Feed conclusions into the existing NCFED `-01` backlog

---

# R24 — Open-territory triage

**Status:** `NOT STARTED`

No mature MCP found for any of these. Flag-planting opportunities rather than gaps — assess
strategic value before scheduling any of them as their own spec.

**Networking platforms**
Nokia SR Linux / SR OS · SONiC · VyOS · Arista ANTA (notable, given CVP is covered) ·
netlab · Oxidized / Netpicker (config backup & compliance) · gNOI (gNMI is covered; the
operations half is not)

> Most of these are practically answered by **R1** (Nornir/Netmiko). Do R1 first, then
> re-assess which still justify a dedicated server.

**Service provider / optical / mobile**
Ciena · Infinera · Nokia NSP · Open5GS · free5GC

**SASE / cloud networking / NaaS**
Netskope · Cato · Versa · Aviatrix · Alkira · **Megaport/NaaS** (genuinely unclaimed and
strategically interesting)

**Wireless design**
Ekahau · Hamina

**Exist but NetClaw lacks (adopt, don't build)**
- MikroTik RouterOS MCP (API + SSH)
- UniFi MCP (community, on the official UniFi API)

**Checklist**
- [ ] After R1 lands, re-test which platforms remain genuinely unreachable
- [ ] Pick at most one or two flag-planting targets; Megaport/NaaS and Arista ANTA are the
      strongest candidates
- [ ] Everything else: record as `DEFERRED` with a reason so it isn't re-litigated

---

# Recommended execution order

R0 is mandatory and first. After that, the value-ordered sequence:

1. **R0** — config reconciliation *(foundation; blocks all)*
2. **R1** — Nornir/Netmiko *(~100 platforms, one server)*
3. **R18** — document generation *(free, official, closes the deliverable gap)*
4. **R8** — Globalping *(remote MCP, zero install, opens the external plane)*
5. **R2** — Cisco Support APIs *(closes PSIRT/EoL/bug in the deepest vendor)*
6. **R3** — Fortinet *(largest single-vendor absence)*

Next wave: **R14** Kubernetes · **R5** Mist · **R6** Aruba Central · **R10** ntopng ·
**R15** Redfish.

Then: R4, R7, R9, R11, R17, R19, R21, and R23 in parallel with tooling work.

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
