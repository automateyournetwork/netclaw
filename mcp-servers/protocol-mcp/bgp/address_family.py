"""
BGP Multiprotocol Extensions (RFC 4760)

Implements support for IPv4 and IPv6 address families using
MP_REACH_NLRI and MP_UNREACH_NLRI path attributes.
"""

import struct
import socket
from typing import Tuple, List, Optional
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network

from .constants import *


class AddressFamily:
    """
    Address Family utilities for BGP multiprotocol extensions

    Constants for AFI and SAFI values per RFC 4760
    """

    # AFI values
    AFI_IPV4 = 1
    AFI_IPV6 = 2

    # SAFI values
    SAFI_UNICAST = 1
    SAFI_MULTICAST = 2

    @staticmethod
    def encode_prefix(prefix: str, afi: int) -> bytes:
        """
        Encode prefix for NLRI or MP_REACH_NLRI

        Args:
            prefix: Prefix string (e.g., "203.0.113.0/24" or "2001:db8::/32")
            afi: Address family identifier

        Returns:
            Encoded prefix bytes: <length> <prefix bytes>
        """
        # Parse prefix
        if '/' in prefix:
            ip_str, prefix_len_str = prefix.split('/')
            prefix_len = int(prefix_len_str)
        else:
            ip_str = prefix
            prefix_len = 32 if afi == AFI_IPV4 else 128

        # Convert IP to bytes
        if afi == AFI_IPV4:
            ip_bytes = socket.inet_aton(ip_str)
        elif afi == AFI_IPV6:
            ip_bytes = socket.inet_pton(socket.AF_INET6, ip_str)
        else:
            raise ValueError(f"Unsupported AFI: {afi}")

        # Calculate number of significant octets
        num_octets = (prefix_len + 7) // 8

        # Encode: <length> <prefix bytes>
        return struct.pack('!B', prefix_len) + ip_bytes[:num_octets]

    @staticmethod
    def decode_prefix(data: bytes, offset: int, afi: int) -> Tuple[Optional[str], int]:
        """
        Decode prefix from NLRI or MP_REACH_NLRI

        Args:
            data: Data bytes
            offset: Offset in data
            afi: Address family identifier

        Returns:
            (prefix_string, bytes_consumed) or (None, 0) on error
        """
        if offset >= len(data):
            return (None, 0)

        # Read prefix length
        prefix_len = data[offset]
        offset += 1

        # Calculate number of octets
        num_octets = (prefix_len + 7) // 8

        if offset + num_octets > len(data):
            return (None, 0)

        # Read prefix bytes
        prefix_bytes = data[offset:offset + num_octets]

        # Pad to full address size
        if afi == AFI_IPV4:
            prefix_bytes += b'\x00' * (4 - num_octets)
            ip_str = socket.inet_ntoa(prefix_bytes)
        elif afi == AFI_IPV6:
            prefix_bytes += b'\x00' * (16 - num_octets)
            ip_str = socket.inet_ntop(socket.AF_INET6, prefix_bytes)
        else:
            return (None, 0)

        prefix = f"{ip_str}/{prefix_len}"
        return (prefix, 1 + num_octets)

    @staticmethod
    def decode_prefixes(data: bytes, afi: int) -> List[str]:
        """
        Decode multiple prefixes from NLRI

        Args:
            data: NLRI data
            afi: Address family identifier

        Returns:
            List of prefix strings
        """
        prefixes = []
        offset = 0

        while offset < len(data):
            prefix, consumed = AddressFamily.decode_prefix(data, offset, afi)
            if prefix:
                prefixes.append(prefix)
                offset += consumed
            else:
                break

        return prefixes

    @staticmethod
    def encode_next_hop(ip: str, afi: int, link_local: Optional[str] = None) -> bytes:
        """
        Encode next hop for MP_REACH_NLRI

        Args:
            ip: Next hop IP address
            afi: Address family identifier
            link_local: Link-local address for IPv6 (optional)

        Returns:
            Encoded next hop bytes

        Notes:
            - IPv4: 4 bytes
            - IPv6: 16 bytes (global) or 32 bytes (global + link-local)
        """
        if afi == AFI_IPV4:
            return socket.inet_aton(ip)
        elif afi == AFI_IPV6:
            nh_bytes = socket.inet_pton(socket.AF_INET6, ip)
            if link_local:
                nh_bytes += socket.inet_pton(socket.AF_INET6, link_local)
            return nh_bytes
        else:
            raise ValueError(f"Unsupported AFI: {afi}")

    @staticmethod
    def decode_next_hop(data: bytes, afi: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Decode next hop from MP_REACH_NLRI

        Args:
            data: Next hop bytes
            afi: Address family identifier

        Returns:
            (next_hop, link_local) or (None, None) on error
            For IPv6: link_local may be None
        """
        if afi == AFI_IPV4:
            if len(data) < 4:
                return (None, None)
            next_hop = socket.inet_ntoa(data[:4])
            return (next_hop, None)

        elif afi == AFI_IPV6:
            if len(data) < 16:
                return (None, None)

            next_hop = socket.inet_ntop(socket.AF_INET6, data[:16])

            # Check for link-local address
            link_local = None
            if len(data) >= 32:
                link_local = socket.inet_ntop(socket.AF_INET6, data[16:32])

            return (next_hop, link_local)

        else:
            return (None, None)

    @staticmethod
    def get_afi_from_prefix(prefix: str) -> int:
        """
        Determine AFI from prefix string

        Args:
            prefix: Prefix string

        Returns:
            AFI_IPV4 or AFI_IPV6
        """
        try:
            net = ip_network(prefix, strict=False)
            if net.version == 4:
                return AFI_IPV4
            elif net.version == 6:
                return AFI_IPV6
        except:
            pass

        # Fallback: check for ':' in address (IPv6 indicator)
        if ':' in prefix:
            return AFI_IPV6
        else:
            return AFI_IPV4


# MP_REACH_NLRI and MP_UNREACH_NLRI Attributes

class MPReachNLRIAttribute:
    """
    MP_REACH_NLRI Attribute (Type 14, RFC 4760)

    Used for IPv6 and other non-IPv4 address families
    """

    def __init__(self, afi: int, safi: int, next_hop: str, nlri: List[str],
                 link_local: Optional[str] = None):
        """
        Args:
            afi: Address Family Identifier
            safi: Subsequent Address Family Identifier
            next_hop: Next hop IP
            nlri: List of prefixes to advertise
            link_local: Link-local next hop (IPv6 only)
        """
        self.afi = afi
        self.safi = safi
        self.next_hop = next_hop
        self.link_local = link_local
        self.nlri = nlri

    def encode(self) -> bytes:
        """
        Encode MP_REACH_NLRI attribute

        Returns:
            Attribute value bytes (without attribute header)
        """
        # AFI (2 bytes) + SAFI (1 byte)
        data = struct.pack('!HB', self.afi, self.safi)

        # Next hop length + next hop
        nh_bytes = AddressFamily.encode_next_hop(self.next_hop, self.afi, self.link_local)
        data += struct.pack('!B', len(nh_bytes)) + nh_bytes

        # Reserved (1 byte, must be 0)
        data += b'\x00'

        # NLRI
        for prefix in self.nlri:
            data += AddressFamily.encode_prefix(prefix, self.afi)

        return data

    @staticmethod
    def decode(data: bytes) -> Optional['MPReachNLRIAttribute']:
        """
        Decode MP_REACH_NLRI attribute

        Args:
            data: Attribute value bytes

        Returns:
            MPReachNLRIAttribute or None
        """
        if len(data) < 5:  # Minimum size
            return None

        # Parse AFI and SAFI
        afi = struct.unpack('!H', data[0:2])[0]
        safi = data[2]

        # Parse next hop length
        nh_len = data[3]
        if len(data) < 4 + nh_len + 1:
            return None

        # Parse next hop
        nh_data = data[4:4+nh_len]
        next_hop, link_local = AddressFamily.decode_next_hop(nh_data, afi)
        if next_hop is None:
            return None

        # Skip reserved byte
        offset = 4 + nh_len + 1

        # Parse NLRI
        nlri_data = data[offset:]
        nlri = AddressFamily.decode_prefixes(nlri_data, afi)

        return MPReachNLRIAttribute(afi, safi, next_hop, nlri, link_local)


class MPUnreachNLRIAttribute:
    """
    MP_UNREACH_NLRI Attribute (Type 15, RFC 4760)

    Used for withdrawing IPv6 and other non-IPv4 routes
    """

    def __init__(self, afi: int, safi: int, withdrawn_routes: List[str]):
        """
        Args:
            afi: Address Family Identifier
            safi: Subsequent Address Family Identifier
            withdrawn_routes: List of prefixes to withdraw
        """
        self.afi = afi
        self.safi = safi
        self.withdrawn_routes = withdrawn_routes

    def encode(self) -> bytes:
        """
        Encode MP_UNREACH_NLRI attribute

        Returns:
            Attribute value bytes (without attribute header)
        """
        # AFI (2 bytes) + SAFI (1 byte)
        data = struct.pack('!HB', self.afi, self.safi)

        # Withdrawn routes
        for prefix in self.withdrawn_routes:
            data += AddressFamily.encode_prefix(prefix, self.afi)

        return data

    @staticmethod
    def decode(data: bytes) -> Optional['MPUnreachNLRIAttribute']:
        """
        Decode MP_UNREACH_NLRI attribute

        Args:
            data: Attribute value bytes

        Returns:
            MPUnreachNLRIAttribute or None
        """
        if len(data) < 3:  # Minimum size
            return None

        # Parse AFI and SAFI
        afi = struct.unpack('!H', data[0:2])[0]
        safi = data[2]

        # Parse withdrawn routes
        withdrawn_data = data[3:]
        withdrawn_routes = AddressFamily.decode_prefixes(withdrawn_data, afi)

        return MPUnreachNLRIAttribute(afi, safi, withdrawn_routes)
