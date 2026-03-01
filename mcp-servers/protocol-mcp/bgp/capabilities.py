"""
BGP Capabilities Negotiation (RFC 5492)

Implements BGP capability advertisement in OPEN messages.
Capabilities allow peers to negotiate optional features.
"""

import struct
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass

from .constants import *


@dataclass
class CapabilityInfo:
    """Information about a BGP capability"""
    code: int
    name: str
    supported: bool = False


class CapabilityManager:
    """
    Manages BGP capabilities for a session

    Tracks local capabilities, peer capabilities, and negotiated result
    """

    def __init__(self, local_as: int):
        """
        Initialize capability manager

        Args:
            local_as: Local AS number
        """
        self.local_as = local_as

        # Local capabilities (what we support)
        self.local_capabilities: Dict[int, bytes] = {}

        # Multiprotocol capabilities (can have multiple AFI/SAFI pairs)
        self.multiprotocol_capabilities: List[Tuple[int, int]] = []

        # Peer capabilities (what peer supports)
        self.peer_capabilities: Dict[int, bytes] = {}

        # Negotiated capabilities (intersection)
        self.negotiated_capabilities: Dict[int, bytes] = {}

    def add_local_capability(self, code: int, value: bytes) -> None:
        """
        Add local capability

        Args:
            code: Capability code
            value: Capability value
        """
        self.local_capabilities[code] = value

    def enable_multiprotocol(self, afi: int, safi: int) -> None:
        """
        Enable multiprotocol capability

        Args:
            afi: Address Family Identifier
            safi: Subsequent Address Family Identifier
        """
        # Store AFI/SAFI pairs separately since we can have multiple
        if (afi, safi) not in self.multiprotocol_capabilities:
            self.multiprotocol_capabilities.append((afi, safi))

    def enable_route_refresh(self) -> None:
        """Enable route refresh capability"""
        self.add_local_capability(CAP_ROUTE_REFRESH, b'')

    def enable_four_octet_as(self) -> None:
        """Enable 4-byte AS capability"""
        value = struct.pack('!I', self.local_as)
        self.add_local_capability(CAP_FOUR_OCTET_AS, value)

    def enable_graceful_restart(self, restart_time: int, restart_state: bool = False) -> None:
        """
        Enable graceful restart capability

        Args:
            restart_time: Restart time in seconds (0-4095)
            restart_state: Restart state flag
        """
        # Flags (4 bits) + Restart Time (12 bits)
        flags_time = restart_time & 0x0FFF
        if restart_state:
            flags_time |= 0x8000

        value = struct.pack('!H', flags_time)
        self.add_local_capability(CAP_GRACEFUL_RESTART, value)

    def enable_add_path(self, afi: int, safi: int, send: bool = True, receive: bool = True) -> None:
        """
        Enable ADD-PATH capability

        Args:
            afi: Address Family Identifier
            safi: Subsequent Address Family Identifier
            send: Can send multiple paths
            receive: Can receive multiple paths
        """
        # AFI (2 bytes), SAFI (1 byte), Send/Receive (1 byte)
        flags = 0
        if send:
            flags |= 0x01
        if receive:
            flags |= 0x02

        value = struct.pack('!HBB', afi, safi, flags)
        self.add_local_capability(CAP_ADD_PATH, value)

    def get_local_capabilities(self) -> List[Tuple[int, bytes]]:
        """
        Get list of local capabilities

        Returns:
            List of (code, value) tuples
        """
        result = []

        # Add multiprotocol capabilities (can have multiple)
        for afi, safi in self.multiprotocol_capabilities:
            value = struct.pack('!HBB', afi, 0, safi)
            result.append((CAP_MULTIPROTOCOL, value))

        # Add other capabilities
        result.extend(self.local_capabilities.items())

        return result

    def set_peer_capabilities(self, capabilities: Dict[int, bytes]) -> None:
        """
        Set peer capabilities from OPEN message

        Args:
            capabilities: Dictionary of peer capabilities
        """
        self.peer_capabilities = capabilities
        self._negotiate_capabilities()

    def _negotiate_capabilities(self) -> None:
        """Negotiate capabilities (intersection of local and peer)"""
        self.negotiated_capabilities = {}

        for code, value in self.local_capabilities.items():
            if code in self.peer_capabilities:
                # Both sides support this capability
                self.negotiated_capabilities[code] = value

    def has_capability(self, code: int) -> bool:
        """
        Check if capability is negotiated

        Args:
            code: Capability code

        Returns:
            True if negotiated
        """
        return code in self.negotiated_capabilities

    def get_capability_value(self, code: int) -> Optional[bytes]:
        """
        Get negotiated capability value

        Args:
            code: Capability code

        Returns:
            Capability value or None
        """
        return self.negotiated_capabilities.get(code)

    def supports_ipv4_unicast(self) -> bool:
        """Check if IPv4 unicast is supported"""
        # IPv4 unicast is implicit (RFC 4760 Section 8)
        return True

    def supports_ipv6_unicast(self) -> bool:
        """Check if IPv6 unicast is negotiated"""
        if CAP_MULTIPROTOCOL not in self.negotiated_capabilities:
            return False

        value = self.negotiated_capabilities[CAP_MULTIPROTOCOL]
        if len(value) < 4:
            return False

        afi = struct.unpack('!H', value[0:2])[0]
        safi = value[3]

        return afi == AFI_IPV6 and safi == SAFI_UNICAST

    def supports_route_refresh(self) -> bool:
        """Check if route refresh is negotiated"""
        return self.has_capability(CAP_ROUTE_REFRESH)

    def supports_four_octet_as(self) -> bool:
        """Check if 4-byte AS is negotiated"""
        return self.has_capability(CAP_FOUR_OCTET_AS)

    def supports_graceful_restart(self) -> bool:
        """Check if graceful restart is negotiated"""
        return self.has_capability(CAP_GRACEFUL_RESTART)

    def supports_add_path(self) -> bool:
        """Check if ADD-PATH is negotiated"""
        return self.has_capability(CAP_ADD_PATH)

    def get_four_octet_as(self) -> Optional[int]:
        """
        Get peer's 4-byte AS number

        Returns:
            AS number or None
        """
        value = self.peer_capabilities.get(CAP_FOUR_OCTET_AS)
        if value and len(value) >= 4:
            return struct.unpack('!I', value[:4])[0]
        return None

    def get_supported_address_families(self) -> List[Tuple[int, int]]:
        """
        Get list of supported address families

        Returns:
            List of (afi, safi) tuples
        """
        families = [(AFI_IPV4, SAFI_UNICAST)]  # IPv4 unicast is implicit

        # Check multiprotocol capability
        value = self.negotiated_capabilities.get(CAP_MULTIPROTOCOL)
        if value and len(value) >= 4:
            afi = struct.unpack('!H', value[0:2])[0]
            safi = value[3]
            families.append((afi, safi))

        return families

    def get_statistics(self) -> Dict:
        """
        Get capability statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'local_capabilities': len(self.local_capabilities),
            'peer_capabilities': len(self.peer_capabilities),
            'negotiated_capabilities': len(self.negotiated_capabilities),
            'ipv4_unicast': self.supports_ipv4_unicast(),
            'ipv6_unicast': self.supports_ipv6_unicast(),
            'route_refresh': self.supports_route_refresh(),
            'four_octet_as': self.supports_four_octet_as(),
            'graceful_restart': self.supports_graceful_restart(),
            'add_path': self.supports_add_path()
        }


def parse_capabilities_from_open(capabilities_data: List[Tuple[int, bytes]]) -> Dict[int, bytes]:
    """
    Parse capabilities from OPEN message

    Args:
        capabilities_data: List of (code, value) tuples from BGPCapability objects

    Returns:
        Dictionary mapping code to value
    """
    capabilities = {}
    for code, value in capabilities_data:
        capabilities[code] = value
    return capabilities


def build_capability_list(cap_manager: CapabilityManager) -> List:
    """
    Build list of BGPCapability objects for OPEN message

    Args:
        cap_manager: CapabilityManager

    Returns:
        List of BGPCapability objects (from messages.py)
    """
    from .messages import BGPCapability

    capabilities = []
    for code, value in cap_manager.get_local_capabilities():
        cap = BGPCapability(code, value)
        capabilities.append(cap)

    return capabilities
