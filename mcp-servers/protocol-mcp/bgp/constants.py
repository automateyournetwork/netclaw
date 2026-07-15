"""
BGP Protocol Constants (RFC 4271, RFC 4456, RFC 1997, RFC 4760, RFC 5492)

This module contains all BGP protocol constants including message types,
FSM states, path attribute types, error codes, and well-known values.
"""

# Protocol Version and Transport
BGP_VERSION = 4
BGP_PORT = 179
BGP_HEADER_SIZE = 19
BGP_MAX_MESSAGE_SIZE = 4096
BGP_MARKER = b'\xff' * 16

# Message Types (RFC 4271 Section 4.1)
MSG_OPEN = 1
MSG_UPDATE = 2
MSG_NOTIFICATION = 3
MSG_KEEPALIVE = 4
MSG_ROUTE_REFRESH = 5  # RFC 2918

MESSAGE_TYPE_NAMES = {
    MSG_OPEN: "OPEN",
    MSG_UPDATE: "UPDATE",
    MSG_NOTIFICATION: "NOTIFICATION",
    MSG_KEEPALIVE: "KEEPALIVE",
    MSG_ROUTE_REFRESH: "ROUTE-REFRESH"
}

# FSM States (RFC 4271 Section 8.2.2)
STATE_IDLE = 0
STATE_CONNECT = 1
STATE_ACTIVE = 2
STATE_OPENSENT = 3
STATE_OPENCONFIRM = 4
STATE_ESTABLISHED = 5

FSM_STATE_NAMES = {
    STATE_IDLE: "Idle",
    STATE_CONNECT: "Connect",
    STATE_ACTIVE: "Active",
    STATE_OPENSENT: "OpenSent",
    STATE_OPENCONFIRM: "OpenConfirm",
    STATE_ESTABLISHED: "Established"
}

# Default Timer Values (seconds)
DEFAULT_HOLD_TIME = 90
DEFAULT_KEEPALIVE_TIME = 30  # HoldTime / 3
DEFAULT_CONNECT_RETRY_TIME = 120

# Minimum Hold Time (RFC 4271 Section 4.2)
MIN_HOLD_TIME = 3  # Must be 0 or >= 3

# Path Attribute Type Codes (RFC 4271 Section 5)
ATTR_ORIGIN = 1
ATTR_AS_PATH = 2
ATTR_NEXT_HOP = 3
ATTR_MED = 4
ATTR_LOCAL_PREF = 5
ATTR_ATOMIC_AGGREGATE = 6
ATTR_AGGREGATOR = 7
ATTR_COMMUNITIES = 8  # RFC 1997
ATTR_ORIGINATOR_ID = 9  # RFC 4456
ATTR_CLUSTER_LIST = 10  # RFC 4456
ATTR_MP_REACH_NLRI = 14  # RFC 4760
ATTR_MP_UNREACH_NLRI = 15  # RFC 4760
ATTR_EXTENDED_COMMUNITIES = 16  # RFC 4360
ATTR_AS4_PATH = 17  # RFC 6793
ATTR_AS4_AGGREGATOR = 18  # RFC 6793
ATTR_NETCLAW_MESH_PEERS = 253  # NetClaw mesh peer exchange (experimental range)

ATTR_TYPE_NAMES = {
    ATTR_ORIGIN: "ORIGIN",
    ATTR_AS_PATH: "AS_PATH",
    ATTR_NEXT_HOP: "NEXT_HOP",
    ATTR_MED: "MULTI_EXIT_DISC",
    ATTR_LOCAL_PREF: "LOCAL_PREF",
    ATTR_ATOMIC_AGGREGATE: "ATOMIC_AGGREGATE",
    ATTR_AGGREGATOR: "AGGREGATOR",
    ATTR_COMMUNITIES: "COMMUNITIES",
    ATTR_ORIGINATOR_ID: "ORIGINATOR_ID",
    ATTR_CLUSTER_LIST: "CLUSTER_LIST",
    ATTR_MP_REACH_NLRI: "MP_REACH_NLRI",
    ATTR_MP_UNREACH_NLRI: "MP_UNREACH_NLRI",
    ATTR_EXTENDED_COMMUNITIES: "EXTENDED_COMMUNITIES",
    ATTR_AS4_PATH: "AS4_PATH",
    ATTR_AS4_AGGREGATOR: "AS4_AGGREGATOR",
    ATTR_NETCLAW_MESH_PEERS: "NETCLAW_MESH_PEERS"
}

# NetClaw mesh directory marker prefix (reserved multicast, won't clash with real routes)
MESH_DIRECTORY_PREFIX = "239.255.255.0/28"

# Path Attribute Flags (RFC 4271 Section 5)
ATTR_FLAG_OPTIONAL = 0x80  # Bit 0
ATTR_FLAG_TRANSITIVE = 0x40  # Bit 1
ATTR_FLAG_PARTIAL = 0x20  # Bit 2
ATTR_FLAG_EXTENDED = 0x10  # Bit 3 (Extended Length)

# Well-Known Mandatory: Optional=0, Transitive=1
# Well-Known Discretionary: Optional=0, Transitive=1
# Optional Transitive: Optional=1, Transitive=1
# Optional Non-Transitive: Optional=1, Transitive=0

# ORIGIN Values (RFC 4271 Section 5.1.1)
ORIGIN_IGP = 0
ORIGIN_EGP = 1
ORIGIN_INCOMPLETE = 2

ORIGIN_NAMES = {
    ORIGIN_IGP: "IGP",
    ORIGIN_EGP: "EGP",
    ORIGIN_INCOMPLETE: "INCOMPLETE"
}

# AS_PATH Segment Types (RFC 4271 Section 5.1.2)
AS_SET = 1
AS_SEQUENCE = 2
AS_CONFED_SEQUENCE = 3  # RFC 5065
AS_CONFED_SET = 4  # RFC 5065

AS_PATH_SEGMENT_NAMES = {
    AS_SET: "AS_SET",
    AS_SEQUENCE: "AS_SEQUENCE",
    AS_CONFED_SEQUENCE: "AS_CONFED_SEQUENCE",
    AS_CONFED_SET: "AS_CONFED_SET"
}

# Well-Known Communities (RFC 1997)
COMMUNITY_NO_EXPORT = 0xFFFFFF01  # Do not advertise to eBGP peers
COMMUNITY_NO_ADVERTISE = 0xFFFFFF02  # Do not advertise to any peer
COMMUNITY_NO_EXPORT_SUBCONFED = 0xFFFFFF03  # Do not export outside confederation
COMMUNITY_NOPEER = 0xFFFFFF04  # RFC 3765

WELL_KNOWN_COMMUNITIES = {
    COMMUNITY_NO_EXPORT: "NO_EXPORT",
    COMMUNITY_NO_ADVERTISE: "NO_ADVERTISE",
    COMMUNITY_NO_EXPORT_SUBCONFED: "NO_EXPORT_SUBCONFED",
    COMMUNITY_NOPEER: "NOPEER"
}

# Address Family Identifiers (RFC 4760)
AFI_IPV4 = 1
AFI_IPV6 = 2

AFI_NAMES = {
    AFI_IPV4: "IPv4",
    AFI_IPV6: "IPv6"
}

# Subsequent Address Family Identifiers (RFC 4760)
SAFI_UNICAST = 1
SAFI_MULTICAST = 2
SAFI_MPLS_LABEL = 4  # RFC 3107
SAFI_MCAST_VPN = 5  # RFC 6514
SAFI_VPLS = 65  # RFC 4761
SAFI_VPN = 128  # RFC 4364
SAFI_FLOWSPEC = 133  # RFC 5575

SAFI_NAMES = {
    SAFI_UNICAST: "Unicast",
    SAFI_MULTICAST: "Multicast",
    SAFI_MPLS_LABEL: "MPLS-Label",
    SAFI_MCAST_VPN: "Multicast-VPN",
    SAFI_VPLS: "VPLS",
    SAFI_VPN: "VPN",
    SAFI_FLOWSPEC: "FlowSpec"
}

# Capability Codes (RFC 5492)
CAP_MULTIPROTOCOL = 1  # RFC 4760
CAP_ROUTE_REFRESH = 2  # RFC 2918
CAP_OUTBOUND_ROUTE_FILTERING = 3  # RFC 5291
CAP_MULTIPLE_ROUTES = 4  # RFC 3107
CAP_EXTENDED_NEXTHOP = 5  # RFC 5549
CAP_GRACEFUL_RESTART = 64  # RFC 4724
CAP_FOUR_OCTET_AS = 65  # RFC 6793
CAP_DYNAMIC_CAPABILITY = 67  # RFC 5291
CAP_MULTISESSION_BGP = 68  # RFC 6381
CAP_ADD_PATH = 69  # RFC 7911
CAP_ENHANCED_ROUTE_REFRESH = 70  # RFC 7313
CAP_NETCLAW_MESH_ENDPOINT = 200  # NetClaw mesh discovery (experimental range)
CAP_NETCLAW_TUNNEL = 201         # NetClaw data-plane tunnel (experimental range)

# NetClaw Tunnel Constants
NCTUN_MAGIC = b'NCTUN'            # 5-byte magic for protocol discrimination on port 1179
NCTUN_OVERLAY_PREFIX = "fd00:cc::"  # /48 overlay prefix for tunnel point-to-point links
NCTUN_FRAME_HEADER_SIZE = 2       # 2-byte big-endian length prefix per IP packet
NCTUN_MAX_PACKET_SIZE = 1400      # Maximum IP packet size in tunnel frame

# NetClaw N2N Federation Constants (feature 052)
# Third protocol on the mesh port: after peeking 'N', the next 4 bytes are
# "CTUN" (tunnel) or "CFED" (federation). See bgp/agent.py discrimination.
NCFED_MAGIC = b'NCFED'            # 5-byte magic for federation channel discrimination
NCFED_FRAME_HEADER_SIZE = 5       # 4-byte big-endian payload length + 1-byte flags
NCFED_MAX_PAYLOAD = 65536         # 64 KB max per frame; larger messages chunk
NCFED_FLAG_CONTINUATION = 0x01    # payload is a chunk; concatenate until flag clear
NCFED_HEARTBEAT_INTERVAL = 30     # seconds of silence before sending an empty frame
NCFED_HEARTBEAT_MISS_LIMIT = 3    # missed heartbeats before channel considered down

# ── iN2N — Internal NetClaw Federation (feature 056) ────────────────
# iN2N reuses the NCFED wire framing above over a member-initiated internal
# transport. It is a NEW binding + trust profile, NOT a new wire protocol; the
# frozen eN2N (052/053) framing/consent/default-deny are untouched.
N2N_ROLE_STANDALONE = "standalone"   # a "risk of one" — behaves as pre-056 NetClaw
N2N_ROLE_BORDER = "border"           # the sole coordinator + external face of a risk
N2N_ROLE_MEMBER = "member"           # an internal, tightly-scoped specialist claw
N2N_ROLES = (N2N_ROLE_STANDALONE, N2N_ROLE_BORDER, N2N_ROLE_MEMBER)

# iN2N handshake methods (siblings of eN2N n2n/hello — dispatched over the
# internal channel; carry a risk-local member id + pinned-key proof, NOT an AS).
IN2N_METHOD_HELLO = "in2n/hello"
IN2N_METHOD_ENROLL = "in2n/enroll"

# iN2N transport preamble: the Border sends this magic + a 32-byte nonce on
# accept; the member replies with in2n/hello|in2n/enroll signing the nonce
# (proof-of-possession of its pinned self-signed key). Distinct from NCFED so
# eN2N discrimination is unaffected; iN2N uses its own listener (N2N_IN2N_PORT).
IN2N_MAGIC = b'IN2N1'
IN2N_NONCE_SIZE = 32

# iN2N JSON-RPC error codes (distinct from the frozen eN2N -3200x range).
IN2N_ERR_ENROLL_TOKEN_INVALID = -32021   # token missing/spent/expired
IN2N_ERR_MEMBER_ID_TAKEN = -32022        # member_id already pinned to another key
IN2N_ERR_MEMBER_NOT_TRUSTED = -32023     # key != pinned, or member removed/quarantined
IN2N_ERR_NOT_A_BORDER = -32024           # enrollment attempted against a non-Border claw
IN2N_ERR_NO_CAPABLE_MEMBER = -32030      # no active member covers the requested capability
IN2N_ERR_OUT_OF_SCOPE = -32031           # member asked to act beyond its advertised scope

# iN2N tunables (defaults; overridable via env — see .env.example).
N2N_QUARANTINE_THRESHOLD_DEFAULT = 5     # consecutive auth/health failures → auto-quarantine
# N2N_IN2N_PORT (env): optional dedicated iN2N listener on the Border; when unset
# the Border accepts iN2N dial-ins on the shared mesh port via discrimination.

CAPABILITY_NAMES = {
    CAP_MULTIPROTOCOL: "Multiprotocol",
    CAP_ROUTE_REFRESH: "Route Refresh",
    CAP_OUTBOUND_ROUTE_FILTERING: "Outbound Route Filtering",
    CAP_MULTIPLE_ROUTES: "Multiple Routes to Destination",
    CAP_EXTENDED_NEXTHOP: "Extended Next Hop",
    CAP_GRACEFUL_RESTART: "Graceful Restart",
    CAP_FOUR_OCTET_AS: "4-Octet AS",
    CAP_DYNAMIC_CAPABILITY: "Dynamic Capability",
    CAP_MULTISESSION_BGP: "Multisession BGP",
    CAP_ADD_PATH: "ADD-PATH",
    CAP_ENHANCED_ROUTE_REFRESH: "Enhanced Route Refresh",
    CAP_NETCLAW_MESH_ENDPOINT: "NetClaw Mesh Endpoint",
    CAP_NETCLAW_TUNNEL: "NetClaw Tunnel",
}

# NOTIFICATION Error Codes (RFC 4271 Section 6)
ERR_MESSAGE_HEADER = 1
ERR_OPEN_MESSAGE = 2
ERR_UPDATE_MESSAGE = 3
ERR_HOLD_TIMER_EXPIRED = 4
ERR_FSM = 5
ERR_CEASE = 6

ERROR_CODE_NAMES = {
    ERR_MESSAGE_HEADER: "Message Header Error",
    ERR_OPEN_MESSAGE: "OPEN Message Error",
    ERR_UPDATE_MESSAGE: "UPDATE Message Error",
    ERR_HOLD_TIMER_EXPIRED: "Hold Timer Expired",
    ERR_FSM: "Finite State Machine Error",
    ERR_CEASE: "Cease"
}

# Message Header Error Subcodes
ERR_HDR_CONNECTION_NOT_SYNCHRONIZED = 1
ERR_HDR_BAD_MESSAGE_LENGTH = 2
ERR_HDR_BAD_MESSAGE_TYPE = 3

# OPEN Message Error Subcodes
ERR_OPEN_UNSUPPORTED_VERSION = 1
ERR_OPEN_BAD_PEER_AS = 2
ERR_OPEN_BAD_BGP_IDENTIFIER = 3
ERR_OPEN_UNSUPPORTED_OPTIONAL_PARAMETER = 4
ERR_OPEN_UNACCEPTABLE_HOLD_TIME = 6

# UPDATE Message Error Subcodes
ERR_UPDATE_MALFORMED_ATTRIBUTE_LIST = 1
ERR_UPDATE_UNRECOGNIZED_WELLKNOWN_ATTRIBUTE = 2
ERR_UPDATE_MISSING_WELLKNOWN_ATTRIBUTE = 3
ERR_UPDATE_ATTRIBUTE_FLAGS_ERROR = 4
ERR_UPDATE_ATTRIBUTE_LENGTH_ERROR = 5
ERR_UPDATE_INVALID_ORIGIN = 6
ERR_UPDATE_INVALID_NEXT_HOP = 8
ERR_UPDATE_OPTIONAL_ATTRIBUTE_ERROR = 9
ERR_UPDATE_INVALID_NETWORK_FIELD = 10
ERR_UPDATE_MALFORMED_AS_PATH = 11

# Cease Error Subcodes (RFC 4486)
ERR_CEASE_MAX_PREFIX = 1
ERR_CEASE_ADMIN_SHUTDOWN = 2
ERR_CEASE_PEER_DECONFIGURED = 3
ERR_CEASE_ADMIN_RESET = 4
ERR_CEASE_CONNECTION_REJECTED = 5
ERR_CEASE_OTHER_CONFIG_CHANGE = 6
ERR_CEASE_CONNECTION_COLLISION = 7
ERR_CEASE_OUT_OF_RESOURCES = 8
ERR_CEASE_HARD_RESET = 9  # RFC 8538

# Special AS Numbers
AS_TRANS = 23456  # RFC 6793 - Used when 4-byte AS not supported
PRIVATE_AS_START = 64512
PRIVATE_AS_END = 65534
RESERVED_AS = 65535

# Route Distinguisher Types (RFC 4364)
RD_TYPE_0 = 0  # 2-byte Admin:4-byte Assigned
RD_TYPE_1 = 1  # IPv4 Admin:2-byte Assigned
RD_TYPE_2 = 2  # 4-byte Admin:2-byte Assigned

# BGP Peer Types
PEER_TYPE_INTERNAL = 0  # iBGP (same AS)
PEER_TYPE_EXTERNAL = 1  # eBGP (different AS)

PEER_TYPE_NAMES = {
    PEER_TYPE_INTERNAL: "iBGP",
    PEER_TYPE_EXTERNAL: "eBGP"
}
