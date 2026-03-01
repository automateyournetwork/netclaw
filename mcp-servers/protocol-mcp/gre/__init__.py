"""
GRE (Generic Routing Encapsulation) Module

RFC 2784 - Generic Routing Encapsulation (GRE)
RFC 2890 - Key and Sequence Number Extensions to GRE

This module provides GRE tunnel functionality for the Agentic network,
enabling interconnection with external networks like Cisco CML, Containerlab,
and other GRE-capable devices.

Features:
- GRE encapsulation/decapsulation per RFC 2784/2890
- Support for keyed GRE tunnels
- Sequence number support for ordered delivery
- Integration with OSPF/BGP for routing over tunnels
- Both active (initiator) and passive (listener) tunnel modes

Example Usage:
    from gre import GREManager, GRETunnelConfig

    # Create manager
    manager = GREManager(local_ip="192.168.1.1")

    # Create tunnel to CML router
    config = GRETunnelConfig(
        name="gre0",
        local_ip="192.168.1.1",
        remote_ip="192.168.2.1",
        tunnel_ip="10.0.0.1/30",
        key=12345  # Optional
    )
    tunnel = await manager.create_tunnel(config)

    # Tunnel is now up - run OSPF/BGP over it
"""

from .constants import (
    # Protocol numbers
    IPPROTO_GRE,

    # Flags
    GRE_FLAG_CHECKSUM,
    GRE_FLAG_KEY,
    GRE_FLAG_SEQUENCE,
    GRE_VERSION_0,

    # Protocol types
    PROTO_IPV4,
    PROTO_IPV6,
    PROTO_ETHERNET,
    PROTOCOL_NAMES,

    # Header sizes
    GRE_HEADER_MIN,
    GRE_HEADER_MAX,

    # MTU
    GRE_TUNNEL_MTU,
    GRE_SAFE_MTU,
    GRE_OVERHEAD_MIN,

    # Tunnel states
    TUNNEL_STATE_DOWN,
    TUNNEL_STATE_UP,
    TUNNEL_STATE_ADMIN_DOWN,
    TUNNEL_STATE_ESTABLISHING,

    # Modes
    MODE_GRE_IPV4,
    MODE_GRE_TAP,

    # Errors
    GREError,
    ERROR_MESSAGES,
)

from .header import (
    GREHeader,
    encode_gre_header,
    decode_gre_header,
    calculate_gre_checksum,
)

from .tunnel import (
    GRETunnel,
    GRETunnelConfig,
    GRETunnelStatistics,
)

from .manager import (
    GREManager,
    get_gre_manager,
    configure_gre_manager,
)

__all__ = [
    # Constants
    "IPPROTO_GRE",
    "GRE_FLAG_CHECKSUM",
    "GRE_FLAG_KEY",
    "GRE_FLAG_SEQUENCE",
    "PROTO_IPV4",
    "PROTO_IPV6",
    "PROTO_ETHERNET",
    "PROTOCOL_NAMES",
    "GRE_HEADER_MIN",
    "GRE_HEADER_MAX",
    "GRE_TUNNEL_MTU",
    "GRE_SAFE_MTU",
    "TUNNEL_STATE_DOWN",
    "TUNNEL_STATE_UP",
    "GREError",

    # Header
    "GREHeader",
    "encode_gre_header",
    "decode_gre_header",
    "calculate_gre_checksum",

    # Tunnel
    "GRETunnel",
    "GRETunnelConfig",
    "GRETunnelStatistics",

    # Manager
    "GREManager",
    "get_gre_manager",
    "configure_gre_manager",
]

__version__ = "1.0.0"
