# Quickstart: Multivendor CLI Driver

**Feature**: 076-multivendor-cli-driver | **Date**: 2026-07-30

Onboarding for the server that reaches the ~90 platforms NetClaw's other device servers cannot.

---

## Which server should answer? Read this first

This server is **not** a replacement for `pyATS` or `junos-mcp`. Platform-first routing:

| Your device | Use |
|---|---|
| Cisco IOS / IOS-XE / NX-OS / IOS-XR | **`pyATS`** — far richer, ~2000 Genie parsers |
| Juniper Junos | **`junos-mcp`** — PyEZ/NETCONF |
| Streaming telemetry, any vendor | **`gnmi-mcp`** |
| No direct reachability | **`radkit-mcp`** |
| MikroTik, VyOS, SONiC, SR Linux, Extreme, Huawei, Dell, EdgeOS, … | **this server** |
| "Compare BGP neighbours across Cisco *and* Arista *and* Nokia" | **this server** (read-only) |

The last row is the exception worth understanding: NAPALM normalizes output across vendors, so this
server is the right tool when a question *spans* vendors even if a dedicated server exists for some of
them. It answers those **read-only**.

**It will refuse configuration writes on Cisco and Juniper**, naming the correct server. That is
deliberate — one write path per platform is what makes "verify the change" mean something.

---

## Step 1 — Install

```bash
./scripts/install.sh          # select "Multivendor CLI Driver"
```

The install creates a **dedicated virtualenv** for this server. That is not incidental: `napalm` and
`netmiko` pull `cryptography`, which NetClaw's federation stack uses for X.509 certificate issuance. A
version conflict would break certificate handling rather than this server, so the dependencies stay
isolated.

If you install manually, note that on some hosts `pip3` and `python3` are **different interpreters**
pointing at different site-packages. Always use the venv's own pip:

```bash
/usr/bin/python3 -m venv mcp-servers/multivendor-cli-mcp/.venv
mcp-servers/multivendor-cli-mcp/.venv/bin/python -m pip install -r \
    mcp-servers/multivendor-cli-mcp/requirements.txt
```

Verify nothing shared moved:

```bash
/usr/bin/python3 -c "import importlib.metadata as m; print(m.version('cryptography'))"
```

Same version before and after, or stop and investigate.

---

## Step 2 — Choose an inventory source

Three supported. Pick the one matching what you already run.

### Option A — Live source of truth (preferred)

You run NetBox, Nautobot, or Infrahub. Devices are read at call time, so inventory **cannot drift**.

```bash
MULTIVENDOR_INVENTORY_SOURCE=live_sot
NETBOX_URL=https://netbox.example.com
NETBOX_TOKEN=...            # in .env, never committed
```

### Option B — Generated from a source of truth

You have a source of truth but need offline or air-gapped operation. An inventory file is rendered from
it at install and on refresh.

```bash
MULTIVENDOR_INVENTORY_SOURCE=generated
MULTIVENDOR_GENERATED_PATH=~/.openclaw/multivendor/inventory.generated.yaml
```

> **This file is a cache.** It carries a generated marker and **will be overwritten** on refresh. Do not
> hand-edit it — your edits will be lost. If you want a file you control, use Option C.

### Option C — Operator-authored

No source of truth. You write and maintain the inventory yourself, the same way you maintain a pyATS
`testbed.yaml`.

```bash
MULTIVENDOR_INVENTORY_SOURCE=operator
MULTIVENDOR_INVENTORY_PATH=~/.openclaw/multivendor/inventory.yaml
```

```yaml
# inventory.yaml — hostnames and platforms only. NO credentials.
edge-mt-01:
  hostname: 10.0.0.1
  platform: mikrotik_routeros
  groups: [edge, site-hq]
  credential_ref: default        # a REFERENCE, resolved at runtime
fw-vyos-01:
  hostname: 10.0.0.2
  platform: vyos
  groups: [edge, site-hq]
  credential_ref: default
```

**The server never writes to this file.** A generated-inventory refresh cannot touch it.

`auto` (the default) tries live, then generated, then operator — and every result tells you which one
answered, so a stale cache never masquerades as live.

**Your pyATS `testbed.yaml` is not an inventory source.** It assumes Cisco, and its platforms
(`iosxe`, `nxos`, `iosxr`) are exactly the ones routed to `pyATS` instead.

---

## Step 3 — Credentials

**Never in the inventory file.** Two supported paths:

```bash
# Preferred: Vault
VAULT_ADDR=https://vault.example.com
VAULT_NAMESPACE=netclaw

# Fallback: environment variables in .env (gitignored)
MULTIVENDOR_USERNAME=netops
MULTIVENDOR_PASSWORD=...
```

Vault is **not required.** If you have no Vault — likely if you chose Option C — environment variables
are fully supported. Both keep secrets off disk in any inventory file, which is the actual requirement.

Every result reports which path supplied the credential, so you can audit a deployment's posture.

---

## Step 4 — Verify

```bash
python3 scripts/reconcile-mcp.py          # must exit 0
```

Then, from NetClaw:

```
"list my multivendor devices"
"check reachability of edge-mt-01"
"get interfaces and facts for fw-vyos-01"
"show me BGP neighbours across the edge group"
```

`check_reachability` is the right first call on a new device — it separates *unreachable* from
*authentication failed* from *the platform in your inventory is wrong*, which need three different fixes.

---

## Step 5 — Understand the safety model before enabling writes

Read-only is the default and write tools are **not exposed at all** until you opt in:

```bash
MULTIVENDOR_WRITE_ENABLED=true
```

Filtering is enforced **server-side**, in this order:

1. Reject any command containing `;` `&&` `||` `>` `<` `` ` `` `$(`
2. Reject a denylisted first token — per platform, because destructive syntax differs (VyOS `delete`,
   MikroTik `/system reset-configuration`, SR Linux `tools system configuration`, SONiC `config erase`)
3. In read-only mode, reject anything not starting with `show` / `display` / `get`

Chaining is rejected **first** and that ordering is deliberate: `show version; write erase` would pass
an allowlist check on its first token.

With writes enabled, every change is: capture baseline → require approval → apply → **verify actual
state against expected via structured diff** → roll back on failure. Verification compares state, not
whether the command returned successfully.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `status: denied`, `denied_reason` mentions chaining | Command contained `;` or `&&` | Send commands separately |
| `status: denied` in read-only mode | Verb not in the allowlist | Use a `show`-class command, or enable write mode deliberately |
| `status: platform_mismatch` | Inventory platform ≠ what the device reports | Fix the source of truth; wrong driver gives confusing output |
| `status: auth_failed` | Credentials resolved but rejected | Check Vault path or env vars — note this is *not* unreachable |
| `apply_config` returns `refused` | Cisco/Junos device | Use `pyATS` or `junos-mcp`; this server is read-only there by design |
| `available: false` on a getter | Platform's NAPALM driver lacks it | Use `run_command` for the raw equivalent — the gap is reported, not hidden |
| My generated inventory edits vanished | It is a cache | Move to Option C, an operator-authored file the server never writes |
| `source_used` is `generated`, not `live_sot` | Source of truth was unreachable | Check `fallback_reason`; results may be stale |
