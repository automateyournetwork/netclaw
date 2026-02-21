---
name: pyats-security
description: "Network security audit - ACLs, AAA, control plane policing, management plane hardening, encryption, port security, and CIS benchmark checks"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Network Security Audit

Systematic security assessment for Cisco IOS-XE devices following industry best practices and CIS benchmarks.

## When to Use

- Security posture assessment for compliance (SOC2, PCI-DSS, NIST, CIS)
- Pre-deployment security review
- Incident response — checking for unauthorized access or configuration
- Hardening audit for new devices
- Periodic security validation

## Security Audit Procedure

### Step 1: Pull Running Configuration

Always start by capturing the full running config for analysis:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_running_config '{"device_name":"R1"}'
```

Scan the full config for the checks below.

### Step 2: Management Plane Hardening

**Check these items in the running config:**

| Check | What to Look For | Finding If Missing |
|-------|------------------|--------------------|
| SSH version | `ip ssh version 2` | CRITICAL: SSHv1 vulnerable to MITM |
| Telnet disabled | No `transport input telnet` on VTY lines | CRITICAL: Telnet sends cleartext credentials |
| VTY ACL | `access-class` on VTY lines | HIGH: Unrestricted management access |
| Console timeout | `exec-timeout` on console (not 0 0) | MEDIUM: Unattended console sessions |
| VTY timeout | `exec-timeout` on VTY lines (not 0 0) | MEDIUM: Stale management sessions |
| Password encryption | `service password-encryption` | MEDIUM: Type 0 passwords visible |
| Enable secret | `enable secret` (not `enable password`) | HIGH: Enable password uses weak hash |
| Login banner | `banner login` or `banner motd` | LOW: Legal/compliance requirement |
| HTTP server disabled | `no ip http server` | MEDIUM: Unnecessary attack surface |
| HTTPS server | `ip http secure-server` if web management needed | MEDIUM: Use HTTPS not HTTP |
| Aux port disabled | `no exec` on aux line | LOW: Unused port open |

### Step 3: AAA Configuration

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show aaa servers"}'
```

**AAA checks in running config:**
- `aaa new-model` enabled
- `aaa authentication login` configured (not just local)
- `aaa authorization exec` configured
- `aaa accounting` configured for commands and connections
- TACACS+ or RADIUS server defined with encryption
- Local fallback account exists (in case AAA server unreachable)
- `aaa authentication enable` uses `enable secret` not `enable password`

### Step 4: Access Control Lists

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip access-lists"}'
```

**ACL analysis:**
- Check hit counts — ACEs with 0 matches may be unnecessary or misplaced
- Look for overly permissive rules (`permit ip any any`)
- Verify explicit deny at the end with logging (`deny ip any any log`)
- Check ACL is applied to the correct interface and direction
- Verify VTY access-class restricts management to known networks
- Look for ACLs referenced in route-maps, NAT, or other features

### Step 5: Control Plane Policing (CoPP)

Check in running config for:
- `control-plane` section with service-policy
- CoPP policy-map classifying and rate-limiting traffic to the CPU
- Protection against: ICMP floods, TTL-expired floods, fragmentation attacks, ARP storms

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show policy-map control-plane"}'
```

### Step 6: Routing Protocol Security

**OSPF authentication:**
- Check for `ip ospf authentication message-digest` on interfaces
- Or area-level: `area X authentication message-digest`
- Verify `ip ospf message-digest-key` is configured

**BGP security:**
- `neighbor X password` (MD5 authentication)
- `neighbor X ttl-security hops N` (GTSM — Generalized TTL Security Mechanism)
- `neighbor X prefix-list` or `neighbor X maximum-prefix` (prefix limits)
- Check for bogon filtering on eBGP peers

**EIGRP authentication:**
- Named mode: `af-interface` with `authentication mode md5` and `authentication key-chain`
- Classic mode: `ip authentication mode eigrp` and `ip authentication key-chain eigrp`

### Step 7: Infrastructure Security

Check in running config:

| Feature | Config | Purpose |
|---------|--------|---------|
| uRPF | `ip verify unicast source reachable-via rx` | Anti-spoofing |
| TCP keepalives | `service tcp-keepalives-in`, `service tcp-keepalives-out` | Dead session cleanup |
| CDP restricted | `no cdp enable` on external interfaces | Information leak prevention |
| LLDP restricted | `no lldp transmit` / `no lldp receive` on external | Information leak prevention |
| IP source routing disabled | `no ip source-route` | Prevent source-routed attacks |
| Directed broadcast disabled | `no ip directed-broadcast` per interface | Smurf attack prevention |
| ICMP redirects disabled | `no ip redirects` per interface | MITM prevention |
| Proxy ARP disabled | `no ip proxy-arp` on external interfaces | ARP spoofing prevention |
| Gratuitous ARP | `no ip gratuitous-arps` | ARP cache poisoning prevention |
| IP unreachables limited | `no ip unreachables` on external | Reconnaissance prevention |
| Timestamps | `service timestamps log datetime msec localtime` | Forensics |
| Logging buffer | `logging buffered` with adequate size | Event capture |
| Remote logging | `logging host X.X.X.X` | Centralized log collection |

### Step 8: Encryption & Credentials

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show crypto key mypubkey rsa"}'
```

**Check:**
- RSA key size >= 2048 bits (CRITICAL if < 1024)
- SSH version 2 only
- No Type 0 (cleartext) passwords in running config
- Enable secret uses Type 8 or Type 9 (scrypt) if available
- SNMP community strings are not "public" or "private"
- SNMPv3 preferred over v2c

### Step 9: SNMP Security

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show snmp"}'
```

**Checks:**
- No default community strings (public, private, cisco)
- RO communities have ACL restricting source
- RW communities have ACL restricting source (or don't exist at all)
- SNMPv3 with authPriv preferred
- SNMP traps configured to central monitoring

## Security Report Format

```
Device: R1 | IOS-XE 17.x.x
Security Audit Date: YYYY-MM-DD

CRITICAL FINDINGS (Fix Immediately):
  1. [C-001] SSHv1 enabled — upgrade to SSH version 2 only
  2. [C-002] No VTY access-class — management plane exposed

HIGH FINDINGS (Fix This Week):
  3. [H-001] No OSPF authentication on Gi1 — route injection risk
  4. [H-002] SNMP community 'public' with no ACL

MEDIUM FINDINGS (Fix This Month):
  5. [M-001] No CoPP policy — CPU vulnerable to floods
  6. [M-002] HTTP server enabled — disable or restrict

LOW / INFORMATIONAL:
  7. [L-001] No login banner configured
  8. [I-001] CDP enabled globally (acceptable on internal interfaces)

Summary: 2 Critical | 2 High | 2 Medium | 2 Low
```

## ISE Integration (MISSION02 Enhancement)

When ISE is available ($ISE_MCP_SCRIPT is set), extend the security audit with identity verification:

### Verify Device is Registered as NAD

Check that the device is registered in ISE as a Network Access Device:

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" network_devices '{}'
```

**Flags:**
- Device not registered as NAD → CRITICAL: Not participating in ISE enforcement
- Device registered but no RADIUS/TACACS config on device → HIGH: ISE configured but device not using it

### Check Active Sessions on Device

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" active_sessions '{}'
```

Filter sessions for this device's IP to see authenticated endpoints.

## NVD CVE Vulnerability Scan

After Step 1 (show version), extract the IOS-XE version and scan for known vulnerabilities:

```bash
python3 $MCP_CALL "npx -y nvd-cve-mcp-server" search_cves '{"keyword":"Cisco IOS XE 17.9.4","resultsPerPage":10}'
```

**For each CVE found:**
1. Check CVSS score (flag CVSS >= 7.0)
2. Cross-reference running config for exposure (e.g., CVE requires HTTP server → check if `ip http server` is configured)
3. Produce exposure correlation: CVE + running-config = actual risk

**Severity mapping:**
- CVSS >= 9.0 → CRITICAL
- CVSS >= 7.0 → HIGH
- CVSS >= 4.0 → MEDIUM
- CVSS < 4.0 → LOW

## Fleet-Wide Security Audit (pCall)

Run the full 9-step audit on ALL devices simultaneously using multiple exec commands. Aggregate findings across the fleet and sort by severity for prioritized remediation.

## GAIT Audit Trail

Record the security audit in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"Security audit on R1: 2 CRITICAL (no enable secret, telnet enabled), 2 HIGH, 2 MEDIUM, 2 LOW findings.","artifacts":[]}}'
```
