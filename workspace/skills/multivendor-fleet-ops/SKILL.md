# Multivendor Fleet Ops

Ask one question of many devices at once — across mixed vendors — and get per-device answers.

**MCP server:** `multivendor-cli-mcp` · **Tools:** `run_fleet`, `get_facts`

## `run_fleet`

`target` is a group name, a comma-separated device list, or `all`. Supply exactly one of:

- `command` — raw CLI, only for platforms this server owns
- `getters` — NAPALM normalized facts, permitted read-only on any platform

```
run_fleet(target="edge", getters=["get_facts","get_interfaces"])
run_fleet(target="srl1,srl2", command="show version")
```

## Reading results — the invariant that matters

**`requested` always equals `returned`.** Every targeted device appears, including failures. A
silently absent device would read as success, which is the most dangerous possible output for a fleet
query — you'd scan the list and see no problem where there is one.

`summary` counts by status. One device failing never aborts the others.

Defaults: **10 concurrent workers**, **30s per-device timeout**, both overridable. Ten rather than
Nornir's own 20 because each worker holds an SSH session and devices commonly cap concurrent
management sessions at 5–15.

## Cross-vendor comparison — the reason this exists

`get_facts` returns **one shape across vendors**, which no other NetClaw server can do. `pyATS` and
`junos-mcp` each answer well for their own platform, but their shapes differ, so a question spanning
vendors otherwise needs reconciling by hand.

Where a platform has no NAPALM driver — SR Linux, FRR, VyOS, MikroTik — you get a **row with
`available: false` and a `gap_reason`**, not a missing row. That distinction is deliberate: "this
platform cannot tell us" and "there are none" are different answers, and conflating them produces a
wrong one. `provenance` is never faked as `napalm` for scraped output.

Verified live: `get_facts` across IOS-XE and SR Linux returns rows with identical keys — one is data,
one is a reported gap.

## Caveat: CLI reach is not full vendor support

netmiko also drives **Fortinet, Palo Alto PAN-OS and Check Point**, so this server gives *CLI-level*
reach to them today. That is **not** equivalent to their dedicated API integrations:

| Vendor | What CLI gives you | What it does NOT give you |
|---|---|---|
| Fortinet | FortiOS CLI reads | FortiManager policy packages, ADOM model, install preview |
| Palo Alto | PAN-OS CLI reads | Panorama device groups, templates, commit validation |
| Check Point | GAiA CLI reads | Management API policy layers, threat intel |

Roadmap items **R3** (Fortinet) and **R4** (Palo Alto) are still needed. Do not treat CLI reach as
completing them.
