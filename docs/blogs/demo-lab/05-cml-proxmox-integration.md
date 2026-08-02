# 05 — CML ↔ Proxmox Integration

## Concept

CML runs the entire router/switch topology (SP core + CE routers). Proxmox runs
the K3s VMs with real compute resources. They connect at the DC LAN segments via
Proxmox Linux bridges passed into the CML VM as extra NICs.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           PROXMOX HOST                                    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                      CML VM                                       │    │
│  │                                                                  │    │
│  │  [SP Core + CEs]                                                 │    │
│  │       CE1-Gi3 ─── ext-dc1 (mapped to ens4 / vmbr100)            │    │
│  │       CE2-Gi3 ─── ext-dc2 (mapped to ens5 / vmbr200)            │    │
│  │       CE3-Gi3 ─── ext-dc3 (mapped to ens6 / vmbr300)            │    │
│  └──────────────────────────┬────────┬────────┬─────────────────────┘    │
│                             │        │        │                          │
│  Proxmox bridges:       vmbr100   vmbr200   vmbr300                     │
│                             │        │        │                          │
│  ┌──────────────┐   ┌──────┴───┐  ┌─┴────────┐   ┌──────────────┐     │
│  │ DC1 K3s VMs  │   │ DC2 K3s  │  │ DC2 K3s  │   │ DC3 K3s VMs  │     │
│  │ k3s-m1       │   │ k3s-m2   │  │ k3s-w3   │   │ k3s-m3       │     │
│  │ k3s-w1       │   │ k3s-w3   │  │ k3s-w4   │   │ k3s-w5       │     │
│  │ k3s-w2       │   │ k3s-w4   │  └──────────┘   └──────────────┘     │
│  └──────────────┘   └──────────┘                                        │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Create Proxmox Bridges

Add to `/etc/network/interfaces` on the Proxmox host:

```bash
# DC1 LAN segment (Customer A — 192.168.100.0/24)
auto vmbr100
iface vmbr100 inet manual
    bridge-ports none
    bridge-stp off
    bridge-fd 0
    description "DC1 - Customer A LAN"

# DC2 LAN segment (Customer B — 192.168.200.0/24)
auto vmbr200
iface vmbr200 inet manual
    bridge-ports none
    bridge-stp off
    bridge-fd 0
    description "DC2 - Customer B LAN"

# DC3 LAN segment (Customer C — 192.168.100.0/24, separate domain)
auto vmbr300
iface vmbr300 inet manual
    bridge-ports none
    bridge-stp off
    bridge-fd 0
    description "DC3 - Customer C LAN"
```

Apply:
```bash
ifreload -a
# or reboot
```

---

## Step 2: Add NICs to CML VM

The CML VM needs 3 additional network interfaces (beyond its management NIC):

| CML VM NIC | Proxmox Bridge | Purpose |
|------------|----------------|---------|
| net0 (ens3) | vmbr0 | CML management (web UI, API) |
| net1 (ens4) | vmbr100 | External connector → DC1 |
| net2 (ens5) | vmbr200 | External connector → DC2 |
| net3 (ens6) | vmbr300 | External connector → DC3 |

In Proxmox CLI:
```bash
qm set <CML_VMID> --net1 virtio,bridge=vmbr100
qm set <CML_VMID> --net2 virtio,bridge=vmbr200
qm set <CML_VMID> --net3 virtio,bridge=vmbr300
```

Or via the Proxmox web UI: VM → Hardware → Add → Network Device.

---

## Step 3: Map External Connectors in CML

In CML, create 3 **External Connector** nodes configured for "Bridge" mode:

| CML Node | Configuration | Maps to |
|----------|---------------|---------|
| ext-dc1 | Bridge virbr1 (or by interface name) | ens4 → vmbr100 |
| ext-dc2 | Bridge virbr2 | ens5 → vmbr200 |
| ext-dc3 | Bridge virbr3 | ens6 → vmbr300 |

> **Note:** CML's external connector bridge naming depends on your CML version.
> You may need to create bridge mappings in CML's system config
> (`/etc/virl2/config.yml`) to map the extra interfaces.

### CML wiring

```
CE1 Gi3 ──── unmanaged-switch-dc1 ──── ext-dc1
CE2 Gi3 ──── unmanaged-switch-dc2 ──── ext-dc2
CE3 Gi3 ──── unmanaged-switch-dc3 ──── ext-dc3
```

The unmanaged switch allows future expansion (add more CML nodes to the DC LAN).

---

## Step 4: Create K3s VMs in Proxmox

### VM creation commands

```bash
# DC1 — K3s server
qm create 201 --name k3s-m1 --memory 8192 --cores 4 --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --net1 virtio,bridge=vmbr100 \
  --scsi0 local-lvm:50 \
  --ide2 local:iso/ubuntu-22.04-server-cloudimg-amd64.img,media=cdrom \
  --boot order=scsi0 --ostype l26

# DC1 — K3s worker 1
qm create 202 --name k3s-w1 --memory 8192 --cores 4 --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --net1 virtio,bridge=vmbr100 \
  --scsi0 local-lvm:50 \
  --boot order=scsi0 --ostype l26

# DC1 — K3s worker 2
qm create 203 --name k3s-w2 --memory 8192 --cores 4 --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --net1 virtio,bridge=vmbr100 \
  --scsi0 local-lvm:50 \
  --boot order=scsi0 --ostype l26

# DC2 — K3s server
qm create 301 --name k3s-m2 --memory 8192 --cores 4 --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --net1 virtio,bridge=vmbr200 \
  --scsi0 local-lvm:50 \
  --boot order=scsi0 --ostype l26

# DC2 — K3s workers
qm create 302 --name k3s-w3 --memory 8192 --cores 4 --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --net1 virtio,bridge=vmbr200 \
  --scsi0 local-lvm:50 \
  --boot order=scsi0 --ostype l26

qm create 303 --name k3s-w4 --memory 8192 --cores 4 --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --net1 virtio,bridge=vmbr200 \
  --scsi0 local-lvm:50 \
  --boot order=scsi0 --ostype l26

# DC3 — K3s server
qm create 401 --name k3s-m3 --memory 8192 --cores 4 --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --net1 virtio,bridge=vmbr300 \
  --scsi0 local-lvm:50 \
  --boot order=scsi0 --ostype l26

# DC3 — K3s worker
qm create 402 --name k3s-w5 --memory 8192 --cores 4 --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --net1 virtio,bridge=vmbr300 \
  --scsi0 local-lvm:50 \
  --boot order=scsi0 --ostype l26
```

---

## Step 5: VM Networking (dual-homed)

Each VM has two NICs:

| NIC | Bridge | Purpose | IP |
|-----|--------|---------|-----|
| net0 (ens18) | vmbr0 | Management (SSH from workstation) | DHCP or static on mgmt LAN |
| net1 (ens19) | vmbr100/200/300 | DC LAN (K3s traffic, services) | Static per addressing plan |

**Why dual-home?** You need SSH access for provisioning and kubectl without
routing through CML. Once everything is running, all application and K3s cluster
traffic uses the DC LAN NIC through the MPLS fabric.

### Netplan example (Ubuntu 22.04)

```yaml
# /etc/netplan/50-cloud-init.yaml on k3s-m1
network:
  version: 2
  ethernets:
    ens18:
      dhcp4: true    # Management — gets you SSH access
    ens19:
      addresses:
        - 192.168.100.10/24
        - fd10:a:100::10/64
      routes:
        - to: 192.168.200.0/24
          via: 192.168.100.1
        - to: 192.168.100.0/24
          via: 192.168.100.1
          # (for DC3's overlapping subnet, use specific routes)
      gateway6: fd10:a:100::1
```

---

## Verification

Once everything is wired:

```bash
# From k3s-m1 (DC1), ping CE1 gateway
ping 192.168.100.1

# From k3s-m1 (DC1), ping k3s-m2 (DC2) — goes through MPLS core
ping 192.168.200.10

# Traceroute shows the MPLS path
traceroute 192.168.200.10
# Expected: 192.168.100.1 → (MPLS hops) → 192.168.200.1 → 192.168.200.10
```

---

## Resource Summary

| Component | Count | vCPU | RAM | Disk |
|-----------|-------|------|-----|------|
| CML VM | 1 | 8–16 | 32–64 GB | 100 GB |
| K3s VMs | 8 | 32 | 64 GB | 400 GB |
| **Total Proxmox** | — | **~48 vCPU** | **~128 GB** | **~500 GB** |

Adjust down if needed — minimum viable: CML (8 vCPU/32 GB) + 5 K3s VMs (20
vCPU/40 GB) = ~28 vCPU / 72 GB.
