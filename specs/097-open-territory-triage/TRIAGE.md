# R24 Open-Territory Triage — dispositions

**Date**: 2026-08-05 | **Spec**: [spec.md](spec.md) | **Evidence base**: [research.md](research.md)

All 22 candidates from R24's list, each with exactly one disposition and a reason. **No environment
was stood up** for this triage (clarified 2026-08-05); the evidence column says whether each
assessment came from repository state or from named desk research.

## Summary

| Disposition | Count | Which |
|---|---|---|
| `COVERED` | **4** | Nokia SR Linux/SR OS, SONiC, VyOS, MikroTik RouterOS — **all by R1**. One platform (SR Linux) verified live; the rest claimed |
| `SELECTED` | **1** | Arista ANTA |
| `DEFERRED` | **12** | gNOI, Ciena, Infinera, Nokia NSP, Netskope, Cato, Versa, Aviatrix, Alkira, Megaport, Hamina, UniFi |
| `DROPPED` | **5** | netlab, Oxidized/Netpicker, Open5GS, free5GC, Ekahau |
| **Total candidates** | **22** | |

**The single most useful line in this document**: **R1 absorbed four of the 22** without anyone
noticing. R24 was written on 2026-07-30, R1 merged after it, and the list was never re-checked —
which is exactly what its own first checklist item asked for.

**Selected: Arista ANTA.** The only candidate that is both a capability nothing here has and
verifiable with access already on disk.

### 22 candidates, 24 rows — the reconciliation

Two of R24's entries name more than one thing, and the spec's partial-coverage rule requires the
halves be dispositioned separately rather than averaged:

- **"Nokia SR Linux / SR OS"** is one R24 entry covering **two different network operating systems**
  with different verification status — SR Linux was verified live, SR OS was not. Collapsing them
  would attach SR Linux's evidence to SR OS.
- **"UniFi"** is one R24 entry that conflates the **EdgeOS device CLI** (which R1 reaches) with the
  **UniFi controller API** (which nothing reaches). This is the partial-coverage edge case verbatim:
  the covered half and the uncovered half get separate dispositions, and the UniFi row is the
  candidate.

The **Ubiquiti EdgeOS** row is included for that contrast and is **not** counted as one of the 22 —
it is the covered half of R24's "UniFi" entry, whose uncovered half (the controller API) carries the
candidate's `DEFERRED` disposition.

So: **22 candidates, 24 table rows.** SR Linux and SR OS share the single `COVERED` "Nokia SR Linux
/ SR OS" entry; EdgeOS is context for the UniFi entry. The counts above are of candidates, not rows.

---

## Networking platforms

| Candidate | Disposition | Reason | Evidence |
|---|---|---|---|
| **Nokia SR Linux** | `COVERED (verified)` | R1's multivendor CLI driver, `nokia_srl` — one of only two families spec 076 verified live | measured |
| **Nokia SR OS** | `COVERED (claimed)` | R1 driver table; not demonstrated here. Distinct NOS from SR Linux, same driver family | measured |
| **SONiC** | `COVERED (claimed)` | R1 names it explicitly; spec 076 records the image is not freely obtainable, which is why it was not verified | measured |
| **VyOS** | `COVERED (claimed)` | R1 names it explicitly; image needs an account or a build | measured |
| **Arista ANTA** | **`SELECTED`** | **The one capability gap nothing else fills** — see below | desk research + measured |
| **netlab** | `DROPPED` | Lab orchestration, already covered four times over: `clab-mcp-server`, `gns3-mcp-server`, `eve-ng-mcp-server`, CML. Adds a different front-end to a solved problem | measured |
| **Oxidized / Netpicker** | `DROPPED` | Config backup and compliance is `nautobot-golden-config-mcp`'s job, and it is registered. A second backup path would compete with the source of truth rather than extend it | measured |
| **gNOI** | `DEFERRED` | A real gap — `gnmi-mcp` is telemetry only. But gNOI's value is concentrated in `System.Reboot`, `SetPackage`, certificate installation and file transfer: **write and lifecycle operations NetClaw deliberately does not perform**, requiring ITSM gating under Principle III. Its read-shaped RPCs (`Ping`, `Traceroute`, `Healthz`) are largely reachable already via R1 or pyATS | desk research |

**gNOI unblocks when**: NetClaw takes on gated device-lifecycle operations as a deliberate posture
change — not before. This is a decision about what NetClaw is, not a scheduling question.

---

## Service provider / optical / mobile

| Candidate | Disposition | Reason | Evidence |
|---|---|---|---|
| **Ciena** | `DEFERRED` | Requires Ciena equipment or an MCP/Blue Planet instance; neither exists here and neither is obtainable without a customer relationship | desk research |
| **Infinera** | `DEFERRED` | Same shape — vendor optical platform, no access path from this environment | desk research |
| **Nokia NSP** | `DEFERRED` | Requires an NSP licence and deployment; NSP is a full network-management platform, not a callable API surface one can trial | desk research |
| **Open5GS** | `DROPPED` | Self-hostable, so **not** access-blocked — dropped on scope. A 5G mobile core is a different discipline from network operations; NetClaw has no mobile-core skills, no user base for them, and adding one would be a new product area rather than closing a coverage gap | desk research |
| **free5GC** | `DROPPED` | Same reasoning as Open5GS. Recorded separately so neither is mistaken for an oversight | desk research |

**Ciena / Infinera / Nokia NSP unblock when**: a customer or lab deployment becomes reachable with
credentials. All three are Tier B in the roadmap's sense — blocked on access, not on effort.

---

## SASE / cloud networking / NaaS

| Candidate | Disposition | Reason | Evidence |
|---|---|---|---|
| **Megaport / NaaS** | `DEFERRED` | **R24's premise is stale**: it calls Megaport "genuinely unclaimed", but an **official Megaport MCP server now exists** — open beta, read-only, with a documented staging environment. This is no longer a build candidate; it is an adopt candidate whose manifest cost would decide it | desk research |
| **Netskope** | `DEFERRED` | Tenant-gated SASE platform; no tenant here | desk research |
| **Cato** | `DEFERRED` | Tenant-gated; Cato does not offer self-serve evaluation access | desk research |
| **Versa** | `DEFERRED` | Tenant or on-prem Director deployment required | desk research |
| **Aviatrix** | `DEFERRED` | Requires a controller deployed into a cloud account with real VPCs attached | desk research |
| **Alkira** | `DEFERRED` | Tenant-gated cloud networking platform | desk research |

**Megaport unblocks when**: a Megaport account (staging is documented and would suffice) becomes
available. **This is the cheapest condition on the board** — worth revisiting first among the
deferred, since the server already exists and only the credential is missing.

**The five SASE vendors unblock when**: a tenant is obtained. All five are the R5 and R12 pattern
exactly — valuable, and unverifiable from here. **Do not spec any of them before confirming access**;
that is the mistake R5 cost a day to learn.

---

## Wireless design

| Candidate | Disposition | Reason | Evidence |
|---|---|---|---|
| **Ekahau** | `DROPPED` | A desktop RF survey and design suite. Its value is human planning judgement over floor plans and survey data; it exposes no operational API surface an agent would drive. Not a coverage gap | desk research |
| **Hamina** | `DEFERRED` | Cloud-based wireless design with an API, unlike Ekahau — so the capability is at least addressable. But it is design-time tooling, subscription-gated, and adjacent to network *operations* rather than part of it | desk research |

**Hamina unblocks when**: a subscription exists **and** a wireless-design use case is actually asked
for. Both conditions, not either — an unused capability is not worth a manifest slot.

---

## Exist but NetClaw lacks (adopt, don't build)

| Candidate | Disposition | Reason | Evidence |
|---|---|---|---|
| **MikroTik RouterOS** | `COVERED (claimed)` | R1 names MikroTik RouterOS explicitly and reaches it over SSH. R24 listed it as "adopt a dedicated MCP" **before R1 existed**; a dedicated server would now duplicate the generic driver for one vendor | measured |
| **Ubiquiti EdgeOS** | `COVERED (claimed)` | R1 names EdgeOS explicitly. Listed here because R24's "UniFi" entry conflates two different surfaces — see next row | measured |
| **UniFi controller** | `DEFERRED` | **Genuinely uncovered.** The UniFi *controller* API (sites, clients, WLANs, adoption state) is a wholly different surface from EdgeOS's device CLI, and R1 does not touch it. Deferred rather than selected because verification needs a running UniFi controller with adopted devices, which this environment does not have | measured + desk research |

**UniFi unblocks when**: a UniFi controller with at least one adopted device is reachable. The
controller is self-hostable, so this is a **cheap condition** — second only to Megaport among the
deferred items.

---

## The selection: Arista ANTA

**Disposition**: `SELECTED` — the only one.

### What it does that nothing else here does

NetClaw can read state and describe it. It has **no assertion layer** — nothing that takes a
declarative expectation and returns a structured pass/fail verdict.

| Existing capability | Answers |
|---|---|
| pyATS, R1 CLI driver, `gnmi-mcp` | what *is* the state |
| `arista-cvp-mcp` | what does the *manager* say |
| `suzieq-mcp`, `zabbix-mcp` | what *was* the state over time |
| **ANTA** | **does the state match what it *should* be** |

ANTA is a catalogue of pre-built network-state tests producing machine-readable results. That is a
different question from every server above, and it composes with all of them.

### Documented access check (FR-006)

| Requirement | Status |
|---|---|
| Test target | **Arista vEOS image present on disk** — `~/clab-images/vrnetlab_arista_veos_4.36.1F.tgz` |
| Runner | containerlab, installed and registered (`clab-mcp-server`) |
| Framework | ANTA is pip-installable Python, speaking eAPI/SSH |
| Credentials | none beyond lab device credentials |
| Vendor account | **none required** |

**This is the only candidate on the list whose verification path is satisfied entirely by what is
already present.** Nothing must be obtained, licensed, or requested.

### Manifest-cost risk

ANTA's test catalogue is large (hundreds of tests). Exposing one tool per test would blow the
5,000-token ceiling the way Catalyst Center's 515 tools did. **The expected shape is a dispatcher
plus discovery** — the 087 pattern — and the manifest must be counted, not estimated, per the R5
lesson. This is the main design risk and belongs in its spec's Phase 0.

### Why only one selection

FR-005 permits two. Nothing else met both bars: every other candidate is either already reachable,
or blocked on access that does not exist here. **Selecting a second to fill the quota would recreate
the unassessed backlog this triage exists to remove.**

Of the deferred items, **Megaport** and **UniFi** have the cheapest unblocking conditions — a free
staging account and a self-hostable controller respectively. Either could become selectable quickly
if the operator wants them.

---

## Notes — territory seen but not assessed

Recorded rather than silently added, per the spec's out-of-scope rule. These are **not** dispositions
and are **not** part of the 22:

- **Arista AVD** (config generation from a data model) surfaced alongside ANTA. Generation rather
  than validation, and it would sit against NetClaw's read-first posture. Not assessed.
- The MCP ecosystem has grown substantially since R24 was written (the Megaport finding is one
  instance). **R24's premise that these are "unclaimed" should not be trusted for any candidate
  without re-checking** — which is precisely what this triage did for the two that mattered.
