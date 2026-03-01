"""
OSPFv3 Protocol Constants
RFC 5340 - OSPF for IPv6
RFC 8362 - OSPFv3 LSA Extensibility
"""

# OSPF Version and Protocol
OSPFV3_VERSION = 3
OSPF_PROTOCOL_NUMBER = 89  # IP protocol number for OSPF (same as OSPFv2)

# IPv6 Multicast Addresses (RFC 5340 Section 2.1)
ALLSPFROUTERS_V6 = "ff02::5"  # All OSPF routers (link-local)
ALLDROUTERS_V6 = "ff02::6"    # All Designated Routers (link-local)

# OSPF Packet Types (RFC 5340 Section 4.2.1 - same as OSPFv2)
HELLO_PACKET = 1
DATABASE_DESCRIPTION = 2
LINK_STATE_REQUEST = 3
LINK_STATE_UPDATE = 4
LINK_STATE_ACK = 5

PACKET_TYPES = {
    1: "Hello",
    2: "Database Description",
    3: "Link State Request",
    4: "Link State Update",
    5: "Link State Acknowledgment"
}

# Neighbor States (RFC 5340 Section 4.2.3 - same as OSPFv2)
STATE_DOWN = 0
STATE_ATTEMPT = 1
STATE_INIT = 2
STATE_2WAY = 3
STATE_EXSTART = 4
STATE_EXCHANGE = 5
STATE_LOADING = 6
STATE_FULL = 7

STATE_NAMES = {
    0: "Down",
    1: "Attempt",
    2: "Init",
    3: "2-Way",
    4: "ExStart",
    5: "Exchange",
    6: "Loading",
    7: "Full"
}

# Neighbor Events (RFC 5340 - same as OSPFv2)
EVENT_HELLO_RECEIVED = "HelloReceived"
EVENT_START = "Start"
EVENT_2WAY_RECEIVED = "2-WayReceived"
EVENT_NEGOTIATION_DONE = "NegotiationDone"
EVENT_EXCHANGE_DONE = "ExchangeDone"
EVENT_BAD_LS_REQ = "BadLSReq"
EVENT_LOADING_DONE = "LoadingDone"
EVENT_ADJ_OK = "AdjOK?"
EVENT_SEQ_NUMBER_MISMATCH = "SeqNumberMismatch"
EVENT_1WAY = "1-Way"
EVENT_KILL_NBR = "KillNbr"
EVENT_INACTIVITY_TIMER = "InactivityTimer"
EVENT_LL_DOWN = "LLDown"

# LSA Types (RFC 5340 Section 4.4.3)
# Function codes
ROUTER_LSA = 0x2001
NETWORK_LSA = 0x2002
INTER_AREA_PREFIX_LSA = 0x2003
INTER_AREA_ROUTER_LSA = 0x2004
AS_EXTERNAL_LSA = 0x4005
GROUP_MEMBERSHIP_LSA = 0x2006  # Deprecated
TYPE_7_LSA = 0x2007            # NSSA
LINK_LSA = 0x0008
INTRA_AREA_PREFIX_LSA = 0x2009

# Alternative representation (LS Type field encoding)
# U-bit (0x8000): Handling of unknown LS type
# S2-bit (0x4000): Flooding scope - 0=link-local, 1=area
# S1-bit (0x2000): Flooding scope - 0=single area, 1=AS
LSA_TYPE_NAMES = {
    0x2001: "Router-LSA",
    0x2002: "Network-LSA",
    0x2003: "Inter-Area-Prefix-LSA",
    0x2004: "Inter-Area-Router-LSA",
    0x4005: "AS-External-LSA",
    0x2006: "Group-Membership-LSA",
    0x2007: "Type-7-LSA",
    0x0008: "Link-LSA",
    0x2009: "Intra-Area-Prefix-LSA"
}

# LSA Flooding Scope (from LS Type S2/S1 bits)
FLOODING_LINK_LOCAL = 0  # Link-local scope
FLOODING_AREA = 1        # Area flooding scope
FLOODING_AS = 2          # AS flooding scope
FLOODING_RESERVED = 3    # Reserved

# Router LSA Link Types (RFC 5340 Appendix A.4.3)
LINK_TYPE_PTP = 1           # Point-to-point connection
LINK_TYPE_TRANSIT = 2       # Transit network
LINK_TYPE_RESERVED = 3      # Reserved
LINK_TYPE_VIRTUAL = 4       # Virtual link

LINK_TYPE_NAMES = {
    1: "Point-to-point",
    2: "Transit network",
    3: "Reserved",
    4: "Virtual link"
}

# Router LSA Router Bits (Flags)
ROUTER_BIT_V = 0x01  # Virtual link endpoint
ROUTER_BIT_E = 0x02  # AS boundary router
ROUTER_BIT_B = 0x04  # Area border router

# Prefix Options (RFC 5340 Section A.4.1.1)
PREFIX_OPTION_NU = 0x01    # No Unicast
PREFIX_OPTION_LA = 0x02    # Local Address
PREFIX_OPTION_P = 0x08     # Propagate
PREFIX_OPTION_DN = 0x10    # Down bit (for VPN routes)

# Link LSA Flags (RFC 5340 Appendix A.4.9)
LINK_LSA_PRIORITY_MASK = 0xFF  # Router priority

# Options Field (RFC 5340 Section A.2) - 24 bits in OSPFv3
OPTION_V6 = 0x01       # V6-bit: IPv6 forwarding capability (always set)
OPTION_E = 0x02        # E-bit: External routing capability
OPTION_MC = 0x04       # MC-bit: Multicast capability
OPTION_N = 0x08        # N-bit: NSSA capability
OPTION_R = 0x10        # R-bit: Router bit
OPTION_DC = 0x20       # DC-bit: Demand circuits
OPTION_AF = 0x0100     # AF-bit: OSPFv3 Address Family (RFC 5838)
OPTION_L = 0x0200      # L-bit: Local address bit
OPTION_AT = 0x0400     # AT-bit: Authentication trailer

OPTION_NAMES = {
    0x01: "V6",
    0x02: "E",
    0x04: "MC",
    0x08: "N",
    0x10: "R",
    0x20: "DC",
    0x0100: "AF",
    0x0200: "L",
    0x0400: "AT"
}

# Network Types (same as OSPFv2)
NETWORK_TYPE_BROADCAST = "broadcast"
NETWORK_TYPE_NBMA = "nbma"
NETWORK_TYPE_PTP = "point-to-point"
NETWORK_TYPE_PTMP = "point-to-multipoint"
NETWORK_TYPE_VIRTUAL = "virtual-link"

# Default Timer Values (RFC 5340 Section 4.2)
DEFAULT_HELLO_INTERVAL = 10      # seconds
DEFAULT_DEAD_INTERVAL = 40       # seconds (4 * hello_interval)
DEFAULT_RXMT_INTERVAL = 5        # seconds
DEFAULT_INFTRA_DELAY = 1         # seconds
DEFAULT_WAIT_TIMER = 40          # seconds (= dead_interval)

# Administrative Distance
ADMIN_DISTANCE = 110

# Maximum Packet Size
MAX_PACKET_SIZE = 65535  # IPv6 can handle larger packets

# Database Description Flags (RFC 5340 Section A.3.3)
DD_FLAG_MS = 0x01    # Master/Slave bit
DD_FLAG_M = 0x02     # More bit
DD_FLAG_I = 0x04     # Init bit

DD_FLAG_NAMES = {
    0x01: "MS",
    0x02: "M",
    0x04: "I"
}

# LSA Header Size
LSA_HEADER_SIZE = 20  # bytes

# OSPF Packet Header Size
OSPF_HEADER_SIZE = 16  # bytes (no authentication in OSPFv3)

# Instance ID (RFC 5340 Section 2.4)
DEFAULT_INSTANCE_ID = 0  # Default instance

# Maximum Age
MAX_AGE = 3600  # seconds
MAX_AGE_DIFF = 900  # seconds

# LS Infinity
LS_INFINITY = 0xFFFFFF  # 16777215

# Initial Sequence Number
INITIAL_SEQ_NUM = 0x80000001
MAX_SEQ_NUM = 0x7FFFFFFF

# Prefix Length Encoding
IPV6_ADDRESS_LENGTH = 128  # bits
IPV6_ADDRESS_BYTES = 16    # bytes
