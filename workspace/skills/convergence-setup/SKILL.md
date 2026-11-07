---
name: convergence-setup
description: Set up Convergence, the separately operated network observability service, on the user's own infrastructure. Asks only for what it cannot discover, shows the plan before changing anything, then builds a local Docker trial, installs into an existing K3s cluster (Helm or Argo CD), or builds a new K3s cluster on Proxmox VE first. Verifies each layer and connects NetClaw's read-only Convergence view. Use for installing or extending Convergence; use convergence-observations to read its data.
version: 1.0.0
license: Apache-2.0
tags: [convergence, setup, docker, k3s, argocd, proxmox]
compatibility: "Linux hosts. Uses the network: Docker and Kubernetes APIs, the Proxmox VE API, SSH to new nodes, and GitHub/Helm/container registries for pinned downloads."
metadata:
  openclaw:
    requires:
      bins: [git, python3]
---

# Convergence setup

Convergence is a separate project: [byrn-baker/convergence-platform](https://github.com/byrn-baker/convergence-platform).
It owns the services, charts, cluster tooling and setup helpers. This skill installs a
**pinned release** of it and follows that release's own procedures, so the commands
always match the code they run. NetClaw never imports or operates the service itself.

**Tested release: `v0.1.1`.** Use it unless the user asks for another; say so if they do.

## 1. Get the release

Ask where to keep it (default `~/convergence`). Never clone into the NetClaw checkout.

```bash
git clone --branch v0.1.1 https://github.com/byrn-baker/convergence-platform.git ~/convergence
```

An existing checkout is fine if `git describe --tags` names the release. Every helper
below runs from that checkout and takes it as `--repo`. The procedures are in its
`docs/convergence/setup/`: read the one for the chosen path before acting.

## 2. Discover, then ask only what is left

Inspect first; ask only for what you could not find. Never ask for secrets in chat:
ask the user to put them in a private file (mode 600) and tell you the path.

- **Where it runs.** Docker on one Linux host (a trial), an existing K3s cluster, or a
  **new K3s cluster on Proxmox VE**. For K3s: Helm directly, or Argo CD from the user's
  Git repository.
- **Existing state.** Running Convergence or monitoring containers, Helm releases,
  Kubernetes contexts. Existing monitoring is a reuse or migration case, not an empty
  host.
- **Site.** A short site name, and what should be observed: router or firewall flows,
  a host interface, or the labelled demonstrations only.
- **Access.** How the user reaches dashboards and the API: this machine only, a LAN,
  or an existing authenticated proxy.

For a new cluster, the release's `docs/convergence/setup/cluster.md` lists the
Proxmox questions (node, template, storage, bridge/VLAN, VMID range and name prefix,
addresses and the API VIP, SSH key) and which ones discovery answers. If a Proxmox MCP
is available ([mcp-proxmox](https://github.com/gilby125/mcp-proxmox) with
`PROXMOX_ALLOW_ELEVATED=false`), use it for read-only discovery. Provisioning uses the
release's `deploy/cluster/proxmox.py`, which only changes VMs inside the declared range
and prefix. Recommend a Proxmox API token limited to a pool for these VMs.

## 3. Show the plan, then act

Before any change, state: hosts and VMs to create, addresses, ports, what is reused,
what is installed, and how to undo it. Wait for the user's approval. Then follow the
release's procedure for the chosen path:

| Path | Procedure in the release |
|---|---|
| Docker trial | `docs/convergence/setup/docker.md` |
| Existing K3s (Helm or Argo CD) | `docs/convergence/setup/k3s.md` |
| New K3s cluster on Proxmox VE (+ Argo CD) | `docs/convergence/setup/cluster.md`, then `k3s.md` |
| Optional telemetry, IDS, flows, JEV | `docs/convergence/setup/integrations.md`, only the selected sections |

Read-only steps (`check`, `plan`, `preflight`, `verify`) can run freely. Steps that
create VMs, install K3s or Argo CD, change a cluster, a hypervisor or a switch need the
approval above; ask again for anything outside the approved plan. Preserve existing
credentials, data volumes and model settings. Keep demonstration data in its own site
or bundle.

If shell execution is not available, write the spec files and the exact commands in
order, label which ones change infrastructure, and let the user run them.

## 4. Verify and hand over

Follow the release's `docs/convergence/setup/acceptance.md`. Run `setup/verify.py`
for the installation, with `--canary` once the user agrees to labelled test records.
A running container is not a verified layer. To show NetClaw's view, configure the
`convergence-read` component with a **viewer** key for the site (NetClaw's
`docs/CONVERGENCE.md` explains it) and open the Convergence view.

Report: the release used, what was created (VMs, namespaces, bundles), URLs, enabled
layers, verification results, layers left unverified, and how to stop or remove each
one. Save a handover without credentials where the user keeps operations notes. Never
call a layer ready that was not verified.
