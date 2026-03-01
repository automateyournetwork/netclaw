"""
GRE (Generic Routing Encapsulation) Constants

RFC 2784 - Generic Routing Encapsulation (GRE)
RFC 2890 - Key and Sequence Number Extensions to GRE

GRE encapsulates packets of one protocol inside another protocol,
allowing routing protocols to traverse non-native networks.
"""

# =============================================================================
# IP Protocol Numbers
# =============================================================================

# GRE uses IP protocol number 47
IPPROTO_GRE = 47

# Other common protocol numbers for reference
IPPROTO_ICMP = 1
IPPROTO_TCP = 6
IPPROTO_UDP = 17
IPPROTO_IPV6 = 41
IPPROTO_OSPF = 89

# =============================================================================
# GRE Header Flags (RFC 2784, RFC 2890)
# =============================================================================

# Header flags are in the first 16 bits of the GRE header
# Format: C|R|K|S|s|Recur|A|Flags|Ver
#         0 1 2 3 4  5-7  8  9-12 13-15

# Checksum Present (bit 0) - RFC 2784
# If set, Checksum and Reserved1 fields are present (4 additional bytes)
GRE_FLAG_CHECKSUM = 0x8000  # 1000 0000 0000 0000

# Reserved (bit 1) - must be zero
GRE_FLAG_RESERVED = 0x4000  # 0100 0000 0000 0000

# Key Present (bit 2) - RFC 2890
# If set, Key field is present (4 additional bytes)
GRE_FLAG_KEY = 0x2000       # 0010 0000 0000 0000

# Sequence Number Present (bit 3) - RFC 2890
# If set, Sequence Number field is present (4 additional bytes)
GRE_FLAG_SEQUENCE = 0x1000  # 0001 0000 0000 0000

# Strict Source Route (bit 4) - deprecated, must be zero
GRE_FLAG_STRICT = 0x0800    # 0000 1000 0000 0000

# Recursion Control (bits 5-7) - deprecated, must be zero
GRE_RECUR_MASK = 0x0700     # 0000 0111 0000 0000

# Acknowledgment Present (bit 8) - used in PPTP, not standard GRE
GRE_FLAG_ACK = 0x0080       # 0000 0000 1000 0000

# Flags (bits 9-12) - reserved, must be zero
GRE_FLAGS_MASK = 0x0078     # 0000 0000 0111 1000

# Version (bits 13-15) - must be 0 for standard GRE, 1 for PPTP
GRE_VERSION_MASK = 0x0007   # 0000 0000 0000 0111
GRE_VERSION_0 = 0           # Standard GRE (RFC 2784)
GRE_VERSION_1 = 1           # Enhanced GRE (PPTP - RFC 2637)

# =============================================================================
# Protocol Types (Ethertypes) - Encapsulated Payload Protocol
# =============================================================================

# Common protocol types that can be encapsulated in GRE
PROTO_IPV4 = 0x0800         # Internet Protocol version 4
PROTO_IPV6 = 0x86DD         # Internet Protocol version 6
PROTO_ARP = 0x0806          # Address Resolution Protocol
PROTO_RARP = 0x8035         # Reverse ARP
PROTO_MPLS_UNICAST = 0x8847 # MPLS Unicast
PROTO_MPLS_MULTICAST = 0x8848  # MPLS Multicast
PROTO_PPP = 0x880B          # Point-to-Point Protocol
PROTO_ETHERNET = 0x6558     # Transparent Ethernet Bridging (TEB)
PROTO_ERSPAN_TYPE2 = 0x88BE # ERSPAN Type II
PROTO_ERSPAN_TYPE3 = 0x22EB # ERSPAN Type III

# Protocol type name mapping for display
PROTOCOL_NAMES = {
    PROTO_IPV4: "IPv4",
    PROTO_IPV6: "IPv6",
    PROTO_ARP: "ARP",
    PROTO_RARP: "RARP",
    PROTO_MPLS_UNICAST: "MPLS-Unicast",
    PROTO_MPLS_MULTICAST: "MPLS-Multicast",
    PROTO_PPP: "PPP",
    PROTO_ETHERNET: "Ethernet",
    PROTO_ERSPAN_TYPE2: "ERSPAN-II",
    PROTO_ERSPAN_TYPE3: "ERSPAN-III",
}

# =============================================================================
# GRE Header Sizes
# =============================================================================

# Minimum GRE header: flags/version (2 bytes) + protocol type (2 bytes)
GRE_HEADER_MIN = 4

# Checksum + Reserved1 field size (when C bit is set)
GRE_CHECKSUM_SIZE = 4

# Key field size (when K bit is set)
GRE_KEY_SIZE = 4

# Sequence number field size (when S bit is set)
GRE_SEQUENCE_SIZE = 4

# Maximum GRE header size (all optional fields present)
GRE_HEADER_MAX = GRE_HEADER_MIN + GRE_CHECKSUM_SIZE + GRE_KEY_SIZE + GRE_SEQUENCE_SIZE  # 16 bytes

# IP header size (for MTU calculations)
IPV4_HEADER_MIN = 20
IPV6_HEADER_MIN = 40

# =============================================================================
# MTU and Overhead Constants
# =============================================================================

# Standard Ethernet MTU
DEFAULT_MTU = 1500

# GRE overhead calculations
GRE_OVERHEAD_MIN = IPV4_HEADER_MIN + GRE_HEADER_MIN  # 24 bytes (IPv4 + basic GRE)
GRE_OVERHEAD_MAX = IPV4_HEADER_MIN + GRE_HEADER_MAX  # 36 bytes (IPv4 + full GRE)

# Recommended GRE tunnel MTU (conservative, allows for all options)
GRE_TUNNEL_MTU = DEFAULT_MTU - GRE_OVERHEAD_MAX  # 1464 bytes

# Safe MTU for GRE over various transports (accounts for IPsec, etc.)
GRE_SAFE_MTU = 1400

# =============================================================================
# Tunnel Configuration Defaults
# =============================================================================

# Default TTL for outer IP header
DEFAULT_TTL = 255

# Default TOS/DSCP for GRE packets (CS6 - Network Control)
DEFAULT_TOS = 0xC0  # DSCP 48 (CS6) << 2 = 192

# Keepalive defaults
DEFAULT_KEEPALIVE_INTERVAL = 10  # seconds
DEFAULT_KEEPALIVE_RETRIES = 3

# Tunnel states
TUNNEL_STATE_DOWN = "down"
TUNNEL_STATE_UP = "up"
TUNNEL_STATE_ADMIN_DOWN = "admin_down"
TUNNEL_STATE_ESTABLISHING = "establishing"
TUNNEL_STATE_FAILED = "failed"

# =============================================================================
# GRE Tunnel Modes
# =============================================================================

# Tunnel encapsulation modes
MODE_GRE_IPV4 = "gre"           # GRE over IPv4
MODE_GRE_IPV6 = "ip6gre"        # GRE over IPv6
MODE_GRE_TAP = "gretap"         # GRE with Ethernet (L2)
MODE_GRE_TAP_IPV6 = "ip6gretap" # GRE with Ethernet over IPv6

# Tunnel direction modes
DIRECTION_BIDIRECTIONAL = "bidirectional"
DIRECTION_INBOUND_ONLY = "inbound"
DIRECTION_OUTBOUND_ONLY = "outbound"

# =============================================================================
# Error Codes
# =============================================================================

class GREError:
    """GRE-specific error codes"""
    SUCCESS = 0
    INVALID_HEADER = 1
    UNSUPPORTED_VERSION = 2
    CHECKSUM_MISMATCH = 3
    INVALID_PROTOCOL = 4
    TUNNEL_NOT_FOUND = 5
    TUNNEL_EXISTS = 6
    SOCKET_ERROR = 7
    PERMISSION_DENIED = 8
    INVALID_ENDPOINT = 9
    MTU_EXCEEDED = 10
    KEY_MISMATCH = 11


# Error messages
ERROR_MESSAGES = {
    GREError.SUCCESS: "Success",
    GREError.INVALID_HEADER: "Invalid GRE header",
    GREError.UNSUPPORTED_VERSION: "Unsupported GRE version",
    GREError.CHECKSUM_MISMATCH: "GRE checksum mismatch",
    GREError.INVALID_PROTOCOL: "Invalid/unsupported protocol type",
    GREError.TUNNEL_NOT_FOUND: "Tunnel not found",
    GREError.TUNNEL_EXISTS: "Tunnel already exists",
    GREError.SOCKET_ERROR: "Socket operation failed",
    GREError.PERMISSION_DENIED: "Permission denied (root required)",
    GREError.INVALID_ENDPOINT: "Invalid tunnel endpoint",
    GREError.MTU_EXCEEDED: "Packet exceeds tunnel MTU",
    GREError.KEY_MISMATCH: "GRE key mismatch",
}
