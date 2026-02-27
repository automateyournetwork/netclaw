# FRR Lab Testbed

Three-router FRR topology for testing NetClaw protocol participation (BGP + OSPF over GRE).

## Topology

```
NetClaw (AS 65001)          Edge1 (AS 65000)       Core (AS 65000, RR)     Edge2 (AS 65000)
  host/WSL                  1.1.1.1                2.2.2.2                 3.3.3.3
  4.4.4.4                   10.0.12.1              10.0.12.2               10.0.23.3
  172.16.0.2 ──GRE──────── 172.16.0.1
                            10.0.100.1

  eBGP AS 65001↔65000       OSPF Area 0            OSPF Area 0             OSPF Area 0
                            iBGP → Core(RR)        iBGP RR hub             iBGP → Core(RR)
```

## Quick Start

```bash
# 1. Start the lab
docker compose up -d

# 2. Wait for OSPF/BGP convergence (~15 seconds)
sleep 15

# 3. Create GRE tunnel from host to Edge1 (requires sudo)
sudo bash scripts/setup-gre.sh

# 4. Verify everything
bash scripts/verify.sh
```

## Verify Manually

```bash
# OSPF neighbors
docker exec netclaw-edge1 vtysh -c "show ip ospf neighbor"
docker exec netclaw-core vtysh -c "show ip ospf neighbor"

# BGP summary
docker exec netclaw-core vtysh -c "show bgp summary"
docker exec netclaw-edge1 vtysh -c "show bgp summary"

# BGP routes
docker exec netclaw-core vtysh -c "show bgp ipv4 unicast"

# GRE tunnel
ping 172.16.0.1
```

## Teardown

```bash
sudo bash scripts/teardown-gre.sh
docker compose down
```

## Networks

| Network | Subnet | Purpose |
|---------|--------|---------|
| edge1-core | 10.0.12.0/24 | Edge1 to Core |
| core-edge2 | 10.0.23.0/24 | Core to Edge2 |
| peering | 10.0.100.0/24 | Edge1 exposed to host |
| GRE tunnel | 172.16.0.0/30 | Host to Edge1 |

## Test Prefixes

Edge2 advertises `192.168.99.0/24` via iBGP. When NetClaw peers with Edge1, it should see this prefix in the BGP table as evidence of end-to-end reachability through the RR.
