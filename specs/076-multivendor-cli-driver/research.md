# Phase 0 Research: Generic Multivendor CLI Driver

**Feature**: 076-multivendor-cli-driver
**Date**: 2026-07-30
**Purpose**: Resolve unknowns before design. The headline finding overturns a spec assumption.

---

## R1 — Neither candidate is adoptable as-is. The spec's "adopt, don't build" assumption fails

The spec assumed "a community server will be adopted rather than written from scratch." Both
candidates were assessed against the spec's own hard requirements. **Both fail, and for overlapping
reasons.**

### Candidate A — `sydasif/nornir-mcp-server`

| Property | Finding | Verdict |
|---|---|---|
| License | MIT | OK |
| Stars / activity | 2 stars, **archived (read-only) 4 June 2026** | **Unmaintained** |
| Python | 3.12+ | Constraint to note |
| Tools | 5: `list_devices`, `fetch_data` (NAPALM getters), `show_commands`, `apply_config`, `backup_configs` | Thin but well-chosen |
| Command filtering | Allowlist (`show`, `display`, `get`), denylist on destructive first tokens, **blocks chaining via `;`, `&&`, `>`, `<`** | **Excellent** |
| Input validation | Pydantic throughout | **Good** |
| Path sandboxing | Backups restricted to a root directory, traversal prevented | **Good** |
| Inventory | Nornir `SimpleInventory`: local `hosts.yaml`, `groups.yaml`, `defaults.yaml`; reloads `config.yaml` from cwd per call | **Violates FR-017** |
| Credentials | Stored in group definitions in YAML | **Violates FR-019** |

### Candidate B — `ntunes/netmiko-mcp-server`

| Property | Finding | Verdict |
|---|---|---|
| License | MIT | OK |
| Stars / activity | 3 stars, **5 total commits** | **Immature** |
| Tools | 12, incl. `send_command_parallel`, `send_config_parallel`, `list_groups`, `get_pool_status`, `test_connection` | Good concurrency surface |
| Command filtering | **Not present** | **Violates FR-023, FR-029** |
| Read-only mode | **Not present** | **Violates FR-022** |
| Credentials | Env vars plus YAML credential profiles | Partially violates FR-019 |
| Inventory | `config/devices.yaml` with groups and tags | **Violates FR-017** |

### The shared pattern — and a correction to how this was first assessed

> **Corrected 2026-07-30 after clarification.** This section originally called "a local YAML inventory
> with credentials in it" a single disqualifying pattern. That conflated two separable things and
> overstated the case. The spec's Clarifications section is authoritative; this is kept for the record.

Both projects are built around a local YAML inventory that also holds credentials. Split properly:

- **The YAML inventory is not disqualifying.** It is NetClaw's established pattern — `pyATS` ships
  `PYATS_TESTBED_PATH` for an operator-built `testbed.yaml`. Hostnames, addresses and platform
  identifiers are not secret. The clarified spec accepts three inventory sources, two of which are
  files (FR-017).
- **Credentials in the YAML are disqualifying**, and that is what both candidates actually do wrong —
  candidate A in Nornir group definitions, candidate B in YAML credential profiles. Forbidden by
  FR-019 and Principle XIII regardless of which inventory source is in use.

The build-rather-than-adopt conclusion is unchanged, but rests on narrower and more defensible
grounds: candidate A is **archived and unmaintained** and reloads `config.yaml` from the working
directory on every tool call, threading the inventory assumption through the request path; candidate B
has **no command filtering whatsoever**, which is the hardest part to get right and the part
Principle I most depends on.

### Decision: build on the libraries directly, using Candidate A as the safety reference

**Not** "adopt", **not** "write blind". Specifically:

1. Build directly on `nornir` + `napalm` + `netmiko` — the libraries, not either wrapper.
2. **Port Candidate A's safety model deliberately**, because it is genuinely good and is the part
   most easily got wrong: prefix allowlist, destructive-first-token denylist, **chaining prevention
   (`;`, `&&`, `>`, `<`)**, Pydantic validation, path sandboxing. MIT licence permits this; archived
   status means there is no upstream to track or contribute back to.
3. Replace the inventory layer with a Nornir inventory backed by NetClaw's existing sources of truth,
   and the credential layer with Vault lookups.
4. Take Candidate B's concurrency surface as a design reference (`*_parallel`, `get_pool_status`,
   `test_connection`) without taking its code.

**Rationale**: the two candidates offer, between them, roughly the safety model plus a concurrency
shape — perhaps 300 lines of genuinely valuable design thinking. Everything else they provide is the
inventory/credential layer that must be discarded. Adopting either would mean carrying an
unmaintained dependency *and* rewriting its core abstraction; forking an archived 2-star repository is
functionally the same as building, minus the freedom to structure it for NetClaw's needs.

**Alternatives rejected**:
- *Adopt Candidate A and swap the inventory* — a plugin swap sounds cheap, but every tool reloads
  `config.yaml` from cwd, so the inventory assumption is threaded through the request path. Also
  inherits an archived Python-3.12+ dependency.
- *Adopt Candidate B and add filtering* — writing the safety layer is the hard part; B contributes
  nothing to it, so this is building with extra steps plus a foreign inventory model.
- *Scrapli instead of Netmiko* — **this framing was superseded by R8.** NAPALM 5.x is scrapli-based, so
  scrapli arrives regardless; the decision is not either/or. Netmiko is retained for raw-CLI platform
  reach (FR-001), scrapli comes in under NAPALM's getters.

**Consequence for the spec**: the "adopt a community server" assumption is void. Effort increases
from integration to implementation. This is a **material scope change and needs the maintainer's
acknowledgement before implementation proceeds.**

---

## R2 — Dependency footprint is the real Principle XV risk

None of `napalm`, `netmiko`, `nornir`, `scrapli` is currently installed. Unlike R0, which added zero
dependencies, this feature pulls a substantial transitive tree — `paramiko`/`cryptography` (SSH),
`ncclient`/`lxml` (NAPALM's NETCONF drivers), `ruamel.yaml`, `pydantic`, and per-vendor driver
packages.

**Risk**: `cryptography` and `paramiko` are shared with NetClaw's existing federation/TLS stack (spec
060 uses `cryptography` for X.509 issuance). A version conflict here would not break this feature — it
would break NCFED certificate handling. Constitution Principle XV requires new dependencies not
conflict with existing ones.

**Decision**: isolate this server's dependencies rather than installing into the shared system
environment, and pin explicitly. Verify the installed `cryptography` version is unchanged after
install, since the federation stack depends on it.

**Open item — RESOLVED by R10**: `mcp-servers/mcp-nvd/.venv` establishes the per-server venv
precedent, so FR-030a follows existing practice.

**Superseded in part by R7**: this item's risk assessment was later measured, and the measurement
initially *understated* the problem. The host has a split toolchain (`pip3` → Python 3.13,
`python3` → 3.14.4) carrying two different `cryptography` versions. Read R7 before acting on this
section.

---

## R3 — Platform coverage claim, verified

Netmiko's supported-platforms list confirms the spec's reach claim. Platforms NetClaw cannot touch
today that Netmiko drives: MikroTik RouterOS and SwitchOS, VyOS, Nokia SR Linux and SR OS, Dell SONiC
(and Dell OS6/OS9/OS10), Extreme (EXOS/VSP/SLX), Huawei (VRP/SmartAX), Ubiquiti EdgeOS/Unifi,
Alcatel, Arista EOS, Check Point GAiA, F5 TMSH, Fortinet, Palo Alto PAN-OS, and more.

**Note worth flagging**: Netmiko also drives Fortinet, Palo Alto and Check Point — all of which are
separate roadmap items (R3, R4, and an existing Check Point integration). This server therefore
provides a *CLI-level* fallback for those vendors even before their dedicated API-level servers land.
That is a genuine bonus, but it must not be mistaken for completing R3/R4: CLI access is not
equivalent to FortiManager's policy-package API or Panorama's device-group model.

**Decision**: document this explicitly in the routing skill so the agent does not treat CLI reach as
"Fortinet support" and skip R3.

---

## R4 — SC-001 is testable without hardware, but not for every platform

NetClaw already integrates containerlab, GNS3 and EVE-NG. Containerlab natively runs Nokia SR Linux,
SONiC, VyOS, Arista cEOS and FRR as containers — comfortably satisfying SC-001's "five platform
families NetClaw cannot reach today" with no hardware and no licences.

MikroTik RouterOS, Extreme and Huawei need VM images (GNS3/EVE-NG) with licensing NetClaw's lab
tooling cannot assume.

**Decision**: target containerlab-hosted platforms for acceptance testing — SR Linux, SONiC, VyOS —
plus any two more available. Do not gate SC-001 on platforms requiring licensed images.

---

## R5 — The normalized-fact set is bounded by NAPALM, not by ambition

FR-006 requires normalized facts in one shape across platforms. In practice this is exactly NAPALM's
getter set (`get_facts`, `get_interfaces`, `get_interfaces_ip`, `get_bgp_neighbors`, `get_lldp_neighbors`,
`get_arp_table`, `get_environment`, …), and getter support is **uneven across drivers** — a driver may
implement `get_facts` but not `get_bgp_neighbors`.

**Decision**: enumerate supported getters per platform at runtime and report unavailability
explicitly, which is precisely what FR-007 demands. Do not emulate a missing getter by scraping CLI
output — that would silently produce a normalized-looking answer of lower reliability, the exact
failure mode FR-007 exists to prevent.

---

## R6 — Command filtering must be per-platform, and this is the subtle part

The Constitution forbids `write erase`, `reload`, `format flash:` — all **Cisco** syntax. The
equivalents differ: VyOS `delete`/`commit`, MikroTik `/system reset-configuration`, SR Linux
`tools system configuration`, Junos `request system zeroize`, SONiC `config erase`.

A Cisco-shaped denylist is therefore not sufficient (FR-023 says so explicitly). Candidate A's design
insight — deny on **destructive first tokens** plus block **chaining metacharacters** — generalises
far better than pattern-matching full command strings, because chaining is how a denylist gets
bypassed regardless of vendor.

**Decision**: implement per-platform denylists keyed by platform family, layered on top of a
universal chaining prohibition and a universal read-only prefix allowlist. Enforce server-side
(FR-029), never in skill prose.

---

## Summary: what changed versus the spec

| Spec assumption | Research finding | Impact |
|---|---|---|
| A community server will be adopted | A is **archived** and threads its inventory assumption through the request path; B has **no command filtering at all**. Both store credentials in YAML (FR-019). Their *YAML inventory* is fine — see the correction in R1 | **Build on libraries, port A's safety model. Scope increases.** |
| Dependency isolation "needs attention" | `cryptography`/`paramiko` are shared with the NCFED TLS stack | Isolation is a hard requirement, not a nicety |
| Reach claim ~90 platforms | Confirmed, and includes Fortinet/PAN-OS/Check Point | Bonus reach — must not be mistaken for R3/R4 completion |
| Lab platforms available | True for SR Linux/SONiC/VyOS; MikroTik/Extreme/Huawei need licensed images | SC-001 targets containerlab platforms |
| Normalized facts across platforms | Bounded by uneven NAPALM getter support | FR-007's explicit-gap reporting is essential, not optional |

---

## R7 — CRITICAL: the host toolchain is split, and it invalidated an earlier finding

Measured 2026-07-30:

```
python3  -> /usr/bin/python3              Python 3.14.4   cryptography 46.0.5   netmiko absent
pip3     -> ~/.local/bin/pip3  (py 3.13)                  cryptography 45.0.2   netmiko 4.6.0
```

`pip3` installs into a **stranded Python 3.13 `site-packages`** that `/usr/bin/python3` (3.14.4)
cannot import. Two different `cryptography` versions are present, in two environments.

**This invalidated a conclusion drawn earlier in this research.** A `pip install --dry-run` of the R1
tree reported that `cryptography`, `paramiko` and `netmiko` were "not pulled", which was read as
evidence that the NCFED conflict risk was low. That reading was unsound: pip was resolving against
the 3.13 environment, where those packages are *already installed*, so they were omitted as
already-satisfied. **The conflict question is unmeasured, not resolved.**

Corroborating detail: `nornir-netmiko 1.0.1` declares `netmiko (>=4.0.0,<5.0.0)`, so netmiko is
unambiguously a real dependency — it only appeared absent because of the environment mismatch.

### Consequences

1. **FR-030a (dedicated virtualenv) is vindicated and now load-bearing.** With a split toolchain, any
   install that relies on bare `pip3` lands in an environment the server will not run under.
2. **The venv MUST be created from an explicitly chosen interpreter** and populated with that
   interpreter's own `-m pip`, never bare `pip3`. `python3 -m venv` + `<venv>/bin/python -m pip` is the
   only form that is self-consistent here.
3. **The FR-030c check must compare the right environment.** Asserting "system `cryptography` unchanged"
   is only meaningful against the interpreter NetClaw's servers actually run under (`/usr/bin/python3`,
   3.14.4), not whatever `pip3` points at.
4. **This is a repo-wide hazard, not an R1 one.** `scripts/lib/install-steps.sh` contains 186
   `pip install` invocations. If any run as bare `pip3` on a host with this split, they install where
   the servers cannot see them. Out of scope for R1, but it should be raised as its own finding — it is
   the same class of defect spec 075 found in hardcoded interpreter paths.

**Decision**: create the venv with `/usr/bin/python3 -m venv`, install with `<venv>/bin/python -m pip`,
record the resolved interpreter path at install time (FR-030b), and run the FR-030c `cryptography`
assertion against `/usr/bin/python3`.

---

## R8 — NAPALM 5.2.0 is scrapli-based, which changes the transport calculus

The resolved tree for `nornir napalm netmiko nornir-netbox nornir-nautobot nornir-utils` is 21
packages and includes:

```
napalm 5.2.0    nornir 3.5.0        nornir-netmiko 1.0.1   nornir_napalm 0.5.0
scrapli 2026.2.20    scrapli_cfg    scrapli_community      scrapli_netconf
nornir_scrapli  pyeapi 1.0.4   pynautobot 3.1.1   nornir-netbox 0.3.0
jdiff 1.0.2     deepdiff 8.6.2      ttp / ttp_templates    httpx 0.27.0
```

Research R1 rejected scrapli on the grounds of narrower platform coverage. That framing was wrong:
**scrapli arrives regardless**, because NAPALM 5.x uses it. The real position is that both transports
are present — scrapli underneath NAPALM's normalized getters, netmiko for broad-platform raw CLI.

**Decision**: keep netmiko as the raw-CLI transport for platform reach (FR-001 depends on its ~100
platforms) and let NAPALM use scrapli internally for normalized getters. Do not attempt to force NAPALM
onto netmiko, and do not drop netmiko in favour of scrapli.

**Rationale**: this is the layering the spec already ratified — NAPALM for normalized cross-vendor
facts, netmiko for reach. The dependency tree happens to match it.

---

## R9 — Two unplanned-for packages are directly useful

- **`jdiff 1.0.2`** — structured diffing of network state. Lands squarely on FR-026 (compare actual
  post-change state against expected, not merely that the command succeeded). Worth using rather than
  hand-rolling comparison logic.
- **`ttp` / `ttp_templates`** — template-based parsing for platforms with no NAPALM getter. Relevant to
  FR-007, but must be used carefully: FR-007 requires reporting a normalization *gap* explicitly rather
  than emulating a getter by scraping CLI output. TTP output must therefore be labelled as
  template-parsed, never presented as a normalized fact.

**Decision**: adopt `jdiff` for change verification. Treat `ttp` as available but explicitly
second-class, and never let its output masquerade as a NAPALM normalized fact.

---

## R10 — Per-server virtualenv already has precedent

R2 left open whether NetClaw uses per-server venvs or a shared environment. Answer: **both, and
inconsistently.** `mcp-servers/mcp-nvd/.venv` exists, so the pattern is established; most other
servers pip-install into the shared environment.

**Decision**: follow the `mcp-nvd` precedent. FR-030a is consistent with existing practice rather than
novel, which lowers the review burden.

---

## R11 — Deferred non-functional values, now resolved

- **Concurrency bound (FR-015)**: default to **10** concurrent workers, operator-overridable. Nornir's
  own default `num_workers` is 20; 10 is chosen because each worker holds an SSH session and network
  devices commonly cap concurrent management sessions (frequently 5–15). Starting conservative and
  documenting the override is safer than discovering a device's session limit under load.
- **Per-device timeout (FR-016)**: default **30 seconds** for connect-and-execute, operator-overridable.
  Netmiko's default read timeout is 10s, which is too aggressive for slow `show` output on loaded
  devices; 30s bounds a hung device without prematurely failing legitimate slow commands.

Both are defaults with overrides, so neither becomes a hidden constraint.

---

## R12 — Python 3.14 has no `ensurepip` on this host; `python3 -m venv` fails

Discovered executing T005/T008. `/usr/bin/python3 -m venv` fails with:

```
The virtual environment was not created successfully because ensurepip is not
available. On Debian/Ubuntu systems, you need to install the python3-venv
package: apt install python3.14-venv
```

Installed venv packages are `python3.10-venv`, `python3.11-venv`, `python3.12-venv` — **not**
`python3.14-venv`, while the system interpreter is 3.14.4. More residue from the same messy upgrade
that produced R7's split toolchain.

**Decision**: create the venv with **`virtualenv -p /usr/bin/python3`**, which bundles pip and does not
need `ensurepip`. Verified: Python 3.14.4, pip 25.1.1, isolated `site-packages`.

**Rationale**: `virtualenv` is already installed and needs no root. `apt install python3.14-venv`
requires sudo and cannot be assumed on an operator's machine. `uv` is also present and would work, but
`virtualenv` preserves the plan's exact contract of `<venv>/bin/python -m pip`.

**Consequence**: the install function (T058) must use `virtualenv`, not `python3 -m venv`, with a clear
error if `virtualenv` is absent. Recorded in `requirements.txt` and `tests/multivendor/run-tests.sh`.

---

## R13 — T005 confirmed the dependency conflict FR-030c was written for

The tree resolves cleanly on Python 3.14.4 — 68 packages — but wants **`cryptography 49.0.0`** while
the system interpreter carries **46.0.5**.

| Environment | cryptography |
|---|---|
| System `/usr/bin/python3` (NCFED X.509, spec 060) | **46.0.5** — unchanged after install |
| Server venv | **49.0.0** |

Had these been installed into the shared environment, `cryptography` would have moved three major
versions underneath NetClaw's certificate stack. Isolation is therefore not hygiene here; it is the
thing preventing a real regression. Verified post-install: system still 46.0.5, and `nornir`, `napalm`,
`netmiko`, `jdiff` are all absent from the system interpreter.

Also pulled: `netmiko 4.7.0`, `paramiko 4.0.0`, `scrapli 2026.2.20` (transitively via NAPALM 5.x, per
R8), `jdiff 1.0.1`.

---

## R14 — `mcp 2.0.0` removes `mcp.server.fastmcp`; ten NetClaw servers are exposed

An unbounded `mcp>=1.2.0` resolved **2.0.0**, in which `mcp.server.fastmcp` no longer exists (FastMCP
moved to the separate `fastmcp` distribution). That is the import used by
`from mcp.server.fastmcp import FastMCP` — the convention in `suzieq-mcp`, `gnmi-mcp` and others.

**Decision**: pin `mcp>=1.2.0,<2` for this server. Verified working at `mcp 1.29.0`.

**Repo-wide finding, out of scope here but must not be lost**: ten existing servers declare an
unbounded `mcp>=1.0.0`, two declare `mcp>=1.2.0`, one `mcp>=1.13`. **Every one of them resolves mcp 2.x
on a fresh install today and breaks on import.** This is the same shape as R7's `pip3` hazard: existing
servers that work only because their environments predate the breaking change. Should be raised
alongside T083 as its own roadmap item.
