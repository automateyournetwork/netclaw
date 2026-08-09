---
name: hardware-health-check
description: "Out-of-band hardware health via Redfish BMC (read-only) — power state, component health, thermal and power readings, firmware inventory, SEL log triage. Use when determining whether a host is powered off versus unreachable, checking hardware faults, reviewing thermal or PSU state, or triaging BMC event logs"
version: 1.0.0
license: Apache-2.0
tags: [hardware, bmc, redfish, idrac, ilo, out-of-band, read-only]
---

# Hardware Health Check (out-of-band, read-only)

## MCP Server

- **Server**: `redfish-mcp` (NetClaw-authored, spec 094)
- **Tools**: `redfish_status`, `redfish_systems`, `redfish_thermal_power`,
  `redfish_managers`, `redfish_firmware`, `redfish_logs`
- **Requires**: `REDFISH_URL`, `REDFISH_USERNAME`, `REDFISH_PASSWORD`
- **Read-only.** No power control exists here — see below.

## The one distinction this skill is for

NetClaw could not previously tell **"the box is dead"** from **"the network to the box is
dead."** A BMC can, because it answers when the operating system cannot. But the distinction is
**symmetric**, and each direction is a different wrong answer:

| Reading | What it establishes | What you must NOT say |
|---|---|---|
| BMC **unreachable** | **nothing about the host** | "the host is down" |
| BMC reachable, `Off` | the host **is** powered off — a fact | — |
| BMC reachable, `On` | the host has **power** | "the host is healthy / the OS is up" |
| BMC reachable, health `Critical` | a **hardware** fault is asserted | anything about the OS |

The BMC has its own NIC, its own network path and its own credentials, all separate from the
host's. **A BMC timeout is a statement about the BMC path, not about the server.** Reporting
"host down" from a BMC timeout is precisely the mistake out-of-band access exists to prevent.

Every response carries a `verdict` saying which of the rows above applies. `redfish-mcp` will
not emit a host claim without one — the tool refuses, so the qualifier cannot be dropped.

**An auth rejection means the BMC is alive.** HTTP 401/403 proves it answered; that is a
credential problem, not a dead box, and the tool says so explicitly.

## Workflow: is the box dead, or is it the network?

1. `redfish_status` — does the BMC answer at all?
2. **If unreachable: stop and report exactly that.** You have learned nothing about the host.
   Say which was tested (the BMC path) and what remains unknown (everything about the host).
3. If reachable: `redfish_systems` — `PowerState` and `Status.Health`
4. Read the `verdict`, and phrase the answer in its terms. `Off` is a conclusion; `On` is not.
5. If `On` but the service is unreachable in band, the finding is **"powered on, not serving"** —
   which points at the OS, the application or the data network, not at the hardware.

## Workflow: hardware fault triage

1. `redfish_systems` — `Status.Health` and the CPU/memory rollups
2. `redfish_thermal_power` — temperatures against their critical thresholds, fan readings, PSU
   health, consumed watts
3. `redfish_logs` — SEL entries by severity, newest first
4. `redfish_firmware` — is this a known-bad firmware level?
5. `redfish_managers` — BMC firmware version, which is a finding in its own right

## Reading results honestly

- **An empty SEL is not a clean bill of health.** SELs are ring buffers cleared during service,
  so no entries means no *recorded* entries. The tool says this in `gaps`.
- **An empty firmware inventory means the BMC does not populate it**, not that the machine has
  no firmware. Several vendors return nothing here.
- **A missing Thermal or Power subresource is a coverage gap, not a pass.** Vendors implement
  different Redfish subsets; the tool marks it `unavailable` rather than reporting no problem.
- **TLS verification is off by default** because BMCs ship self-signed certificates. Every
  response discloses it. On an untrusted network the readings could be forged — say so if it
  matters to the conclusion.
- **Thermal and power are hardware facts** and establish nothing about the OS.

## Important Rules

- **No power control.** No reset, no power on/off, no virtual media. Redfish exposes
  `#ComputerSystem.Reset` and this server deliberately does not implement it — a power cycle on
  the wrong box is an outage. If a reset is genuinely needed, that is an operator action through
  the BMC UI, gated by change control.
- **BMC credentials are root-equivalent on the host.** Store them in Vault where available;
  never echo them into a report or a GAIT entry.
- **Always name which vantage point answered** — "the BMC reports" is not "the host reports".
- **Record in GAIT** — log the endpoint, the verdict, and the reading it came from.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `globalping-probes` | Outside-in reachability — pairs with a BMC verdict to separate host from network |
| `zabbix-nms` / `suzieq-observability` | In-band polling history; a BMC answers when those go silent |
| `pyats-health-check` | In-band device health once the box is known to be powered and booted |
| `servicenow-change-workflow` | Raise the CR if a hardware fault needs an intervention |
| `gait-session-tracking` | Record every health check and its verdict |

## Environment Variables

- `REDFISH_URL` — BMC base URL (e.g. `https://10.0.0.5`). Never guessed.
- `REDFISH_USERNAME` / `REDFISH_PASSWORD` — BMC credentials
- `REDFISH_VERIFY_TLS` — `true` to require a valid certificate (default `false`)
- `REDFISH_TIMEOUT` — per-request seconds (default 15)
