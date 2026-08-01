# Multivendor Raw CLI

Run a command on a device whose platform has no dedicated NetClaw server, and get its real output.

**MCP server:** `multivendor-cli-mcp` · **Tools:** `run_command`, `check_reachability`

## Check routing first

Refuses raw execution on Cisco and Juniper, naming `pyats` / `junos-mcp`. Those servers are richer for
their own platforms. Use `list_devices` and look at `owning_server` before reaching for this.

## Start with `check_reachability`

On any newly added device, run it first. It separates three failures that look identical in a generic
error message and need three different fixes:

| Status | Means | Fix |
|---|---|---|
| `unreachable` | TCP/port problem | network, or the device is down |
| `auth_failed` | credentials resolved but rejected | check Vault path or env vars |
| `platform_mismatch` | inventory platform ≠ reality, or no driver | correct the inventory |
| `not_found` | device in no inventory source | add it |

## Command policy

Filtering is **server-side and runs before connecting** — a denied command never opens a session. In
read-only mode the first verb must be `show`/`display`/`get`/… Ordering: chaining is rejected first,
then per-platform destructive verbs, then the allowlist.

**CLI wrappers are unwrapped and their inner command judged.** On FRR the only read path is
`vtysh -c "show ip route"`, whose first token is `vtysh` — so the wrapper is stripped and
`show ip route` is what gets evaluated. This means `vtysh -c "configure terminal"` is correctly
**denied**: allowlisting `vtysh` itself would have turned the wrapper into a config escape.

## Platform strings

Aliases are normalised, so `nokia_srl`, `srl` and `nokia_srlinux` all resolve to the same policy — and
to the SR Linux-specific denylist rather than only the universal baseline.

Verified live against Nokia SR Linux (native CLI) and FRR (shell-hosted).

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
