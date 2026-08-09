# Phase 0 Research — Open-territory triage (R24)

**Date**: 2026-08-05 | **Plan**: [plan.md](plan.md) | **Deliverable**: [TRIAGE.md](TRIAGE.md)

Establishes what NetClaw already reaches, so the 22 candidates can be assessed against fact rather
than against the assumptions in place when R24 was written (2026-07-30).

---

## R1 — What does the multivendor CLI driver actually reach?

**Decision**: It covers eight of R24's candidates **by claim**, and **two by verification**.

Spec 076's own text names *"MikroTik RouterOS, VyOS, SONiC, Nokia SR Linux, Extreme, Huawei, Dell
OS10 and Ubiquiti EdgeOS and roughly ninety more"*. But its success criteria were **amended during
the feature**, and it says why:

> **≥2 families verified live, drawn from different CLI paradigms** … *"Reaching five live-verified
> families requires container images that are not freely obtainable: only Nokia SR Linux is fully
> public, and Arista cEOS, SONiC, VyOS and Cumulus each need an account, an artifact download, or a
> build."*

**Verified live: Nokia SR Linux** (native NOS CLI, `nokia_srl` driver) **and FRR** (shell). The
other six are claimed on the strength of the driver's platform table.

**Consequence for this triage**: `COVERED` must be split at the evidence line. A `COVERED (claimed)`
disposition still means "do not build a dedicated server", but a reader can see what it rests on.
Spec 076 also records fixing a `nokia_srl`/`nokia_srlinux` **platform-key mismatch that had left SR
Linux unreachable** — direct evidence that a platform appearing in a driver table is not the same as
a platform being reachable.

---

## R2 — What is already registered that bears on the list?

Of 102 registered servers, two touch R24 candidates directly:

| Server | Bears on |
|---|---|
| `arista-cvp-mcp` | Arista CloudVision — the *management* plane, not the test plane |
| `gnmi-mcp` | gNMI streaming telemetry — the *telemetry* half of the gNMI/gNOI pair |

Also relevant: `nautobot-golden-config-mcp` (config backup and compliance, bearing on
Oxidized/Netpicker), and the lab tooling `clab-mcp-server`, `gns3-mcp-server`, `eve-ng-mcp-server`
plus CML (bearing on netlab).

---

## R3 — Megaport: the list is out of date

**Finding**: **Megaport shipped an official MCP server** after R24 was written. R24 calls it
"genuinely unclaimed and strategically interesting"; that is no longer true.

| Property | Value |
|---|---|
| Status | **open beta** |
| Posture | **read-only** during beta — provisioning not exposed |
| Capability | service status and utilisation, latency diagnosis, Looking Glass, port/VXC metrics |
| Interface | a general natural-language query surface rather than discrete per-operation tools |
| Testing | a **staging environment** exists and is documented for testing configurations |

**This changes its category** — from build-candidate to adopt-candidate — and the manifest ceiling
would then decide, exactly as it did for R12 (adopt at 1,094) and R5 (reject at 11,783).

**What it does not change**: it still needs a Megaport account. The staging environment is
documented but account provisioning was not confirmed, and this environment has no Megaport account.
By the verifiability-first rule that is `DEFERRED` with a named condition, not `SELECTED`.

---

## R4 — Arista ANTA: a capability nothing here has

**Finding**: **No ANTA MCP server exists.** Searching the ecosystem surfaces CloudVision MCPs
(management plane, already covered by `arista-cvp-mcp`) and an Arista documentation RAG server —
neither is ANTA.

ANTA (Arista Network Test Automation) is a **declarative test framework**: a catalogue of pre-built
network-state tests producing structured pass/fail results.

**What makes it distinct from everything NetClaw has:**

| NetClaw today | Answers |
|---|---|
| pyATS, R1's CLI driver, `gnmi-mcp` | *what is the state* |
| `arista-cvp-mcp` | *what does the manager say* |
| `suzieq-mcp`, `zabbix-mcp` | *what was the state over time* |
| **nothing** | ***does the state match what it should be*** — structured, repeatable, pass/fail |

That last row is the gap. NetClaw can read state and can describe it, but has no assertion layer
that returns a verdict.

**Verifiability with access on hand**: an Arista vEOS image is present in this environment
(`~/clab-images/vrnetlab_arista_veos_4.36.1F.tgz`), containerlab is installed and registered, and
ANTA is a pip-installable Python framework speaking eAPI/SSH. **This is the only candidate whose
verification path is entirely satisfied by what is already on disk.**

---

## R5 — gNOI: a real gap, with a posture problem

**Finding**: `gnmi-mcp` covers telemetry; **the operations half is absent**, as R24 says.

gNOI's RPCs are dominated by **write and lifecycle operations** — `System.Reboot`,
`System.SetPackage`, certificate installation, file transfer — which sit against NetClaw's
read-first posture and would require ITSM gating under Principle III. Its read-shaped RPCs
(`System.Ping`, `System.Traceroute`, `Healthz`) are a thin subset, and much of what they return is
already reachable through R1's CLI driver or pyATS.

Verifiable in principle (SR Linux supports gNOI and is the one fully public image), but the value is
concentrated in exactly the operations NetClaw deliberately does not perform.

---

## R6 — The rest, by category

- **Networking platforms** — SR Linux, SR OS, SONiC, VyOS are R1's territory; netlab overlaps four
  registered lab controllers (clab, GNS3, EVE-NG, CML); Oxidized/Netpicker overlaps
  `nautobot-golden-config-mcp`.
- **Service provider / optical / mobile** — Ciena, Infinera and Nokia NSP need vendor equipment or a
  vendor NMS licence; no path from this environment. Open5GS and free5GC are self-hostable but are a
  mobile-core discipline, not network operations.
- **SASE / cloud** — Netskope, Cato, Versa, Aviatrix, Alkira are all tenant-gated. This is the R5
  and R12 pattern precisely: valuable, unverifiable here.
- **Wireless design** — Ekahau and Hamina are desktop survey and design tools whose value is human
  RF planning; neither presents an operational API surface worth an agent.
- **Adopt-don't-build** — MikroTik RouterOS and UniFi were listed as "exist but NetClaw lacks".
  R1 now reaches MikroTik's CLI, which changes the question. UniFi's controller API is a genuinely
  separate surface from EdgeOS's CLI and remains uncovered.

---

## R7 — What the evidence base is, stated honestly

Per the 2026-08-05 clarification, **no environment was stood up for this triage.**

- **Measured** (from repository state): R1's claimed vs verified platforms, the registered server
  inventory, vendored servers, available lab images.
- **Desk research** (named sources, not measured): Megaport's MCP status and posture, the absence of
  an ANTA MCP, the SASE and optical vendors' access models.

No disposition in `TRIAGE.md` claims a measurement that was not made.
