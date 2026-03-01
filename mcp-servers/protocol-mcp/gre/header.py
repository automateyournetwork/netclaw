"""
GRE Header Encoding and Decoding

RFC 2784 - Generic Routing Encapsulation (GRE)
RFC 2890 - Key and Sequence Number Extensions to GRE

GRE Header Format (RFC 2784):
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|C|R|K|S| Reserved0       | Ver |         Protocol Type         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      Checksum (optional)      |       Reserved1 (optional)    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Key (optional)                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 Sequence Number (optional)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
"""

import struct
import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any

from .constants import (
    GRE_FLAG_CHECKSUM,
    GRE_FLAG_KEY,
    GRE_FLAG_SEQUENCE,
    GRE_VERSION_MASK,
    GRE_VERSION_0,
    GRE_HEADER_MIN,
    GRE_CHECKSUM_SIZE,
    GRE_KEY_SIZE,
    GRE_SEQUENCE_SIZE,
    PROTO_IPV4,
    PROTO_IPV6,
    PROTOCOL_NAMES,
    GREError,
)

logger = logging.getLogger("GRE.Header")


@dataclass
class GREHeader:
    """
    GRE Header representation per RFC 2784/2890

    Attributes:
        protocol_type: Ethertype of encapsulated payload (e.g., 0x0800 for IPv4)
        checksum: Optional checksum over GRE header and payload
        key: Optional 32-bit key for traffic flow identification
        sequence_number: Optional sequence number for packet ordering
        version: GRE version (0 for standard GRE)
    """
    protocol_type: int = PROTO_IPV4
    checksum: Optional[int] = None
    key: Optional[int] = None
    sequence_number: Optional[int] = None
    version: int = GRE_VERSION_0

    # Computed properties
    _raw_flags: int = field(default=0, repr=False)

    @property
    def has_checksum(self) -> bool:
        """Check if checksum is present"""
        return self.checksum is not None

    @property
    def has_key(self) -> bool:
        """Check if key is present"""
        return self.key is not None

    @property
    def has_sequence(self) -> bool:
        """Check if sequence number is present"""
        return self.sequence_number is not None

    @property
    def header_length(self) -> int:
        """Calculate total header length based on present fields"""
        length = GRE_HEADER_MIN  # 4 bytes base
        if self.has_checksum:
            length += GRE_CHECKSUM_SIZE  # +4 for checksum + reserved
        if self.has_key:
            length += GRE_KEY_SIZE  # +4 for key
        if self.has_sequence:
            length += GRE_SEQUENCE_SIZE  # +4 for sequence
        return length

    @property
    def flags(self) -> int:
        """Build flags word from header properties"""
        flags = self.version & GRE_VERSION_MASK
        if self.has_checksum:
            flags |= GRE_FLAG_CHECKSUM
        if self.has_key:
            flags |= GRE_FLAG_KEY
        if self.has_sequence:
            flags |= GRE_FLAG_SEQUENCE
        return flags

    @property
    def protocol_name(self) -> str:
        """Get human-readable protocol name"""
        return PROTOCOL_NAMES.get(self.protocol_type, f"0x{self.protocol_type:04X}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "protocol_type": self.protocol_type,
            "protocol_name": self.protocol_name,
            "checksum": self.checksum,
            "key": self.key,
            "sequence_number": self.sequence_number,
            "version": self.version,
            "header_length": self.header_length,
            "flags": {
                "checksum_present": self.has_checksum,
                "key_present": self.has_key,
                "sequence_present": self.has_sequence,
            }
        }

    def __str__(self) -> str:
        parts = [f"GRE[{self.protocol_name}]"]
        if self.has_key:
            parts.append(f"key={self.key}")
        if self.has_sequence:
            parts.append(f"seq={self.sequence_number}")
        if self.has_checksum:
            parts.append(f"csum=0x{self.checksum:04X}")
        return " ".join(parts)


def calculate_gre_checksum(data: bytes) -> int:
    """
    Calculate GRE checksum (IP one's complement checksum)

    The checksum is the 16-bit one's complement of the one's complement
    sum of all 16-bit words in the GRE header and payload.

    Args:
        data: Bytes to checksum (GRE header with zero checksum + payload)

    Returns:
        16-bit checksum value
    """
    if len(data) % 2 == 1:
        data += b'\x00'  # Pad to even length

    checksum = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        checksum += word

    # Fold 32-bit sum to 16 bits
    while checksum >> 16:
        checksum = (checksum & 0xFFFF) + (checksum >> 16)

    # One's complement
    return ~checksum & 0xFFFF


def encode_gre_header(
    protocol_type: int = PROTO_IPV4,
    checksum: bool = False,
    key: Optional[int] = None,
    sequence_number: Optional[int] = None,
    payload: bytes = b''
) -> Tuple[bytes, GREHeader]:
    """
    Encode a GRE header

    Args:
        protocol_type: Ethertype of payload (default IPv4)
        checksum: Whether to include checksum
        key: Optional 32-bit key value
        sequence_number: Optional sequence number
        payload: Payload data (needed for checksum calculation)

    Returns:
        Tuple of (encoded header bytes, GREHeader object)
    """
    # Build flags
    flags = GRE_VERSION_0
    if checksum:
        flags |= GRE_FLAG_CHECKSUM
    if key is not None:
        flags |= GRE_FLAG_KEY
    if sequence_number is not None:
        flags |= GRE_FLAG_SEQUENCE

    # Pack base header: flags (2 bytes) + protocol type (2 bytes)
    # '!' = network byte order (big-endian)
    header = struct.pack('!HH', flags, protocol_type)

    # Add checksum field (placeholder if calculating)
    checksum_value = None
    if checksum:
        header += struct.pack('!HH', 0, 0)  # Checksum + Reserved1

    # Add key if present
    if key is not None:
        header += struct.pack('!I', key)

    # Add sequence number if present
    if sequence_number is not None:
        header += struct.pack('!I', sequence_number)

    # Calculate checksum if requested
    if checksum:
        checksum_value = calculate_gre_checksum(header + payload)
        # Repack header with actual checksum
        header = struct.pack('!HH', flags, protocol_type)
        header += struct.pack('!HH', checksum_value, 0)
        if key is not None:
            header += struct.pack('!I', key)
        if sequence_number is not None:
            header += struct.pack('!I', sequence_number)

    # Create header object
    gre_header = GREHeader(
        protocol_type=protocol_type,
        checksum=checksum_value,
        key=key,
        sequence_number=sequence_number,
        version=GRE_VERSION_0
    )

    logger.debug(f"Encoded GRE header: {gre_header} ({len(header)} bytes)")
    return header, gre_header


def decode_gre_header(data: bytes) -> Tuple[GREHeader, int, Optional[int]]:
    """
    Decode a GRE header from raw bytes

    Args:
        data: Raw bytes containing GRE header (and possibly payload)

    Returns:
        Tuple of (GREHeader object, payload offset, error code or None)

    Raises:
        ValueError: If header is invalid or too short
    """
    if len(data) < GRE_HEADER_MIN:
        logger.error(f"GRE header too short: {len(data)} < {GRE_HEADER_MIN}")
        return GREHeader(), 0, GREError.INVALID_HEADER

    # Unpack base header
    flags, protocol_type = struct.unpack('!HH', data[:4])
    offset = 4

    # Extract version
    version = flags & GRE_VERSION_MASK
    if version != GRE_VERSION_0:
        logger.warning(f"Unsupported GRE version: {version}")
        return GREHeader(version=version), offset, GREError.UNSUPPORTED_VERSION

    # Check for optional fields
    has_checksum = bool(flags & GRE_FLAG_CHECKSUM)
    has_key = bool(flags & GRE_FLAG_KEY)
    has_sequence = bool(flags & GRE_FLAG_SEQUENCE)

    checksum_value = None
    key_value = None
    sequence_value = None

    # Parse checksum field
    if has_checksum:
        if len(data) < offset + 4:
            return GREHeader(), offset, GREError.INVALID_HEADER
        checksum_value, reserved = struct.unpack('!HH', data[offset:offset + 4])
        offset += 4

    # Parse key field
    if has_key:
        if len(data) < offset + 4:
            return GREHeader(), offset, GREError.INVALID_HEADER
        key_value, = struct.unpack('!I', data[offset:offset + 4])
        offset += 4

    # Parse sequence number field
    if has_sequence:
        if len(data) < offset + 4:
            return GREHeader(), offset, GREError.INVALID_HEADER
        sequence_value, = struct.unpack('!I', data[offset:offset + 4])
        offset += 4

    # Create header object
    header = GREHeader(
        protocol_type=protocol_type,
        checksum=checksum_value,
        key=key_value,
        sequence_number=sequence_value,
        version=version,
        _raw_flags=flags
    )

    # Verify checksum if present
    if has_checksum and checksum_value is not None:
        # Zero out checksum field for verification
        verify_data = data[:4] + struct.pack('!HH', 0, 0) + data[8:]
        calculated = calculate_gre_checksum(verify_data)
        if calculated != checksum_value:
            logger.warning(f"GRE checksum mismatch: expected 0x{checksum_value:04X}, got 0x{calculated:04X}")
            return header, offset, GREError.CHECKSUM_MISMATCH

    logger.debug(f"Decoded GRE header: {header} (payload at offset {offset})")
    return header, offset, None


def encapsulate_packet(
    payload: bytes,
    protocol_type: int = PROTO_IPV4,
    key: Optional[int] = None,
    sequence_number: Optional[int] = None,
    use_checksum: bool = False
) -> bytes:
    """
    Encapsulate a packet in GRE

    Args:
        payload: The packet to encapsulate
        protocol_type: Ethertype of the payload
        key: Optional GRE key
        sequence_number: Optional sequence number
        use_checksum: Whether to calculate and include checksum

    Returns:
        GRE-encapsulated packet (header + payload)
    """
    header_bytes, _ = encode_gre_header(
        protocol_type=protocol_type,
        checksum=use_checksum,
        key=key,
        sequence_number=sequence_number,
        payload=payload
    )
    return header_bytes + payload


def decapsulate_packet(data: bytes, expected_key: Optional[int] = None) -> Tuple[bytes, GREHeader, Optional[int]]:
    """
    Decapsulate a GRE packet

    Args:
        data: Raw GRE packet (header + payload)
        expected_key: If set, verify the key matches

    Returns:
        Tuple of (payload bytes, GREHeader, error code or None)
    """
    header, offset, error = decode_gre_header(data)
    if error:
        return b'', header, error

    # Verify key if expected
    if expected_key is not None and header.key != expected_key:
        logger.warning(f"GRE key mismatch: expected {expected_key}, got {header.key}")
        return b'', header, GREError.KEY_MISMATCH

    payload = data[offset:]
    return payload, header, None


# Convenience functions for common encapsulations

def encapsulate_ipv4(payload: bytes, key: Optional[int] = None, seq: Optional[int] = None) -> bytes:
    """Encapsulate an IPv4 packet in GRE"""
    return encapsulate_packet(payload, PROTO_IPV4, key, seq)


def encapsulate_ipv6(payload: bytes, key: Optional[int] = None, seq: Optional[int] = None) -> bytes:
    """Encapsulate an IPv6 packet in GRE"""
    return encapsulate_packet(payload, PROTO_IPV6, key, seq)
