# Ninety Platforms, Two Bugs, and Why We Didn't Adopt Either Candidate

**Draft for review — not published.** Constitution Principle XVII requires John's sign-off first.

*By John Capobianco and Claude · 2026-07-31*

NetClaw could reach network devices four ways, and every one was platform-bound: pyATS for Cisco,
junos-mcp for Juniper, gNMI for telemetry, RADKit for cloud-relayed access. If you had a MikroTik edge
router, a VyOS firewall, a SONiC white-box or a Nokia SR Linux fabric, NetClaw had nothing to say.

Roadmap item R1 closed that gap. Here's what we actually learned.

## Four libraries, not four choices

"Nornir vs NAPALM vs Netmiko vs pyATS" reads like a tool selection. It isn't — they're four layers.
Netmiko is transport (SSH, ~175 platforms, raw text). NAPALM is normalization (vendor-neutral getters,
~10 platforms, identical shape). Nornir is orchestration and drives the others. pyATS/Genie is parse
and test, Cisco-deep with ~2000 parsers.

Recognising that resolved the design. The real trade-off is NAPALM's *normalized but narrow* against
Genie's *rich but Cisco-centric*. We chose platform-first routing: dedicated servers own their
platforms, the new server covers everything else — plus cross-vendor normalized reads as an explicit
exception, because NAPALM is the only thing that can answer "compare BGP neighbours across Cisco AND
Arista AND Nokia" in one shape.

**Writes stay single-pathed per platform.** Reads may overlap; writes may not. That asymmetry isn't
tidiness — the Constitution requires device state be verified rather than assumed, and post-change
verification to compare actual against expected. Both become unenforceable the moment "verified by
which tool?" has two answers.

## We rejected both community servers

Two existed. `sydasif/nornir-mcp-server` had a genuinely good safety model — prefix allowlist,
destructive-token denylist, chaining prevention, path sandboxing — but it was **archived**, and it
reloaded its config from the working directory on every call, threading the inventory assumption
through the request path. `ntunes/netmiko-mcp-server` had **no command filtering whatsoever**.

So we built on the libraries and deliberately ported the archived project's safety design. Adopting
either would have meant carrying an unmaintained dependency *and* rewriting its core abstraction.

## The two bugs only real hardware found

We had 93 passing offline tests before touching a device. Then John spun up a lab.

**The filter blocked FRR's only read path.** FRR is read over SSH via `vtysh -c "show ip route"` —
whose first token is `vtysh`, not an allowlisted verb. So legitimate reads were refused. The obvious
fix, adding `vtysh` to the allowlist, is *badly wrong*: it permits `vtysh -c "configure terminal"`,
turning the wrapper into a config escape. The correct fix unwraps recognised wrappers and evaluates
what they actually run.

**Nokia SR Linux was under-protected.** The netmiko driver and our inventory used `nokia_srl`; the
denylist table used `nokia_srlinux`. Same platform, two spellings, no code connecting them — so SR
Linux devices were checked against the universal baseline only, **missing `tools system
configuration`**, their actual config-wipe command. Nothing in the source or the unit tests could have
revealed that.

Neither bug was findable by reading code. That's the argument for lab verification in one paragraph.

## A third bug, found by the spec process

`/speckit.analyze` flagged that Constitution Principle III — ITSM-gated changes — had **zero task
coverage**, while the plan claimed it was "inherited from the existing approval path." That was an
assertion with nothing behind it. Human approval and a ServiceNow Change Request are *distinct gates*:
one is a person saying yes, the other is change-management authorisation with a lifecycle.

Now a production change requires both, verified against a live ServiceNow instance. An **unclassified**
device is treated as production — guessing "lab" wrongly permits an unauthorised production change.

## Honest accounting

The original success criterion asked for five platform families verified live. We verified **two**, and
amended the criterion rather than quietly claiming five. Only SR Linux has a fully public container
image; cEOS, SONiC, VyOS and Cumulus each need an account, an artifact download or a build. Chasing
five would have measured lab-building effort, not the server's behaviour.

Two families from *different paradigms* — one native NOS CLI, one shell-hosted — turned out to be
better evidence anyway. They exercise different halves of the driver abstraction, and each found a bug
the other wouldn't have.

## What it looks like now

Ten tools, read-only by default, write tools **absent** from the tool list unless explicitly enabled.
Three inventory tiers — live source of truth, generated cache, operator-authored — where the cache and
the operator file are strictly distinguished so a refresh can never destroy hand-maintained work.
Credentials from Vault or environment, never from an inventory file, with `repr` overridden so a stray
traceback can't leak them.

175 platform families driver-documented. Two verified live. Ninety-odd newly reachable.

*Next: R0a, where we fix the seven servers that break on a fresh install because `mcp 2.0.0` removed
`mcp.server.fastmcp`.*
