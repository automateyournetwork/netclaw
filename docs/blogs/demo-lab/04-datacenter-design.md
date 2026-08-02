# 04 — Datacenter Design

## Architecture per DC

Each datacenter is minimal — a single CE router providing L3 gateway to a flat
LAN segment where K3s nodes live. This keeps the CML topology light while giving
full L3VPN reachability across the MPLS core.

```
SPE(x)
  │  eBGP (VRF)
  │
CE(x) ─── GigabitEthernet3 ──┐
                              │
                        L2 segment (bridge)
                         │    │    │
                      k3s-m  k3s-w1 k3s-w2
```

## K3s Cluster Model

**3 independent clusters** (one per DC) — most realistic for multi-tenant SP:

| DC | Cluster | Server node | Worker nodes | Total |
|----|---------|-------------|--------------|-------|
| DC1 | cluster-dc1 | k3s-m1 | k3s-w1, k3s-w2 | 3 |
| DC2 | cluster-dc2 | k3s-m2 | k3s-w3, k3s-w4 | 3 |
| DC3 | cluster-dc3 | k3s-m3 | k3s-w5 | 2 |

Cross-cluster connectivity relies entirely on the MPLS L3VPN fabric — pods in
DC1 reach services in DC2 by routing through CE1 → SPE1 → core → SPE2 → CE2.

## K3s Installation

### Server node (one per DC)

```bash
# On k3s-m1 (DC1)
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --cluster-init \
  --node-ip=192.168.100.10 \
  --flannel-iface=ens3 \
  --tls-san=192.168.100.10 \
  --disable=traefik \
  --write-kubeconfig-mode=644" sh -

# Get the token for workers
cat /var/lib/rancher/k3s/server/node-token
```

### Worker nodes

```bash
# On k3s-w1 (DC1)
curl -sfL https://get.k3s.io | K3S_URL=https://192.168.100.10:6443 \
  K3S_TOKEN=<token-from-server> \
  INSTALL_K3S_EXEC="agent --node-ip=192.168.100.11 --flannel-iface=ens3" sh -
```

### Repeat for DC2 and DC3

Each DC gets its own independent K3s cluster. The server nodes are:
- DC1: `k3s-m1` at `192.168.100.10`
- DC2: `k3s-m2` at `192.168.200.10`
- DC3: `k3s-m3` at `192.168.100.10` (different L2 domain, same IP is fine)

## K3s Networking

- **CNI:** Flannel (default, VXLAN mode) for intra-cluster pod networking
- **Service CIDR:** Default `10.43.0.0/16` per cluster (each cluster independent)
- **Pod CIDR:** Default `10.42.0.0/16` per cluster
- **Cross-DC traffic:** Goes through node IPs (192.168.x.x) — routed by the CE

For cross-cluster service discovery, use explicit DNS or a service mesh
(Skupper/Submariner) if you want to demonstrate that layer.

## Persistent Storage

Install Longhorn on each cluster for distributed block storage:

```bash
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml
```

Or use `local-path-provisioner` (default in K3s) for simplicity.

## Node Specs (Proxmox VMs)

| VM | vCPU | RAM | Disk | OS |
|----|------|-----|------|----|
| k3s-m* (server) | 4 | 8 GB | 50 GB | Ubuntu 22.04 |
| k3s-w* (worker) | 4 | 8 GB | 50 GB | Ubuntu 22.04 |

## Cloud-Init Template

```yaml
#cloud-config
hostname: k3s-m1
manage_etc_hosts: true
packages:
  - curl
  - open-iscsi
  - nfs-common
  - jq
network:
  version: 2
  ethernets:
    ens18:
      dhcp4: true          # Management NIC (vmbr0) — for SSH access
    ens19:
      addresses:
        - 192.168.100.10/24
      routes:
        - to: 192.168.200.0/24
          via: 192.168.100.1
        - to: 192.168.100.0/24
          via: 192.168.100.1
      # IPv6
      addresses:
        - fd10:a:100::10/64
      routes:
        - to: fd10:a:200::/64
          via: fd10:a:100::1
runcmd:
  - echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
  - sysctl -p
```

## Default Routes on K3s Nodes

Each K3s node's default gateway points to the local CE router:

| DC | Gateway (IPv4) | Gateway (IPv6) |
|----|----------------|----------------|
| DC1 | `192.168.100.1` (CE1) | `fd10:a:100::1` |
| DC2 | `192.168.200.1` (CE2) | `fd10:a:200::1` |
| DC3 | `192.168.100.1` (CE3) | `fd10:a:300::1` |

The CE routers handle eBGP to the PEs, so all inter-DC traffic naturally
traverses the MPLS VPN core.
