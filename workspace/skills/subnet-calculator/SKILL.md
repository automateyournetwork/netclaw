---
name: subnet-calculator
description: "IPv4 and IPv6 subnet calculator - CIDR breakdown, usable hosts, previous/next subnets, address classification, VLSM planning, and dual-stack analysis"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["SUBNET_MCP_SCRIPT", "MCP_CALL"] } } }
---

# Subnet Calculator (IPv4 + IPv6)

Calculate subnet details for both IPv4 and IPv6 networks. Supports CIDR notation, provides usable host ranges, neighboring subnets, address classification, and standard allocation annotations.

## Available Tools

### 1. `subnet_calculator` — IPv4 Subnet Details

```bash
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"192.168.1.0/24"}'
```

**Parameters:**
- `cidr` (required): IPv4 CIDR notation, e.g., `10.0.0.0/8`, `172.16.0.0/12`, `192.168.1.0/24`

**Returns:**
- Network address, broadcast address, netmask, wildcard mask
- Prefix length, host bits
- Number of total and usable addresses
- First and last usable host addresses
- Usable hosts preview (up to 10)
- Previous and next subnets (same size)
- Address classification: private, global, link-local, multicast, loopback, reserved
- Human-readable summary

### 2. `subnet_calculator_v6` — IPv6 Subnet Details

```bash
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_v6 '{"cidr":"2001:db8::/48"}'
```

**Parameters:**
- `cidr` (required): IPv6 CIDR notation, e.g., `2001:db8::/32`, `fd00::/64`, `fe80::/10`

**Returns:**
- Network address (compressed and exploded forms)
- Last address in range
- Prefix length, host bits
- Number of addresses (exact for /64+, exponential notation for larger)
- Number of /64 subnets contained
- Previous and next subnets
- Address classification: ULA, global unicast, link-local, multicast
- Standard allocation annotation (e.g., "/64 = SLAAC capable", "/48 = site allocation")
- Human-readable summary

### 3. `subnet_calculator_auto` — Auto-Detect IPv4/IPv6

```bash
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_auto '{"cidr":"10.0.0.0/24"}'
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_auto '{"cidr":"2001:db8:abcd::/48"}'
```

Automatically detects IP version and calls the appropriate calculator.

## When to Use

- **Interface addressing**: Calculate the correct subnet for a new interface
- **VLSM planning**: Break a large block into appropriately sized subnets
- **ACL wildcard masks**: Get the wildcard mask for access-list entries
- **Routing verification**: Confirm that route entries match expected subnets
- **IPv6 migration planning**: Understand IPv6 allocation standards (/48, /64, /128)
- **Network design**: Validate addressing schemes before deployment
- **Troubleshooting**: Verify if two IPs are in the same subnet

## Common Network Engineering Scenarios

### Scenario 1: Point-to-Point Link Addressing

**IPv4 /30 link:**
```bash
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"10.1.1.0/30"}'
```
Result: 4 addresses, 2 usable (10.1.1.1 and 10.1.1.2). Standard for router-to-router links.

**IPv4 /31 link (RFC 3021):**
```bash
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"10.1.1.0/31"}'
```
Result: 2 addresses (10.1.1.0 and 10.1.1.1). No broadcast waste.

**IPv6 /127 link (RFC 6164):**
```bash
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_v6 '{"cidr":"2001:db8:1::/127"}'
```
Result: 2 addresses. Recommended for IPv6 point-to-point links.

### Scenario 2: VLSM Subnet Planning

Break 10.10.0.0/16 into subnets for different departments:

```bash
# Engineering: 500 hosts needed → /23 (510 usable)
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"10.10.0.0/23"}'

# Sales: 100 hosts needed → /25 (126 usable)
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"10.10.2.0/25"}'

# Management: 10 hosts needed → /28 (14 usable)
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"10.10.2.128/28"}'

# Server VLAN: 30 hosts needed → /27 (30 usable)
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"10.10.2.192/27"}'
```

Produce an addressing plan:

```
Subnet Plan — 10.10.0.0/16
┌────────────┬─────────────────┬────────┬───────────┬───────────────┐
│ Department │ Subnet          │ Prefix │ Usable    │ Gateway       │
├────────────┼─────────────────┼────────┼───────────┼───────────────┤
│ Engineering│ 10.10.0.0/23    │ /23    │ 510 hosts │ 10.10.0.1     │
│ Sales      │ 10.10.2.0/25    │ /25    │ 126 hosts │ 10.10.2.1     │
│ Management │ 10.10.2.128/28  │ /28    │ 14 hosts  │ 10.10.2.129   │
│ Servers    │ 10.10.2.192/27  │ /27    │ 30 hosts  │ 10.10.2.193   │
│ P2P Links  │ 10.10.3.0/24    │ /30 ea │ 2 per link│ varies        │
└────────────┴─────────────────┴────────┴───────────┴───────────────┘
```

### Scenario 3: IPv6 Site Allocation

Plan a /48 allocation for a campus:

```bash
# Site allocation
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_v6 '{"cidr":"2001:db8:abcd::/48"}'

# Building 1 — first /56 from the /48
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_v6 '{"cidr":"2001:db8:abcd::/56"}'

# Floor 1, Building 1 — first /64 from the /56
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_v6 '{"cidr":"2001:db8:abcd::/64"}'

# Loopback /128
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_v6 '{"cidr":"2001:db8:abcd::1/128"}'

# Point-to-point /127
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_v6 '{"cidr":"2001:db8:abcd:ffff::/127"}'
```

```
IPv6 Allocation — 2001:db8:abcd::/48
┌──────────────┬──────────────────────────┬────────┬──────────────────────┐
│ Purpose      │ Prefix                   │ Size   │ Note                 │
├──────────────┼──────────────────────────┼────────┼──────────────────────┤
│ Site         │ 2001:db8:abcd::/48       │ /48    │ 65,536 /64 subnets   │
│ Building 1   │ 2001:db8:abcd::/56       │ /56    │ 256 /64 subnets      │
│ Floor 1/B1   │ 2001:db8:abcd::/64       │ /64    │ SLAAC capable        │
│ Loopback     │ 2001:db8:abcd::1/128     │ /128   │ Single host          │
│ P2P Link     │ 2001:db8:abcd:ffff::/127 │ /127   │ RFC 6164             │
└──────────────┴──────────────────────────┴────────┴──────────────────────┘
```

### Scenario 4: ACL Wildcard Mask Reference

```bash
# What's the wildcard for a /22?
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"10.0.0.0/22"}'
```

Use the `wildcard_mask` field directly in ACL configuration:
```
ip access-list extended EXAMPLE
  permit ip 10.0.0.0 0.0.3.255 any
```

### Scenario 5: Dual-Stack Verification

Verify both IPv4 and IPv6 assignments on an interface:

```bash
# IPv4 side
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"10.1.1.1/30"}'

# IPv6 side
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator_v6 '{"cidr":"2001:db8:1::1/127"}'
```

## Quick Reference: Common Prefix Sizes

### IPv4
| Prefix | Hosts | Usable | Use Case |
|--------|-------|--------|----------|
| /30 | 4 | 2 | Point-to-point link |
| /29 | 8 | 6 | Small DMZ |
| /28 | 16 | 14 | Management VLAN |
| /27 | 32 | 30 | Server VLAN |
| /26 | 64 | 62 | Small department |
| /25 | 128 | 126 | Medium department |
| /24 | 256 | 254 | Standard subnet |
| /23 | 512 | 510 | Large subnet |
| /22 | 1024 | 1022 | Campus building |
| /16 | 65536 | 65534 | Campus site |

### IPv6
| Prefix | Subnets (/64) | Use Case |
|--------|--------------|----------|
| /128 | 0 | Single host (loopback) |
| /127 | 0 | Point-to-point link (RFC 6164) |
| /64 | 1 | Standard subnet (SLAAC) |
| /56 | 256 | Building or floor |
| /48 | 65,536 | Site allocation |
| /32 | 16,777,216 | ISP allocation |

## Integration with Network Config

After calculating subnets, use pyats-config-mgmt to apply:

```bash
# Calculate the subnet first
python3 $MCP_CALL "python3 -u $SUBNET_MCP_SCRIPT" subnet_calculator '{"cidr":"10.1.1.0/30"}'

# Then configure the interface
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_configure_device '{"device_name":"R1","config_commands":["interface GigabitEthernet2","ip address 10.1.1.1 255.255.255.252","no shutdown"]}'
```
