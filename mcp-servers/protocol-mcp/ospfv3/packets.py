"""
OSPFv3 Packet Structures and Encoding/Decoding
RFC 5340 - OSPF for IPv6
"""

import struct
import socket
import ipaddress
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from .constants import *


def calculate_checksum(data: bytes, src_addr: str, dst_addr: str) -> int:
    """
    Calculate OSPFv3 checksum (RFC 5340 Section A.3.1)

    Uses IPv6 pseudo-header for checksum calculation:
    - Source Address (16 bytes)
    - Destination Address (16 bytes)
    - Upper-Layer Packet Length (4 bytes)
    - Zero (3 bytes)
    - Next Header = 89 (1 byte)
    - OSPFv3 packet data

    Args:
        data: OSPFv3 packet data
        src_addr: Source IPv6 address
        dst_addr: Destination IPv6 address

    Returns:
        Checksum value (16-bit)
    """
    # Build pseudo-header
    src_bytes = ipaddress.IPv6Address(src_addr).packed
    dst_bytes = ipaddress.IPv6Address(dst_addr).packed

    pseudo_header = b''
    pseudo_header += src_bytes  # 16 bytes
    pseudo_header += dst_bytes  # 16 bytes
    pseudo_header += struct.pack('!I', len(data))  # Upper-layer packet length
    pseudo_header += b'\x00\x00\x00'  # Zero (3 bytes)
    pseudo_header += struct.pack('!B', OSPF_PROTOCOL_NUMBER)  # Next Header

    # Combine pseudo-header and data
    checksum_data = pseudo_header + data

    # Calculate checksum
    if len(checksum_data) % 2:
        checksum_data += b'\x00'

    total = 0
    for i in range(0, len(checksum_data), 2):
        word = (checksum_data[i] << 8) + checksum_data[i + 1]
        total += word

    # Add carries
    while total > 0xFFFF:
        total = (total & 0xFFFF) + (total >> 16)

    # One's complement
    checksum = ~total & 0xFFFF

    return checksum


@dataclass
class OSPFv3Header:
    """
    OSPFv3 Packet Header (RFC 5340 Section A.3.1)

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Version #   |     Type      |         Packet length         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                          Router ID                            |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                           Area ID                             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |           Checksum            |  Instance ID  |      0        |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    version: int = OSPFV3_VERSION
    packet_type: int = 0
    packet_length: int = 0
    router_id: str = "0.0.0.0"
    area_id: str = "0.0.0.0"
    checksum: int = 0
    instance_id: int = DEFAULT_INSTANCE_ID

    def encode(self) -> bytes:
        """Encode header to bytes (checksum will be calculated later)"""
        router_id_int = int(ipaddress.IPv4Address(self.router_id))
        area_id_int = int(ipaddress.IPv4Address(self.area_id))

        return struct.pack(
            '!BBHIIHBB',
            self.version,
            self.packet_type,
            self.packet_length,
            router_id_int,
            area_id_int,
            self.checksum,
            self.instance_id,
            0  # Reserved
        )

    @classmethod
    def decode(cls, data: bytes) -> 'OSPFv3Header':
        """Decode header from bytes"""
        if len(data) < OSPF_HEADER_SIZE:
            raise ValueError(f"Insufficient data for OSPFv3 header: {len(data)} < {OSPF_HEADER_SIZE}")

        fields = struct.unpack('!BBHIIHBB', data[:OSPF_HEADER_SIZE])

        router_id = str(ipaddress.IPv4Address(fields[3]))
        area_id = str(ipaddress.IPv4Address(fields[4]))

        return cls(
            version=fields[0],
            packet_type=fields[1],
            packet_length=fields[2],
            router_id=router_id,
            area_id=area_id,
            checksum=fields[5],
            instance_id=fields[6]
        )


@dataclass
class OSPFv3HelloPacket:
    """
    OSPFv3 Hello Packet (RFC 5340 Section A.3.2)

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                        Interface ID                           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |   Rtr Priority|             Options                           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |         HelloInterval         |        DeadInterval           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                   Designated Router ID                        |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                Backup Designated Router ID                    |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                          Neighbor ID                          |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                          ...                                  |
    """
    header: OSPFv3Header = field(default_factory=lambda: OSPFv3Header(packet_type=HELLO_PACKET))
    interface_id: int = 0
    router_priority: int = 1
    options: int = OPTION_V6 | OPTION_E | OPTION_R  # V6, E, and R bits set by default
    hello_interval: int = DEFAULT_HELLO_INTERVAL
    dead_interval: int = DEFAULT_DEAD_INTERVAL
    designated_router: str = "0.0.0.0"
    backup_designated_router: str = "0.0.0.0"
    neighbors: List[str] = field(default_factory=list)

    def encode(self, src_addr: str, dst_addr: str) -> bytes:
        """Encode Hello packet to bytes with checksum"""
        # Encode body
        dr_int = int(ipaddress.IPv4Address(self.designated_router))
        bdr_int = int(ipaddress.IPv4Address(self.backup_designated_router))

        # Combine router_priority (1 byte) and options (3 bytes) into 4 bytes
        priority_options = (self.router_priority << 24) | (self.options & 0xFFFFFF)

        body = struct.pack(
            '!IIHHII',
            self.interface_id,
            priority_options,
            self.hello_interval,
            self.dead_interval,
            dr_int,
            bdr_int
        )

        # Add neighbor list
        for neighbor in self.neighbors:
            neighbor_int = int(ipaddress.IPv4Address(neighbor))
            body += struct.pack('!I', neighbor_int)

        # Update header
        self.header.packet_length = OSPF_HEADER_SIZE + len(body)
        header_bytes = self.header.encode()

        # Calculate checksum
        packet = header_bytes + body
        checksum = calculate_checksum(packet, src_addr, dst_addr)

        # Update checksum in header
        self.header.checksum = checksum
        header_bytes = self.header.encode()

        return header_bytes + body

    @classmethod
    def decode(cls, data: bytes, header: OSPFv3Header) -> 'OSPFv3HelloPacket':
        """Decode Hello packet from bytes"""
        if len(data) < 20:  # Minimum Hello body size
            raise ValueError(f"Insufficient data for Hello packet: {len(data)} < 20")

        # Decode fixed part
        fields = struct.unpack('!IIHHII', data[:20])

        interface_id = fields[0]
        priority_options = fields[1]
        hello_interval = fields[2]
        dead_interval = fields[3]

        # Extract router_priority (top byte) and options (lower 3 bytes)
        router_priority = (priority_options >> 24) & 0xFF
        options = priority_options & 0xFFFFFF
        dr = str(ipaddress.IPv4Address(fields[4]))
        bdr = str(ipaddress.IPv4Address(fields[5]))

        # Decode neighbor list
        neighbors = []
        offset = 20
        while offset + 4 <= len(data):
            neighbor_int = struct.unpack('!I', data[offset:offset + 4])[0]
            neighbors.append(str(ipaddress.IPv4Address(neighbor_int)))
            offset += 4

        return cls(
            header=header,
            interface_id=interface_id,
            router_priority=router_priority,
            options=options,
            hello_interval=hello_interval,
            dead_interval=dead_interval,
            designated_router=dr,
            backup_designated_router=bdr,
            neighbors=neighbors
        )


@dataclass
class LSAHeader:
    """
    LSA Header (RFC 5340 Section A.4.2.1)

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |           LS Age              |           LS Type             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                       Link State ID                           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                    Advertising Router                         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                    LS Sequence Number                         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |        LS Checksum            |             Length            |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """
    ls_age: int = 0
    ls_type: int = 0
    link_state_id: int = 0
    advertising_router: str = "0.0.0.0"
    ls_sequence_number: int = INITIAL_SEQ_NUM
    ls_checksum: int = 0
    length: int = LSA_HEADER_SIZE

    def encode(self) -> bytes:
        """Encode LSA header to bytes"""
        adv_router_int = int(ipaddress.IPv4Address(self.advertising_router))

        return struct.pack(
            '!HHIIIHH',
            self.ls_age,
            self.ls_type,
            self.link_state_id,
            adv_router_int,
            self.ls_sequence_number,
            self.ls_checksum,
            self.length
        )

    @classmethod
    def decode(cls, data: bytes) -> 'LSAHeader':
        """Decode LSA header from bytes"""
        if len(data) < LSA_HEADER_SIZE:
            raise ValueError(f"Insufficient data for LSA header: {len(data)} < {LSA_HEADER_SIZE}")

        fields = struct.unpack('!HHIIIHH', data[:LSA_HEADER_SIZE])

        return cls(
            ls_age=fields[0],
            ls_type=fields[1],
            link_state_id=fields[2],
            advertising_router=str(ipaddress.IPv4Address(fields[3])),
            ls_sequence_number=fields[4],
            ls_checksum=fields[5],
            length=fields[6]
        )

    def get_flooding_scope(self) -> int:
        """Extract flooding scope from LS Type"""
        if self.ls_type & 0x2000:  # S1 bit
            if self.ls_type & 0x4000:  # S2 bit
                return FLOODING_RESERVED
            else:
                return FLOODING_AS
        else:
            if self.ls_type & 0x4000:  # S2 bit
                return FLOODING_AREA
            else:
                return FLOODING_LINK_LOCAL

    def __str__(self) -> str:
        """String representation"""
        lsa_type_name = LSA_TYPE_NAMES.get(self.ls_type, f"Unknown-{self.ls_type:04x}")
        return (f"LSA: Type={lsa_type_name}, "
                f"ID={self.link_state_id}, "
                f"AdvRouter={self.advertising_router}, "
                f"Age={self.ls_age}, "
                f"Seq=0x{self.ls_sequence_number:08x}")


@dataclass
class DatabaseDescriptionPacket:
    """
    OSPFv3 Database Description Packet (RFC 5340 Section A.3.3)
    """
    header: OSPFv3Header = field(default_factory=lambda: OSPFv3Header(packet_type=DATABASE_DESCRIPTION))
    options: int = OPTION_V6 | OPTION_E | OPTION_R
    interface_mtu: int = 1500
    flags: int = 0  # I, M, MS bits
    dd_sequence_number: int = 0
    lsa_headers: List[LSAHeader] = field(default_factory=list)

    def encode(self, src_addr: str, dst_addr: str) -> bytes:
        """Encode DD packet to bytes with checksum"""
        # Combine Reserved (1 byte) + Options (3 bytes) into 4 bytes
        reserved_options = (0 << 24) | (self.options & 0xFFFFFF)
        # Combine Reserved (1 byte) + Flags (1 byte) into 2 bytes
        reserved_flags = (0 << 8) | (self.flags & 0xFF)

        # Encode body: 4 + 2 + 2 + 4 = 12 bytes
        body = struct.pack(
            '!IHHI',
            reserved_options,
            self.interface_mtu,
            reserved_flags,
            self.dd_sequence_number
        )

        # Add LSA headers
        for lsa_header in self.lsa_headers:
            body += lsa_header.encode()

        # Update header
        self.header.packet_length = OSPF_HEADER_SIZE + len(body)
        header_bytes = self.header.encode()

        # Calculate checksum
        packet = header_bytes + body
        checksum = calculate_checksum(packet, src_addr, dst_addr)

        # Update checksum in header
        self.header.checksum = checksum
        header_bytes = self.header.encode()

        return header_bytes + body

    @classmethod
    def decode(cls, data: bytes, header: OSPFv3Header) -> 'DatabaseDescriptionPacket':
        """Decode DD packet from bytes"""
        if len(data) < 12:
            raise ValueError(f"Insufficient data for DD packet: {len(data)} < 12")

        # Decode fixed part (12 bytes)
        fields = struct.unpack('!IHHI', data[:12])

        reserved_options = fields[0]
        options = reserved_options & 0xFFFFFF
        interface_mtu = fields[1]
        reserved_flags = fields[2]
        flags = reserved_flags & 0xFF
        dd_seq = fields[3]

        # Decode LSA headers
        lsa_headers = []
        offset = 12
        while offset + LSA_HEADER_SIZE <= len(data):
            lsa_header = LSAHeader.decode(data[offset:])
            lsa_headers.append(lsa_header)
            offset += LSA_HEADER_SIZE

        return cls(
            header=header,
            options=options,
            interface_mtu=interface_mtu,
            flags=flags,
            dd_sequence_number=dd_seq,
            lsa_headers=lsa_headers
        )


@dataclass
class LinkStateRequest:
    """Link State Request entry"""
    ls_type: int = 0
    link_state_id: int = 0
    advertising_router: str = "0.0.0.0"

    def encode(self) -> bytes:
        """Encode to 12 bytes"""
        adv_router_int = int(ipaddress.IPv4Address(self.advertising_router))
        return struct.pack('!HHI', 0, self.ls_type, self.link_state_id) + struct.pack('!I', adv_router_int)

    @classmethod
    def decode(cls, data: bytes) -> 'LinkStateRequest':
        """Decode from 12 bytes"""
        fields = struct.unpack('!HHI', data[:8])
        adv_router = struct.unpack('!I', data[8:12])[0]

        return cls(
            ls_type=fields[1],
            link_state_id=fields[2],
            advertising_router=str(ipaddress.IPv4Address(adv_router))
        )


@dataclass
class LinkStateRequestPacket:
    """OSPFv3 Link State Request Packet"""
    header: OSPFv3Header = field(default_factory=lambda: OSPFv3Header(packet_type=LINK_STATE_REQUEST))
    requests: List[LinkStateRequest] = field(default_factory=list)

    def encode(self, src_addr: str, dst_addr: str) -> bytes:
        """Encode LS Request packet"""
        body = b''.join(req.encode() for req in self.requests)

        self.header.packet_length = OSPF_HEADER_SIZE + len(body)
        header_bytes = self.header.encode()

        packet = header_bytes + body
        checksum = calculate_checksum(packet, src_addr, dst_addr)

        self.header.checksum = checksum
        header_bytes = self.header.encode()

        return header_bytes + body

    @classmethod
    def decode(cls, data: bytes, header: OSPFv3Header) -> 'LinkStateRequestPacket':
        """Decode LS Request packet"""
        requests = []
        offset = 0
        while offset + 12 <= len(data):
            req = LinkStateRequest.decode(data[offset:offset + 12])
            requests.append(req)
            offset += 12

        return cls(header=header, requests=requests)


def decode_packet(data: bytes) -> Optional[Tuple[OSPFv3Header, object]]:
    """
    Decode OSPFv3 packet from bytes

    Returns:
        Tuple of (header, packet_object) or None if invalid
    """
    if len(data) < OSPF_HEADER_SIZE:
        return None

    try:
        header = OSPFv3Header.decode(data[:OSPF_HEADER_SIZE])
        body = data[OSPF_HEADER_SIZE:header.packet_length]

        if header.packet_type == HELLO_PACKET:
            packet = OSPFv3HelloPacket.decode(body, header)
        elif header.packet_type == DATABASE_DESCRIPTION:
            packet = DatabaseDescriptionPacket.decode(body, header)
        elif header.packet_type == LINK_STATE_REQUEST:
            packet = LinkStateRequestPacket.decode(body, header)
        # TODO: Add other packet types
        else:
            return (header, None)

        return (header, packet)

    except Exception as e:
        print(f"Error decoding packet: {e}")
        return None
