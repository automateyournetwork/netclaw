"""Cisco Design Reference MCP Tool — lightweight knowledge base for network design best practices.

Sources: Cisco SAFE Architecture, Campus LAN Design Guide, IOS-XE Hardening Guide,
CIS Cisco IOS Benchmark, Cisco Validated Designs (CVD).

This is NOT a full MCP server — it's a reference tool added to nautobot-mcp-v2 that the agent
can query when building golden config templates, compliance rules, or hardening recommendations.
"""

# Each section maps to a compliance feature and contains:
# - best_practices: what Cisco recommends
# - config_example: IOS-XE config snippet showing the recommendation
# - rationale: why this matters
# - rfc: relevant RFC if applicable
# - match_config: regex pattern for golden config compliance rule

DESIGN_REFERENCE = {
    "aaa": {
        "title": "Authentication, Authorization, and Accounting",
        "best_practices": [
            "Enable AAA new-model for centralized authentication",
            "Use TACACS+ for device administration (provides command authorization)",
            "Configure local fallback authentication in case TACACS+ is unreachable",
            "Enable login authentication on all VTY and console lines",
            "Enable exec authorization to control privilege levels",
            "Enable command accounting for audit trail",
            "Set failed-login lockout after 5 attempts",
        ],
        "config_example": """\
aaa new-model
!
aaa authentication login default group tacacs+ local
aaa authentication login CONSOLE local
aaa authentication enable default group tacacs+ enable
aaa authorization exec default group tacacs+ local
aaa authorization commands 15 default group tacacs+ local
aaa accounting exec default start-stop group tacacs+
aaa accounting commands 15 default start-stop group tacacs+
!
tacacs server TACACS-PRIMARY
 address ipv4 {tacacs_server_primary}
 key {tacacs_key}
 timeout 3
tacacs server TACACS-SECONDARY
 address ipv4 {tacacs_server_secondary}
 key {tacacs_key}
 timeout 3
!
aaa group server tacacs+ TACACS-GROUP
 server name TACACS-PRIMARY
 server name TACACS-SECONDARY
!
login block-for 120 attempts 5 within 60""",
        "rationale": "Centralized AAA prevents credential sprawl, enables audit trails, and allows immediate revocation of access. Local fallback ensures access during server outages. TACACS+ preferred over RADIUS for device admin because it encrypts the full payload and supports per-command authorization.",
        "rfc": "RFC 8907 (TACACS+)",
        "match_config": "^aaa ",
        "severity": "critical",
    },
    "ntp": {
        "title": "Network Time Protocol",
        "best_practices": [
            "Configure at least 2 NTP servers for redundancy",
            "Use NTP authentication (MD5 or SHA) to prevent time poisoning",
            "Restrict NTP access with access-group (peer, serve, query-only)",
            "Use a trusted internal NTP source or well-known public servers",
            "Set clock timezone and summer-time",
            "Source NTP from management interface/VRF",
        ],
        "config_example": """\
clock timezone {timezone} {utc_offset_hours} {utc_offset_minutes}
clock summer-time {summer_time_zone} recurring
!
ntp authentication-key 1 md5 {ntp_auth_key}
ntp trusted-key 1
ntp authenticate
ntp source {ntp_source_interface}
ntp access-group peer 10
ntp server vrf {mgmt_vrf} {ntp_server_1} key 1 prefer
ntp server vrf {mgmt_vrf} {ntp_server_2} key 1""",
        "rationale": "Accurate time is critical for log correlation, certificate validation, and troubleshooting. NTP authentication prevents man-in-the-middle attacks that could desynchronize clocks and break time-based security controls (TOTP, certificate expiry, log sequencing).",
        "rfc": "RFC 5905 (NTPv4)",
        "match_config": "^ntp ",
        "severity": "high",
    },
    "logging": {
        "title": "System Logging (Syslog)",
        "best_practices": [
            "Send logs to a centralized syslog server",
            "Set logging trap level to informational (6) minimum for security events",
            "Include timestamps with millisecond precision",
            "Source logging from management interface/VRF",
            "Configure logging buffered for local retention",
            "Disable logging to console in production (performance impact)",
            "Enable login success/failure logging",
        ],
        "config_example": """\
no logging console
logging buffered 65536 informational
logging trap informational
logging source-interface {mgmt_interface} vrf {mgmt_vrf}
logging host {syslog_server} vrf {mgmt_vrf}
!
logging origin-id hostname
logging facility local6
!
login on-success log
login on-failure log every 3""",
        "rationale": "Centralized logging enables incident detection, forensics, and compliance auditing. Millisecond timestamps allow correlation across devices. Disabling console logging prevents CPU impact from high-volume events. Buffered logging provides local retention when the syslog server is unreachable.",
        "rfc": "RFC 5424 (Syslog Protocol), RFC 5425 (TLS Transport for Syslog)",
        "match_config": "^logging ",
        "severity": "high",
    },
    "snmp": {
        "title": "Simple Network Management Protocol",
        "best_practices": [
            "Use SNMPv3 with authPriv (authentication + encryption) where possible",
            "If SNMPv2c is required, use non-default community strings",
            "Restrict SNMP access with ACLs to management stations only",
            "Never use 'public' or 'private' as community strings in production",
            "Disable SNMP write access unless specifically required",
            "Configure SNMP traps/informs to a central NMS",
            "Set snmp-server contact and location for asset management",
        ],
        "config_example": """\
! SNMPv3 (preferred)
snmp-server group MONITORING v3 priv read READONLY
snmp-server user {snmp_user} MONITORING v3 auth sha {snmp_auth_key} priv aes 128 {snmp_priv_key}
snmp-server view READONLY iso included
!
! SNMPv2c (if v3 not supported by NMS)
access-list 99 permit {nms_network} {nms_wildcard}
snmp-server community {snmp_ro_community} RO 99
!
snmp-server location {location}
snmp-server contact {contact}
snmp-server enable traps snmp authentication linkdown linkup coldstart warmstart
snmp-server enable traps config
snmp-server enable traps syslog
snmp-server host {snmp_trap_host} version 2c {snmp_ro_community}""",
        "rationale": "SNMP communities are sent in cleartext — ACLs limit exposure. SNMPv3 provides authentication and encryption. Write communities allow remote config changes and should be avoided. Traps enable proactive monitoring of link state, config changes, and security events.",
        "rfc": "RFC 3414 (SNMPv3 USM), RFC 3826 (AES for SNMPv3)",
        "match_config": "^snmp-server ",
        "severity": "high",
    },
    "ssh": {
        "title": "Secure Shell Access",
        "best_practices": [
            "Use SSH version 2 only (v1 has known vulnerabilities)",
            "Set SSH timeout and authentication retries",
            "Source SSH from management interface",
            "Disable Telnet on all VTY lines",
            "Configure RSA key of 2048 bits or greater",
            "Enable SCP server for secure file transfers",
        ],
        "config_example": """\
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3
ip ssh source-interface {mgmt_interface}
ip scp server enable
!
crypto key generate rsa modulus 2048""",
        "rationale": "SSH v1 has cryptographic weaknesses. SSH v2 provides strong encryption and host authentication. Sourcing from the management interface ensures SSH traffic stays in the management VRF. SCP replaces insecure TFTP for file transfers.",
        "rfc": "RFC 4253 (SSH Transport Layer), RFC 4252 (SSH Authentication)",
        "match_config": "^ip ssh ",
        "severity": "critical",
    },
    "vty_lines": {
        "title": "Virtual Terminal Line Security",
        "best_practices": [
            "Restrict transport input to SSH only (no telnet)",
            "Apply ACL to VTY lines limiting source addresses",
            "Set exec-timeout to prevent idle sessions (5-15 minutes recommended)",
            "Enable login authentication via AAA or local",
            "Configure consistent settings across all VTY lines (0-4 and 5-15)",
        ],
        "config_example": """\
line con 0
 exec-timeout 15 0
 logging synchronous
 login authentication CONSOLE
!
line vty 0 4
 exec-timeout 15 0
 access-class {vty_acl} in
 login authentication default
 transport input ssh
 transport output ssh
line vty 5 15
 exec-timeout 15 0
 access-class {vty_acl} in
 login authentication default
 transport input ssh
 transport output ssh""",
        "rationale": "VTY lines are the remote access entry point. Unrestricted access allows brute-force attacks. Exec-timeout prevents abandoned sessions from being hijacked. ACLs limit which hosts can attempt connections. SSH-only transport eliminates cleartext credential exposure.",
        "rfc": None,
        "match_config": "^line vty ",
        "severity": "critical",
    },
    "spanning_tree": {
        "title": "Spanning Tree Protocol",
        "best_practices": [
            "Use Rapid PVST+ or MST (not legacy PVST+)",
            "Enable BPDU Guard on all access ports",
            "Enable Root Guard on ports that should never become root",
            "Enable Loop Guard on non-designated ports",
            "Configure PortFast on access ports only",
            "Enable spanning-tree logging for topology change visibility",
            "Set bridge priority explicitly on root/secondary root switches",
        ],
        "config_example": """\
spanning-tree mode rapid-pvst
spanning-tree logging
spanning-tree extend system-id
spanning-tree vlan 1-4094 priority {stp_priority}
!
! On access ports:
interface range {access_port_range}
 spanning-tree portfast
 spanning-tree bpduguard enable
!
! On uplinks where root should not move:
interface range {uplink_range}
 spanning-tree guard root""",
        "rationale": "Rapid PVST+ provides sub-second convergence. BPDU Guard prevents rogue switches from disrupting the topology. Root Guard prevents unauthorized root bridge elections. PortFast eliminates the 30-second STP delay on access ports but must be paired with BPDU Guard for safety.",
        "rfc": "IEEE 802.1w (RSTP), IEEE 802.1D-2004",
        "match_config": "^spanning-tree ",
        "severity": "medium",
    },
    "vtp": {
        "title": "VLAN Trunking Protocol",
        "best_practices": [
            "Use VTP transparent or off mode in production",
            "Never use VTP server/client mode without understanding the blast radius",
            "VTP transparent allows local VLAN management without propagation risk",
            "If VTP is used, set a VTP password and use version 3",
        ],
        "config_example": """\
vtp mode transparent""",
        "rationale": "VTP server mode can propagate VLAN deletions across the entire network from a single misconfigured switch. Transparent mode gives local control without propagation risk. This is the single most common cause of network-wide outages in campus environments.",
        "rfc": None,
        "match_config": "^vtp ",
        "severity": "medium",
    },
    "interfaces_l2_access": {
        "title": "Layer 2 Access Port Security",
        "best_practices": [
            "Assign all access ports to a specific VLAN (never leave on VLAN 1)",
            "Enable PortFast on access ports",
            "Enable BPDU Guard on access ports",
            "Shut down unused ports",
            "Move unused ports to a black-hole VLAN",
            "Set port descriptions for documentation",
            "Consider port-security or 802.1X for endpoint authentication",
        ],
        "config_example": """\
interface {interface_name}
 description {description}
 switchport access vlan {access_vlan}
 switchport mode access
 spanning-tree portfast
 spanning-tree bpduguard enable
 load-interval 30
!
! Unused port template:
interface {unused_interface}
 description NOT IN USE
 switchport access vlan {blackhole_vlan}
 switchport mode access
 shutdown""",
        "rationale": "VLAN 1 is the default and carries control plane traffic (CDP, VTP, DTP). Moving access ports off VLAN 1 reduces attack surface. Shutting unused ports prevents unauthorized access. BPDU Guard prevents rogue switches on access ports.",
        "rfc": "IEEE 802.1Q (VLAN Tagging)",
        "match_config": "^interface ",
        "severity": "medium",
    },
    "interfaces_l2_trunk": {
        "title": "Layer 2 Trunk Port Security",
        "best_practices": [
            "Explicitly configure trunk mode (don't rely on DTP negotiation)",
            "Prune allowed VLANs to only what's needed on each trunk",
            "Set native VLAN to something other than VLAN 1",
            "Disable DTP negotiation on trunk ports",
            "Use descriptions indicating the far-end device and port",
        ],
        "config_example": """\
interface {interface_name}
 description {description}
 switchport trunk allowed vlan {allowed_vlans}
 switchport trunk native vlan {native_vlan}
 switchport mode trunk
 switchport nonegotiate""",
        "rationale": "DTP negotiation can be exploited to form unauthorized trunks (VLAN hopping). Pruning allowed VLANs limits broadcast domain scope and reduces the blast radius of a compromised VLAN. Non-default native VLAN prevents double-tagging attacks.",
        "rfc": "IEEE 802.1Q",
        "match_config": "^interface ",
        "severity": "medium",
    },
    "management_plane": {
        "title": "Management Plane Hardening",
        "best_practices": [
            "Use a dedicated management VRF",
            "Source all management traffic (SSH, SNMP, syslog, NTP) from management interface",
            "Disable HTTP server if not needed, or restrict with ACL",
            "Enable HTTPS (ip http secure-server) if web UI is required",
            "Disable unused services (ip finger, ip bootp server, service pad)",
            "Configure service password-encryption",
            "Set enable secret (not enable password) with type 9 hash",
            "Configure login banner with legal notice",
        ],
        "config_example": """\
no service pad
service timestamps debug datetime msec
service timestamps log datetime msec
service password-encryption
!
no ip bootp server
no ip finger
no ip source-route
no ip http server
ip http secure-server
ip http authentication local
ip http access-class {http_acl}
!
vrf definition {mgmt_vrf}
 address-family ipv4
 exit-address-family
!
ip route vrf {mgmt_vrf} 0.0.0.0 0.0.0.0 {mgmt_gateway}
!
banner login ^
{banner_text}
^""",
        "rationale": "The management plane is the highest-value target on a network device. VRF isolation prevents management traffic from mixing with data plane traffic. Disabling unused services reduces attack surface. Password encryption prevents casual credential exposure in config files.",
        "rfc": "RFC 2827 (BCP 38 - Network Ingress Filtering)",
        "match_config": "^(no )?service |^ip http |^banner ",
        "severity": "high",
    },
    "dhcp_snooping": {
        "title": "DHCP Snooping",
        "best_practices": [
            "Enable DHCP snooping globally and per-VLAN",
            "Trust only uplink/trunk ports (where legitimate DHCP server resides)",
            "Untrusted ports (access) will drop DHCP server messages",
            "Pairs with Dynamic ARP Inspection (DAI) and IP Source Guard",
        ],
        "config_example": """\
ip dhcp snooping
ip dhcp snooping vlan {vlan_list}
!
interface {trusted_uplink}
 ip dhcp snooping trust
!
! Access ports are untrusted by default""",
        "rationale": "DHCP snooping prevents rogue DHCP servers from distributing incorrect IP configuration or performing man-in-the-middle attacks. The snooping database also enables DAI and IP Source Guard for additional L2 security.",
        "rfc": None,
        "match_config": "^ip dhcp snooping",
        "severity": "medium",
    },
    "control_plane_policing": {
        "title": "Control Plane Policing (CoPP)",
        "best_practices": [
            "Apply a system-cpp-policy to rate-limit control plane traffic",
            "Protect against DoS attacks targeting the switch CPU",
            "IOS-XE 3850 uses built-in system-cpp-policy (not user-configurable on older code)",
            "Monitor CoPP drops via 'show platform hardware fed switch active qos queue stats internal cpu policer'",
        ],
        "config_example": """\
control-plane
 service-policy input system-cpp-policy""",
        "rationale": "The switch CPU is a shared resource. Without CoPP, a flood of ARP, ICMP, or routing protocol packets can overwhelm the CPU and cause a denial of service for legitimate management and control plane traffic.",
        "rfc": None,
        "match_config": "^control-plane",
        "severity": "medium",
    },
}


def get_reference(feature: str) -> dict | None:
    """Get design reference for a specific feature."""
    return DESIGN_REFERENCE.get(feature)


def get_all_features() -> list[str]:
    """Get list of all available design reference features."""
    return list(DESIGN_REFERENCE.keys())


def get_summary() -> list[dict]:
    """Get a summary of all design references with title and severity."""
    return [
        {
            "feature": k,
            "title": v["title"],
            "severity": v["severity"],
            "rfc": v.get("rfc"),
            "match_config": v["match_config"],
        }
        for k, v in DESIGN_REFERENCE.items()
    ]
