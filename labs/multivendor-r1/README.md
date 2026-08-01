# R1 verification lab (spec 076)

Two ways to give the multivendor CLI driver a real non-Cisco device to talk to.
Needed because SC-001 asks for live state from platform families NetClaw's
existing servers cannot reach — and the available CML lab contains only Cisco
devices, which are precisely the platforms FR-009 routes *away* from this server.

---

## Option 1 — FRR over SSH (no containerlab, no downloads)

**This is the zero-friction option and it is already verified working.**

The repo's existing `netclaw-core` / `netclaw-edge1` / `netclaw-edge2` FRR
containers **cannot** be used: they ship `vtysh` but no `sshd`, and netmiko needs
SSH. They are also live BGP peers for the `frr-testbed` stack, so they must not be
modified.

This builds a *separate* FRR container with `sshd` added, using the already-cached
`frrouting/frr` image.

```bash
cd labs/multivendor-r1/frr-ssh
docker build -t netclaw-frr-ssh:test .
docker run -d --name netclaw-r1-frr --privileged -p 2222:22 netclaw-frr-ssh:test
```

Then point the server at it:

```bash
export MULTIVENDOR_INVENTORY_SOURCE=operator
export MULTIVENDOR_INVENTORY_PATH=$PWD/labs/multivendor-r1/frr-inventory.yaml
export MULTIVENDOR_FRRLAB_USERNAME=netops
export MULTIVENDOR_FRRLAB_PASSWORD=netops123
export MULTIVENDOR_FRR_LAB_01_PORT=2222
```

**What this exercises**, verified end to end:

| Case | Result |
|---|---|
| `vtysh -c "show ip route"` | allowed, real FRR routing table returned |
| `vtysh -c "configure terminal"` | **denied** — wrapper unwrapped, inner verb not read-only |
| `vtysh -c "reload"` | **denied** — inner verb denylisted |
| `vtysh -c "show version"; reload` | **denied** — chaining rejected first |
| `rm -rf /` | **denied** — destructive verb |
| raw read on a `cisco_xe` device | **refused**, names `pyats` |

Denied commands never open a session — the filter runs before connecting.

### Why FRR needed a code change

FRR's only read path over SSH is `vtysh -c "show ..."`, whose first token is
`vtysh`, not an allowlisted verb — so the filter blocked legitimate reads. The
obvious fix, adding `vtysh` to the read-only allowlist, is **badly wrong**: it
would permit `vtysh -c "configure terminal"`, turning the wrapper into a config
escape.

The correct fix, now implemented, is to **unwrap** recognised CLI wrappers and
evaluate the inner command. Found by testing against a real device, not by
reading the code.

---

## Option 2 — Nokia SR Linux via containerlab (a genuinely different CLI)

FRR is reached through netmiko's `linux` driver, i.e. a shell. SR Linux is a
*native network CLI* with its own prompt handling, so it exercises the driver
abstraction in a way a shell-based platform cannot. It is also the only
enterprise NOS whose container image is fully public — no account, no licence:
`ghcr.io/nokia/srlinux:latest` (manifest verified public).

```bash
bash -c "$(curl -sL https://get.containerlab.dev)"       # needs sudo
sudo containerlab deploy -t labs/multivendor-r1/srl-lab.clab.yml
ssh admin@172.20.20.11                                    # NokiaSrl1!
```

SR Linux needs 30–60s after deploy before SSH answers. Use
`labs/multivendor-r1/inventory.yaml`, which sets `platform: nokia_srl`.

SR Linux also has **no NAPALM driver**, which usefully exercises FR-007's
"report the normalization gap explicitly rather than faking it" path.

---

## Platforms considered and why

| Platform | netmiko driver | Image obtainable |
|---|---|---|
| **FRR** (via `linux`) | ✅ | **already cached** — Option 1 |
| **Nokia SR Linux** | `nokia_srl` ✅ | **public, no account** — Option 2 |
| Arista cEOS | `arista_eos` ✅ | free Arista account required |
| VyOS | `vyos` ✅ | needs building from ISO |
| SONiC | `dell_sonic` ✅ | Azure build-artifact download |
| MikroTik / Extreme / Huawei | ✅ | licensed VM images only |
