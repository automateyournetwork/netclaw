# redfish-mcp — out-of-band hardware visibility (read-only)

Roadmap **R15**, spec [094](../../specs/094-redfish-bmc/spec.md). NetClaw-authored.

| | |
|---|---|
| Tools | **6** — `redfish_status`, `redfish_systems`, `redfish_thermal_power`, `redfish_managers`, `redfish_firmware`, `redfish_logs` |
| Manifest | **~728 tokens** of 5,000 |
| Works with | iDRAC, iLO, XClarity, Supermicro — anything implementing DMTF Redfish |
| Verified against | DMTF Redfish mockup server (1.15.0), no hardware required |

## The distinction it exists for

**"Is the box dead, or is it the network?"** A BMC answers when the OS cannot. But the trap is
symmetric:

| Reading | Establishes | Never report as |
|---|---|---|
| BMC **unreachable** | **nothing about the host** | "the host is down" |
| reachable, `Off` | the host **is** off — a fact | — |
| reachable, `On` | the host has **power** | "healthy" / "the OS is up" |
| reachable, health bad | a **hardware** fault | anything about the OS |

A BMC has its own NIC, path and credentials. **A BMC timeout is a statement about the BMC path.**
So the verdict is mandatory: `host_verdict()` raises if asked to derive a host state from an
unreachable BMC, and `emit()` raises on a host claim with no verdict. There is no path that
returns a reading without its qualifier.

**HTTP 401/403 means the BMC is alive** — a credential problem, not a dead box. Reported as such
rather than collapsed into "unreachable".

## Read-only at the transport

`client.py` implements `get()` and nothing else. Redfish exposes `#ComputerSystem.Reset` as a POST
on every system; a power cycle on the wrong box is an outage, so there is no code path here that
can issue one. A reset is an operator action through the BMC UI under change control.

## Empty is never good news

An empty SEL (ring buffers are cleared during service), an empty firmware inventory (many BMCs
don't populate it), and an absent Thermal/Power subresource (vendors implement different subsets)
are each reported as coverage gaps in `gaps`, never as "no problem found".

## TLS

Verification defaults **off** because BMCs ship self-signed certificates, and every response says
so. Set `REDFISH_VERIFY_TLS=true` where the BMC has a real certificate.

## Environment

`REDFISH_URL` (never guessed), `REDFISH_USERNAME`, `REDFISH_PASSWORD`, `REDFISH_VERIFY_TLS`,
`REDFISH_TIMEOUT`. **BMC credentials are root-equivalent on the host** — use Vault where available.

## Tests

`bash tests/redfish/run-tests.sh` — 15 assertions. Verdict and read-only assertions are pure
stdlib; the live mockup ones skip without `httpx` and the container.
