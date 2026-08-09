# Phase 0 Research — Fortinet Coverage (spec 080 / roadmap R3)

**Date**: 2026-08-01 · **Branch**: `080-fortinet-coverage`

All measurements and repository facts below were gathered on 2026-07-31 and 2026-08-01. Where something
was **not** verified, it says so.

**Read R1 and R6 first.** R1 settles build-vs-adopt on four independent grounds. R6 records that the
verification lab is feasible on this host — checked, not assumed.

---

## R1 — Build, adopt, or wrap? → **Build, with all three candidates as reference**

### The candidates, measured

| Repo | Plane | Licence | Stars | Tools | Read-only? | Auth | TLS default |
|---|---|---|---|---|---|---|---|
| `rstierli/fortimanager-mcp` | Manager | MIT | 4 | **106** | ✗ writes fully exposed | Token *or* user/pass | verify **on** |
| `rstierli/fortianalyzer-mcp` | Analyzer | MIT | 12 | **69** | Partial — the 16-tool "skills layer" is read-only; alerts/incidents are writes | Token (7.2.2+) *or* user/pass | verify **on** |
| `paoloamato2/fortinet-mcp-server` | Device | MIT | 11 | **204+ typed, plus 5 generic** | ✗ no mode; defers to FortiGate admin profiles | Bearer token | not stated |
| `ivillagomez/fortigate-mcp` | Device + Analyzer | — | — | — | ✅ **all writes blocked** | — | — |

**A find the roadmap missed**: `rstierli` also publishes **`fortianalyzer-mcp`**, a sibling to the
FortiManager server. The roadmap listed only the latter. Three planes, three candidate servers, one
author for two of them.

### Why not adopt

Four independent disqualifications, any one of which is sufficient:

1. **The `plane` field (FR-005/FR-005a).** No candidate emits one. This was settled in clarification: a
   structural guarantee, not skill prose. Adoption unmodified is already ruled out by the spec.
2. **The token ceiling (FR-026).** 106 + 69 + 204 = **~380 tools**. Any *single* candidate blows the
   5,000-token budget on its own. This is not a tuning problem; it is an order-of-magnitude mismatch.
3. **Read-only default (FR-019).** Only `ivillagomez` enforces it. `rstierli/fortimanager-mcp` exposes
   policy create/delete, script execution and **package install** with no mode gate — the highest
   blast-radius operation in this feature, ungated.
4. **The two gates (FR-020).** None has any concept of a ServiceNow change record. `fortimanager-mcp`
   has *guardrails* — it blocks `factory-reset`/`reboot` inside scripts and refuses overly permissive
   policies — which is thoughtful, but a denylist is not an approval gate.

### What adoption still gives us

All three are MIT. Their value is **endpoint knowledge, not code**: which JSON-RPC methods return what,
which FortiOS REST paths matter, how log pagination behaves. Spec 076 reached the identical conclusion
about `sydasif/nornir-mcp-server` — port the knowledge, build the server.

Two specific designs worth stealing outright:

- **`paoloamato2`'s five generic pass-throughs** (`cmdb_list/get/create/update/delete`, `monitor_get/action`,
  `log_get`, `service_call`) reach **all 1,536 FortiOS endpoints** from a handful of tools. This is the
  existence proof that a small manifest can carry full coverage, and it is the shape FR-026a asks for.
  Its mistake is shipping those *alongside* 204 typed tools rather than instead of them.
- **`rstierli/fortianalyzer-mcp`'s pagination model.** It re-runs the query at a new offset rather than
  consuming FortiAnalyzer's single-use task IDs, returning a reusable handle with `total`/`has_more`/
  `next_offset`. That is a real bug avoided, learned from someone else's implementation.

**Decision: build.** `mcp-servers/fortinet-mcp/`, NetClaw-authored.
**Alternatives rejected**: adopt-unmodified (fails FR-005a, FR-019, FR-020, FR-026); wrap a candidate
(inherits a 106–204 tool manifest we would then have to suppress — more work than building the ~20 tools
we want, and we would own the debugging of someone else's transport anyway).

---

## R2 — FortiManager and FortiAnalyzer share one transport

**Both expose the same `/jsonrpc` endpoint** with the same request envelope and the same
`exec /sys/login/user` authentication. They differ in the *methods* called, not the protocol.

**Consequence, and it is a large one**: two of the three planes are served by **one JSON-RPC client
class**. The manager/analyzer split lives in the tool layer, not the transport layer. This materially
reduces the build — the earlier assumption of three independent integrations was wrong.

FortiAnalyzer log search is **task-based**: issue a search, receive a `tid`, poll for results, delete the
task. Per R1, NetClaw follows `rstierli`'s approach of re-running at an offset rather than treating the
`tid` as a durable cursor.

**Decision**: one `jsonrpc.py` client, two tool modules (`manager.py`, `analyzer.py`) over it.

---

## R3 — FortiOS device plane is plain REST

Bearer-token REST over HTTPS, distinct from the JSON-RPC planes. The permanent free evaluation licence
now permits HTTPS admin access (it was HTTP-only before FortiOS 7.2.1), so the REST API is reachable on
the free tier — a fact the whole lab design depends on.

**Decision**: `rest.py`, an `httpx.AsyncClient` with a bearer token. No third-party FortiOS SDK.

---

## R4 — Dependencies: two, matching spec 078

Surveyed: `pyFMG` (maintained by the Fortinet North America CSE team — the most credible), `pyfortimanager`,
`fortiosapi`, `fortigate-api`, `PyFortiAPI` (unmaintained).

**Decision: none of them.** `httpx` + a ~150-line JSON-RPC client covers everything here. JSON-RPC over
HTTPS is a POST with `method`/`params`/`session` — an SDK adds a dependency, a pinning hazard under spec
077, and an abstraction over a protocol simpler than the abstraction.

```
mcp>=1.2.0,<2      # upper bound LOAD-BEARING — mcp 2.0.0 removed mcp.server.fastmcp
httpx>=0.27.0,<1
```

Identical to `mcp-servers/cisco-psirt-mcp/requirements.txt` (spec 078).

**No dedicated venv.** Spec 076 needed one because its 21-package tree moved `cryptography` three major
versions and would have broken the NCFED X.509 stack. Two pure-HTTP packages carry no such risk, and 078
set the precedent for installing shared.

**Alternatives rejected**: `pyFMG` — credible and semi-official, but pulls a dependency for a trivial
protocol and does not support 2FA; `fortiosapi`/`fortigate-api` — target config *management*, a far wider
surface than a read-first server needs.

---

## R5 — Sizing the tool surface to the 5,000-token ceiling

The ceiling is FR-026, set during clarification. `count_tokens` over the serialised `tools/list` response
is the measurement (FR-025).

No candidate manifest was measured directly — the servers were not installed. What *is* known is the tool
counts (106 / 69 / 204+), and at any plausible per-tool schema cost those are far beyond budget. Precision
is unnecessary to reach the decision.

**Design target: ~20 tools across three planes**, roughly 8 manager / 6 device / 6 analyzer, budgeting
~150–250 tokens per tool including schema. That lands near 3,000–5,000 tokens with headroom.

**The rule adopted**: prefer *parameterised* tools over *enumerated* ones. `fmg_get_policy_package(adom,
package)` rather than a tool per object type. This is `paoloamato2`'s generic-passthrough insight applied
deliberately rather than in addition.

**Open, resolved as a task not an assumption**: the real figure MUST be measured once the surface exists
(T-series task), and re-measured if the surface grows. A design target is not a measurement.

---

## R6 — The verification lab: **Hyper-V for all three; containerlab dropped**

**Superseded 2026-08-01 by a real deployment.** This section originally specified containerlab for the
FortiGate. The operator stood one up on Hyper-V instead, which is strictly better, and containerlab is now
**out of the design entirely**.

### Why containerlab is gone

Verified against the installed binary — containerlab has exactly **one** Fortinet kind:

```
$ containerlab: fortinet kinds
fortinet_fortigate
```

There is no `fortinet_fortimanager` and no `fortinet_fortianalyzer`; both ship only as full appliance VMs.
So containerlab could only ever have hosted one of three planes, and the other two needed Hyper-V
regardless. With the FortiGate on Hyper-V too, the lab is **one hypervisor, three VMs** — fewer moving
parts, and the `srl-labs/vrnetlab` build step disappears.

**This also closes the version fork** that was this section's main open risk. containerlab tested its kind
against **v7.0.14** only, which carries the old 15-day eval; escaping that constraint required a fallback
plan. On Hyper-V there is no such constraint, and the deployed device runs **FortiOS v8.0.0** (build 0167,
GA) — newer than any option containerlab offered.

### The deployed FortiGate, measured 2026-08-01

| Property | Value |
|---|---|
| Version | **FortiOS v8.0.0**, build 0167, GA |
| Model / Serial | `EVAL (1)` / `FGVMEV1DKEYA2Q3E` — `FGVMEV` denotes an evaluation VM |
| Address | `192.168.2.130/24`, reachable from WSL2 at 0.55 ms; 443 and 22 open |
| Certificate | **Self-signed**, `CN=FortiGate`, issued by the unit's own serial-named CA |
| VDOMs | 2 permitted, currently disabled |
| Resources | 1 vCPU / 1 allowed, 2 GB RAM |
| Internet | FortiGuard reachable (`fds1.fortinet.com`, 57 ms); DNS resolves |
| **Licence** | ⚠️ **`Invalid` — not yet activated.** Blocks device-plane *verification* only |

Two findings that change earlier conclusions:

1. **v8.0.0 is newer than every community server targets.** `paoloamato2/fortinet-mcp-server` pins to
   FortiOS **7.6.6**; containerlab tested **7.0.14**. A server built against 7.6.6 schemas and pointed at
   v8.0.0 is precisely the compatibility exposure R1 avoids by building. Their endpoint knowledge remains
   useful but must now be **checked against v8**, not trusted.
2. **The self-signed certificate is real, not hypothetical.** R8's TLS path is exercised by the actual lab
   rather than reasoned about.

### Networking — a trap worth recording

The FortiGate was first deployed on the Hyper-V **Default Switch** (`172.21.224.0/20`) and was
**unreachable from WSL2**: that switch is an internal NAT network reachable only from the Windows host,
while WSL2 (mirrored networking) sits on the external adapter at `192.168.2.61`. All ports appeared closed.

Two reasons the Default Switch is wrong for this lab, and the second is the serious one:

- It is not routable from WSL2, where NetClaw runs.
- **Its subnet re-randomises on host reboot.** A lab pinned to a Default Switch address silently breaks
  later — incompatible with FR-036a's reproducibility requirement.

Resolved by moving the adapter to an **External** vSwitch with a static LAN address. Note also that
FortiGate interfaces drop everything not in `allowaccess`, so `ping`/`https` must be enabled explicitly on
`port1` — a failed ping there proves nothing about reachability.

### Still operator actions, not implementation steps

Image download (`support.fortinet.com`, free account) and licence activation cannot be automated from the
repo, and **no image, licence or credential may be committed** (FR-036a).

**FortiManager-VM and FortiAnalyzer-VM**: same Hyper-V host, both **15-day clocks from first boot**, while
the FortiGate's eval is permanent once activated. Hence the staging rule in the plan. They may be
*downloaded and imported* at any time — **import is not first boot**, and the clock does not start until
power-on.

---

## R7 — The two gates already exist, in spec 076

`mcp-servers/multivendor-cli-mcp/tools/change.py` (399 lines) already implements exactly what FR-020
requires, and its module docstring names the same history:

> *The distinction that took a `/speckit.analyze` finding to surface: **human approval** … "inherited from
> the existing approval path" — an assertion with no implementation.*

Reusable surface: `check_change_request(cr_number)` querying `/api/now/table/change_request`;
`APPROVED_CR_STATES`; a `Stage` enum including `AWAITING_APPROVAL`; `is_lab()` for the CR exemption; an
unconfigured-ServiceNow path that reports *unconfigured* rather than silently approving.

**Decision: port the logic, do not import it.** The two servers are separate processes with separate
dependency sets, and 076's version is bound to its own `inventory.Device` type. Copy with explicit
attribution in the header. Sharing across MCP servers would need a shared package NetClaw does not have —
out of scope here, and worth noting as future work rather than inventing now.

**One inherited rule matters most**: an unclassified device is treated as **production**. Guessing "lab"
wrongly permits an unauthorised production change; guessing "production" wrongly costs one CR.

---

## R8 — TLS against self-signed appliances

Both `rstierli` servers default `VERIFY_SSL=true` and document importing the appliance CA rather than
disabling verification, warning that disabling it exposes the API token to interception. That is the right
posture and NetClaw adopts it.

**Decision**: verification **on** by default; a per-plane opt-out env var that is never the silent default
(FR-030); the lab documents CA import as the recommended path. The lab's appliances are self-signed, so
this code path is exercised rather than theoretical.

---

## R9 — Auth per plane

| Plane | Method | Notes |
|---|---|---|
| Manager | API token preferred, user/pass session fallback | Sessions expire — FR must report expiry as an auth condition, never as "no policies" |
| Analyzer | API token (FortiAnalyzer 7.2.2+), user/pass fallback | Same session semantics |
| Device | Bearer token | Generated per-admin on the FortiGate |

**Decision**: token-only for all three in v1. Username/password adds session lifecycle for no capability
gain, and tokens are what both vendors' own docs recommend. Env vars per plane; a missing one is reported
by name (FR-029).

---

## Summary of decisions

| # | Decision | Drives |
|---|---|---|
| R1 | Build `mcp-servers/fortinet-mcp/`; candidates as reference only | FR-005a, FR-019, FR-020, FR-026 |
| R2 | One JSON-RPC client serves manager **and** analyzer | Halves the transport work |
| R3 | FortiOS device plane is separate REST + bearer token | FR-015–018 |
| R4 | `mcp` + `httpx` only; no dedicated venv | FR-041, spec 077 |
| R5 | ~20 parameterised tools, measured against 5,000 tokens | FR-025–027 |
| R6 | **Hyper-V for all three planes; containerlab dropped.** FortiGate live at 192.168.2.130 on FortiOS v8.0.0 | FR-036a |
| R7 | Port 076's two-gate logic with attribution | FR-020–024 |
| R8 | TLS verify on by default, explicit opt-out | FR-030 |
| R9 | Token auth only in v1 | FR-028, FR-029 |

## Still open — carried as tasks, not assumptions

1. **Measure the real manifest cost** once the surface exists (R5).
2. ~~Resolve the FortiGate version fork~~ — **closed**. containerlab dropped; the deployed device runs
   FortiOS v8.0.0 on Hyper-V (R6).
3. **Confirm FortiAnalyzer-VM has a Hyper-V image**; only the trial terms were verified, not the
   hypervisor matrix.
4. **Confirm the FortiGate 3-policy cap does not block FortiManager install verification** — installing a
   package with more than 3 rules onto a capped device may fail, which would be a finding about the lab,
   not the server.
5. **Activate the FortiGate evaluation licence** (currently `Invalid`). Blocks device-plane verification
   only — not the build. Note the free permanent eval is **one per FortiCloud account**.
6. **Re-verify community endpoint knowledge against FortiOS v8.0.0.** All reference repos target 7.6.6 or
   older; treat their paths as leads, not facts (R6).
