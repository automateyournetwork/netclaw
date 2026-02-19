# Example: RFC-Informed Configuration

## Prompt

```
Configure BGP on R1 to peer with 10.1.1.2 AS 65002, following RFC best practices
```

## What NetClaw Does

NetClaw uses **rfc-lookup** to reference standards, **pyats-config-mgmt** for change control, and **pyats-network** to apply config:

### Step 1: Research RFC Best Practices

```
→ rfc-lookup get_rfc: number "7454"  (BGP Operations and Security)
→ rfc-lookup get_rfc_section: number "7454", section "Prefix Filtering"
→ rfc-lookup get_rfc_section: number "7454", section "Next-Hop Filtering"
→ rfc-lookup get_rfc: number "4271"  (BGP-4 specification)
```

NetClaw extracts key recommendations from RFC 7454:
- Apply strict prefix filters on eBGP sessions
- Set maximum-prefix limits
- Use TTL security (GTSM) per RFC 5082
- Enable MD5 authentication
- Filter bogon prefixes
- Set explicit hold timer values

### Step 2: Pre-Change Baseline

```
→ pyats_show_running_config
→ pyats_run_show_command: show ip bgp summary
→ pyats_run_show_command: show ip route summary
→ pyats_ping_from_network_device: ping 10.1.1.2 repeat 5
```

Records current state: no BGP configured, routing table has 12 routes, peer IP is reachable.

### Step 3: Build RFC-Compliant Configuration

Based on RFC 7454 recommendations:

```
→ pyats_configure_device with config_commands:
```

```
ip prefix-list BOGONS seq 5 deny 0.0.0.0/8 le 32
ip prefix-list BOGONS seq 10 deny 10.0.0.0/8 le 32
ip prefix-list BOGONS seq 15 deny 127.0.0.0/8 le 32
ip prefix-list BOGONS seq 20 deny 169.254.0.0/16 le 32
ip prefix-list BOGONS seq 25 deny 172.16.0.0/12 le 32
ip prefix-list BOGONS seq 30 deny 192.0.2.0/24 le 32
ip prefix-list BOGONS seq 35 deny 192.168.0.0/16 le 32
ip prefix-list BOGONS seq 40 deny 224.0.0.0/4 le 32
ip prefix-list BOGONS seq 99 permit 0.0.0.0/0 le 24
!
ip prefix-list OUR-NETS seq 10 permit 203.0.113.0/24
!
route-map PEER-IN permit 10
 match ip address prefix-list BOGONS
 set local-preference 100
!
route-map PEER-OUT permit 10
 match ip address prefix-list OUR-NETS
!
router bgp 65001
 bgp log-neighbor-changes
 neighbor 10.1.1.2 remote-as 65002
 neighbor 10.1.1.2 description eBGP-to-ISP-RFC7454
 neighbor 10.1.1.2 password SecureKey123
 neighbor 10.1.1.2 ttl-security hops 1
 address-family ipv4 unicast
  neighbor 10.1.1.2 activate
  neighbor 10.1.1.2 route-map PEER-IN in
  neighbor 10.1.1.2 route-map PEER-OUT out
  neighbor 10.1.1.2 maximum-prefix 1000 80 restart 15
  neighbor 10.1.1.2 soft-reconfiguration inbound
```

### Step 4: Post-Change Verification

```
→ pyats_show_logging (check for BGP errors)
→ pyats_run_show_command: show ip bgp summary (verify peer state)
→ pyats_run_show_command: show ip bgp neighbors 10.1.1.2 (verify policy applied)
→ pyats_run_show_command: show ip route bgp (verify learned routes)
→ pyats_ping_from_network_device: ping 10.1.1.2 repeat 5
```

### Step 5: Document

```
Change Report:
  Applied RFC 7454-compliant BGP config for eBGP peer 10.1.1.2 (AS 65002)
  Security: MD5 auth + GTSM (TTL security) + bogon filtering
  Policy: prefix-list BOGONS (inbound), OUR-NETS (outbound)
  Limits: max-prefix 1000 with 80% warning, 15-min restart
  Result: Peer Established, receiving X prefixes
  RFC References: RFC 7454, RFC 4271, RFC 5082
```

## Skills Used

- **rfc-lookup** (RFC 7454 BGP security, RFC 4271 BGP-4 spec)
- **pyats-config-mgmt** (baseline → apply → verify → document)
- **pyats-routing** (BGP state analysis)
- **pyats-network** (underlying MCP tool calls)
