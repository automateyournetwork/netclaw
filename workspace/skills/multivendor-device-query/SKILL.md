# Multivendor Device Query

Query network devices on platforms NetClaw's Cisco- and Juniper-specific servers cannot reach —
MikroTik RouterOS, VyOS, SONiC, Nokia SR Linux, Extreme, Huawei, Dell, Ubiquiti EdgeOS, and roughly
eighty more.

**MCP server:** `multivendor-cli-mcp` (results identify themselves as `multivendor-cli`)

---

## Decide which server to use FIRST

This skill is wrong for most Cisco and Juniper work. Check here before using it:

| Your device | Use |
|---|---|
| Cisco IOS / IOS-XE / NX-OS / IOS-XR | **`pyats-*` skills** — ~2000 Genie parsers, state diffing |
| Juniper Junos | **`junos-network` skill** — PyEZ/NETCONF |
| Streaming telemetry, any vendor | **`gnmi-telemetry` skill** |
| No direct reachability | **`radkit-remote-access` skill** |
| Anything else | **this skill** |
| "Compare X across Cisco *and* Arista *and* Nokia" | **this skill** (read-only) |

That last row is the exception worth understanding. NAPALM returns one shape across vendors, so this
is the only server that can answer a genuinely cross-vendor question. It answers those **read-only**,
even on Cisco and Juniper.

**Configuration writes on Cisco and Juniper are refused**, naming the correct server. That is
deliberate, not a limitation: one write path per platform is what makes "verify the change" mean
something. Reads may overlap between servers; writes may not.

## Tools

| Tool | Purpose |
|---|---|
| `server_info` | Server identity, read-only vs write mode, which platforms have destructive-syntax modelling |
| `check_command_policy` | Would this command be permitted? Answers without touching a device |
| `list_devices` | Inventory, with the source that answered and why |
| `check_device_readiness` | Is this device resolvable, authenticable, and mine to act on? Contacts nothing |

## Workflow

1. **`list_devices`** — confirm the device is in inventory and see `owning_server`. If that is
   `pyats` or `junos-mcp`, stop and use that server for single-device work.
2. **`check_device_readiness`** — verify credentials resolve and check what this server may do.
   Run this before anything else on a new device: it separates *not in inventory* from
   *credentials missing* from *owned by another server*, which need three different fixes.
3. **`check_command_policy`** — before an unusual command, confirm it passes policy.

## Reading the results

**`source_used`** names which inventory source answered: `live_sot`, `generated`, or `operator`. When
it is not `live_sot`, `fallback_reason` says why — treat those results as potentially stale.

**`credential_path`** says `vault` or `environment`. Both are supported; Vault is not required.

**`status: refused`** with `owning_server` means routing sent you elsewhere. This is a successful
call, not an error — read `refused_reason` and use the named server.

## Safety

Read-only by default; write tools are **absent** from the tool list unless an operator sets
`MULTIVENDOR_WRITE_ENABLED`. Command filtering is enforced **server-side**, so it cannot be bypassed
by rephrasing a request. Evaluation order: chaining (`;`, `&&`, `||`, `>`, `<`) is rejected first,
then per-platform destructive verbs, then the read-only allowlist.

Chaining is checked first because `show version; write erase` begins with an allowlisted verb.

A single `|` is fine — on network devices that is a display filter, not a shell pipe.

## Environment variables

See `.env.example` for the full set. `MULTIVENDOR_INVENTORY_SOURCE`,
`MULTIVENDOR_INVENTORY_PATH`, `MULTIVENDOR_USERNAME`/`MULTIVENDOR_PASSWORD`,
`MULTIVENDOR_WRITE_ENABLED`. **Never put credentials in an inventory file** — the server rejects
inventory records containing credential-shaped fields.

## Caveat worth knowing

Netmiko also drives Fortinet, PAN-OS and Check Point, so this server gives *CLI-level* reach to them.
That is **not** equivalent to their dedicated API integrations — FortiManager's policy-package model
and Panorama's device groups have no CLI equivalent. Do not treat CLI reach as full vendor support.

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
