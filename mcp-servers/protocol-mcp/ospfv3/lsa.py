"""
OSPFv3 Link State Advertisements (LSAs)
RFC 5340 Appendix A.4
"""

import struct
import ipaddress
from dataclasses import dataclass, field
from typing import List, Optional
from .constants import *
from .packets import LSAHeader


@dataclass
class PrefixOption:
    """
    OSPFv3 Prefix with options (RFC 5340 Section A.4.1.1)

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |  PrefixLength | PrefixOptions |        Metric                 |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                        Address Prefix                         |
    |                           ...                                 |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    prefix_length: int = 0
    prefix_options: int = 0
    metric: int = 0
    address_prefix: str = "::"

    def encode(self) -> bytes:
        """Encode prefix to bytes"""
        # Calculate number of 32-bit words needed for address
        if self.prefix_length == 0:
            prefix_words = 0
        else:
            prefix_words = (self.prefix_length + 31) // 32

        data = struct.pack('!BBH',
                          self.prefix_length,
                          self.prefix_options,
                          self.metric)

        # Add address prefix (only the necessary words)
        if prefix_words > 0:
            addr_bytes = ipaddress.IPv6Address(self.address_prefix).packed
            data += addr_bytes[:prefix_words * 4]

        return data

    @classmethod
    def decode(cls, data: bytes, offset: int = 0) -> tuple['PrefixOption', int]:
        """
        Decode prefix from bytes

        Returns:
            Tuple of (PrefixOption, bytes_consumed)
        """
        if len(data) < offset + 4:
            raise ValueError("Insufficient data for prefix")

        prefix_length, prefix_options, metric = struct.unpack('!BBH', data[offset:offset + 4])

        # Calculate number of 32-bit words
        if prefix_length == 0:
            prefix_words = 0
        else:
            prefix_words = (prefix_length + 31) // 32

        # Extract address prefix
        if prefix_words > 0:
            addr_bytes = data[offset + 4:offset + 4 + prefix_words * 4]
            # Pad to 16 bytes
            addr_bytes = addr_bytes + b'\x00' * (16 - len(addr_bytes))
            address_prefix = str(ipaddress.IPv6Address(addr_bytes))
        else:
            address_prefix = "::"

        bytes_consumed = 4 + prefix_words * 4

        return cls(
            prefix_length=prefix_length,
            prefix_options=prefix_options,
            metric=metric,
            address_prefix=address_prefix
        ), bytes_consumed

    def __str__(self) -> str:
        return f"{self.address_prefix}/{self.prefix_length} (metric={self.metric})"


@dataclass
class RouterLSA:
    """
    Router-LSA (RFC 5340 Section A.4.3)

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            0              |V|E|B|            Options           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |     Type      |       0       |          Metric               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                      Interface ID                             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                   Neighbor Interface ID                       |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                    Neighbor Router ID                         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                          ...                                  |
    """
    header: LSAHeader = field(default_factory=lambda: LSAHeader(ls_type=ROUTER_LSA))
    flags: int = 0  # V, E, B bits
    options: int = OPTION_V6 | OPTION_E | OPTION_R
    links: List['RouterLink'] = field(default_factory=list)

    def encode(self) -> bytes:
        """Encode Router-LSA body (without header)"""
        body = struct.pack('!BBH',
                          0,  # Reserved
                          self.flags,
                          self.options & 0xFFFF)

        # Encode each link
        for link in self.links:
            body += link.encode()

        return body

    @classmethod
    def decode(cls, data: bytes, header: LSAHeader) -> 'RouterLSA':
        """Decode Router-LSA from bytes"""
        if len(data) < 4:
            raise ValueError("Insufficient data for Router-LSA")

        flags = data[1]
        options = struct.unpack('!H', data[2:4])[0]

        # Decode links
        links = []
        offset = 4
        while offset + 16 <= len(data):
            link = RouterLink.decode(data[offset:offset + 16])
            links.append(link)
            offset += 16

        return cls(header=header, flags=flags, options=options, links=links)


@dataclass
class RouterLink:
    """Router-LSA Link entry"""
    link_type: int = LINK_TYPE_PTP
    metric: int = 1
    interface_id: int = 0
    neighbor_interface_id: int = 0
    neighbor_router_id: str = "0.0.0.0"

    def encode(self) -> bytes:
        """Encode to 16 bytes"""
        neighbor_id_int = int(ipaddress.IPv4Address(self.neighbor_router_id))

        return struct.pack('!BBHIII',
                          self.link_type,
                          0,  # Reserved
                          self.metric,
                          self.interface_id,
                          self.neighbor_interface_id,
                          neighbor_id_int)

    @classmethod
    def decode(cls, data: bytes) -> 'RouterLink':
        """Decode from 16 bytes"""
        fields = struct.unpack('!BBHIII', data[:16])

        return cls(
            link_type=fields[0],
            metric=fields[2],
            interface_id=fields[3],
            neighbor_interface_id=fields[4],
            neighbor_router_id=str(ipaddress.IPv4Address(fields[5]))
        )


@dataclass
class NetworkLSA:
    """
    Network-LSA (RFC 5340 Section A.4.4)

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |      0        |                  Options                      |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                       Attached Router                         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                          ...                                  |
    """
    header: LSAHeader = field(default_factory=lambda: LSAHeader(ls_type=NETWORK_LSA))
    options: int = OPTION_V6 | OPTION_E | OPTION_R
    attached_routers: List[str] = field(default_factory=list)

    def encode(self) -> bytes:
        """Encode Network-LSA body"""
        body = struct.pack('!I', self.options & 0xFFFFFF)

        for router_id in self.attached_routers:
            router_int = int(ipaddress.IPv4Address(router_id))
            body += struct.pack('!I', router_int)

        return body

    @classmethod
    def decode(cls, data: bytes, header: LSAHeader) -> 'NetworkLSA':
        """Decode Network-LSA"""
        if len(data) < 4:
            raise ValueError("Insufficient data for Network-LSA")

        options = struct.unpack('!I', data[:4])[0] & 0xFFFFFF

        attached_routers = []
        offset = 4
        while offset + 4 <= len(data):
            router_int = struct.unpack('!I', data[offset:offset + 4])[0]
            attached_routers.append(str(ipaddress.IPv4Address(router_int)))
            offset += 4

        return cls(header=header, options=options, attached_routers=attached_routers)


@dataclass
class LinkLSA:
    """
    Link-LSA (RFC 5340 Section A.4.9)

    Link-local scope LSA that provides:
    - Router's link-local address
    - List of IPv6 prefixes on the link
    - Options for the link

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    | Rtr Priority  |                Options                        |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                                                               |
    +-                                                             -+
    |                                                               |
    +-                Link-local Interface Address                -+
    |                                                               |
    +-                                                             -+
    |                                                               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                         # prefixes                            |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |  PrefixLength | PrefixOptions |             0                 |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                        Address Prefix                         |
    |                          ...                                  |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    header: LSAHeader = field(default_factory=lambda: LSAHeader(ls_type=LINK_LSA))
    router_priority: int = 1
    options: int = OPTION_V6 | OPTION_E | OPTION_R
    link_local_address: str = "::"
    prefixes: List[PrefixOption] = field(default_factory=list)

    def encode(self) -> bytes:
        """Encode Link-LSA body"""
        body = struct.pack('!BI',
                          self.router_priority,
                          self.options & 0xFFFFFF)

        # Add link-local address
        link_local_bytes = ipaddress.IPv6Address(self.link_local_address).packed
        body += link_local_bytes

        # Add number of prefixes
        body += struct.pack('!I', len(self.prefixes))

        # Add each prefix
        for prefix in self.prefixes:
            body += prefix.encode()

        return body

    @classmethod
    def decode(cls, data: bytes, header: LSAHeader) -> 'LinkLSA':
        """Decode Link-LSA"""
        if len(data) < 24:  # Min: 1 + 3 + 16 + 4 bytes
            raise ValueError("Insufficient data for Link-LSA")

        router_priority = data[0]
        options = struct.unpack('!I', b'\x00' + data[1:4])[0]

        link_local_bytes = data[4:20]
        link_local_address = str(ipaddress.IPv6Address(link_local_bytes))

        num_prefixes = struct.unpack('!I', data[20:24])[0]

        prefixes = []
        offset = 24
        for _ in range(num_prefixes):
            prefix, consumed = PrefixOption.decode(data, offset)
            prefixes.append(prefix)
            offset += consumed

        return cls(
            header=header,
            router_priority=router_priority,
            options=options,
            link_local_address=link_local_address,
            prefixes=prefixes
        )


@dataclass
class IntraAreaPrefixLSA:
    """
    Intra-Area-Prefix-LSA (RFC 5340 Section A.4.10)

    Associates IPv6 address prefixes with:
    - A Router-LSA (for stub networks, loopbacks)
    - A Network-LSA (for transit network prefixes)

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |        # prefixes             |      Referenced LS Type       |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                  Referenced Link State ID                     |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               Referenced Advertising Router                   |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |  PrefixLength | PrefixOptions |         Metric                |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                        Address Prefix                         |
    |                          ...                                  |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    header: LSAHeader = field(default_factory=lambda: LSAHeader(ls_type=INTRA_AREA_PREFIX_LSA))
    referenced_ls_type: int = ROUTER_LSA
    referenced_link_state_id: int = 0
    referenced_advertising_router: str = "0.0.0.0"
    prefixes: List[PrefixOption] = field(default_factory=list)

    def encode(self) -> bytes:
        """Encode Intra-Area-Prefix-LSA body"""
        ref_router_int = int(ipaddress.IPv4Address(self.referenced_advertising_router))

        body = struct.pack('!HHII',
                          len(self.prefixes),
                          self.referenced_ls_type,
                          self.referenced_link_state_id,
                          ref_router_int)

        for prefix in self.prefixes:
            body += prefix.encode()

        return body

    @classmethod
    def decode(cls, data: bytes, header: LSAHeader) -> 'IntraAreaPrefixLSA':
        """Decode Intra-Area-Prefix-LSA"""
        if len(data) < 12:
            raise ValueError("Insufficient data for Intra-Area-Prefix-LSA")

        fields = struct.unpack('!HHII', data[:12])

        num_prefixes = fields[0]
        referenced_ls_type = fields[1]
        referenced_link_state_id = fields[2]
        referenced_advertising_router = str(ipaddress.IPv4Address(fields[3]))

        prefixes = []
        offset = 12
        for _ in range(num_prefixes):
            prefix, consumed = PrefixOption.decode(data, offset)
            prefixes.append(prefix)
            offset += consumed

        return cls(
            header=header,
            referenced_ls_type=referenced_ls_type,
            referenced_link_state_id=referenced_link_state_id,
            referenced_advertising_router=referenced_advertising_router,
            prefixes=prefixes
        )


def decode_lsa(header: LSAHeader, body: bytes):
    """
    Decode LSA based on type

    Returns:
        LSA object or None if type not supported
    """
    try:
        if header.ls_type == ROUTER_LSA:
            return RouterLSA.decode(body, header)
        elif header.ls_type == NETWORK_LSA:
            return NetworkLSA.decode(body, header)
        elif header.ls_type == LINK_LSA:
            return LinkLSA.decode(body, header)
        elif header.ls_type == INTRA_AREA_PREFIX_LSA:
            return IntraAreaPrefixLSA.decode(body, header)
        else:
            # Unsupported LSA type
            return None
    except Exception as e:
        logging.error(f"Error decoding LSA type {header.ls_type:04x}: {e}")
        return None
