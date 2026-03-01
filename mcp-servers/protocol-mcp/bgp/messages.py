"""
BGP Message Encoding/Decoding (RFC 4271 Section 4)

This module implements all BGP-4 message types:
- OPEN (Type 1)
- UPDATE (Type 2)
- NOTIFICATION (Type 3)
- KEEPALIVE (Type 4)
- ROUTE-REFRESH (Type 5, RFC 2918)
"""

import struct
import socket
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field

from .constants import *


class BGPMessage:
    """
    Base class for all BGP messages (RFC 4271 Section 4.1)

    All BGP messages have a fixed 19-byte header:
    - Marker (16 bytes): All 1s for no authentication
    - Length (2 bytes): Total message length including header
    - Type (1 byte): Message type code
    """

    def __init__(self, msg_type: int):
        self.msg_type = msg_type

    def encode(self) -> bytes:
        """
        Encode message to wire format

        Returns:
            Encoded message bytes
        """
        raise NotImplementedError("Subclasses must implement encode()")

    @staticmethod
    def decode(data: bytes) -> Optional['BGPMessage']:
        """
        Decode message from wire format

        Args:
            data: Message bytes

        Returns:
            Decoded BGPMessage subclass or None if invalid
        """
        if len(data) < BGP_HEADER_SIZE:
            return None

        # Parse header
        marker = data[0:16]
        length = struct.unpack('!H', data[16:18])[0]
        msg_type = data[18]

        # Validate marker
        if marker != BGP_MARKER:
            return None

        # Validate length
        if length < BGP_HEADER_SIZE or length > BGP_MAX_MESSAGE_SIZE:
            return None

        if len(data) < length:
            return None

        # Dispatch to specific message type
        if msg_type == MSG_OPEN:
            return BGPOpen.decode(data)
        elif msg_type == MSG_UPDATE:
            return BGPUpdate.decode(data)
        elif msg_type == MSG_NOTIFICATION:
            return BGPNotification.decode(data)
        elif msg_type == MSG_KEEPALIVE:
            return BGPKeepalive.decode(data)
        elif msg_type == MSG_ROUTE_REFRESH:
            return BGPRouteRefresh.decode(data)
        else:
            return None

    def _build_header(self, payload: bytes) -> bytes:
        """
        Build BGP message header

        Args:
            payload: Message payload (after header)

        Returns:
            Complete message with header
        """
        length = BGP_HEADER_SIZE + len(payload)
        header = BGP_MARKER + struct.pack('!HB', length, self.msg_type)
        return header + payload

    @staticmethod
    def parse_header(data: bytes) -> Optional[Tuple[int, int, bytes]]:
        """
        Parse BGP message header

        Args:
            data: Message bytes

        Returns:
            Tuple of (message_type, length, payload) or None if invalid
        """
        if len(data) < BGP_HEADER_SIZE:
            return None

        marker = data[0:16]
        length = struct.unpack('!H', data[16:18])[0]
        msg_type = data[18]

        if marker != BGP_MARKER:
            return None

        if length < BGP_HEADER_SIZE or length > BGP_MAX_MESSAGE_SIZE:
            return None

        if len(data) < length:
            return None

        payload = data[BGP_HEADER_SIZE:length]
        return (msg_type, length, payload)


@dataclass
class BGPCapability:
    """
    BGP Capability (RFC 5492)

    Used in OPEN message Optional Parameters
    """
    code: int
    value: bytes

    def encode(self) -> bytes:
        """Encode capability as TLV"""
        return struct.pack('!BB', self.code, len(self.value)) + self.value

    @staticmethod
    def decode(data: bytes) -> Tuple[Optional['BGPCapability'], int]:
        """
        Decode capability from bytes

        Returns:
            (BGPCapability, bytes_consumed) or (None, 0)
        """
        if len(data) < 2:
            return (None, 0)

        code = data[0]
        length = data[1]

        if len(data) < 2 + length:
            return (None, 0)

        value = data[2:2+length]
        return (BGPCapability(code, value), 2 + length)

    @staticmethod
    def encode_multiprotocol(afi: int, safi: int) -> 'BGPCapability':
        """Encode Multiprotocol capability (Code 1, RFC 4760)"""
        value = struct.pack('!HBB', afi, 0, safi)  # Reserved byte = 0
        return BGPCapability(CAP_MULTIPROTOCOL, value)

    @staticmethod
    def encode_route_refresh() -> 'BGPCapability':
        """Encode Route Refresh capability (Code 2, RFC 2918)"""
        return BGPCapability(CAP_ROUTE_REFRESH, b'')

    @staticmethod
    def encode_four_octet_as(asn: int) -> 'BGPCapability':
        """Encode 4-byte AS capability (Code 65, RFC 6793)"""
        value = struct.pack('!I', asn)
        return BGPCapability(CAP_FOUR_OCTET_AS, value)

    @staticmethod
    def encode_add_path(afi: int, safi: int, send: bool, receive: bool) -> 'BGPCapability':
        """Encode ADD-PATH capability (Code 69, RFC 7911)"""
        flags = 0
        if send:
            flags |= 0x01
        if receive:
            flags |= 0x02
        value = struct.pack('!HBB', afi, safi, flags)
        return BGPCapability(CAP_ADD_PATH, value)


class BGPOpen(BGPMessage):
    """
    BGP OPEN Message (RFC 4271 Section 4.2)

    Format:
    - Version (1 byte): BGP version (4)
    - My Autonomous System (2 bytes): Sender's AS number
    - Hold Time (2 bytes): Proposed hold time in seconds
    - BGP Identifier (4 bytes): Sender's BGP router ID
    - Optional Parameters Length (1 byte)
    - Optional Parameters (variable): Capabilities
    """

    def __init__(self, version: int, my_as: int, hold_time: int,
                 bgp_identifier: str, capabilities: List[BGPCapability] = None):
        super().__init__(MSG_OPEN)
        self.version = version
        self.my_as = my_as
        self.hold_time = hold_time
        self.bgp_identifier = bgp_identifier  # IPv4 address string
        self.capabilities = capabilities or []

    def encode(self) -> bytes:
        """Encode OPEN message to wire format"""
        # Convert BGP identifier to 32-bit int
        bgp_id_int = struct.unpack('!I', socket.inet_aton(self.bgp_identifier))[0]

        # Encode capabilities as Optional Parameters
        opt_params = b''
        if self.capabilities:
            # Capabilities are wrapped in Optional Parameter Type 2
            cap_data = b''.join(cap.encode() for cap in self.capabilities)
            # Param Type=2 (Capability), Param Length, Capability data
            opt_params = struct.pack('!BB', 2, len(cap_data)) + cap_data

        opt_param_len = len(opt_params)

        # Build OPEN payload
        payload = struct.pack('!BHH I B',
                             self.version,
                             self.my_as if self.my_as <= 65535 else AS_TRANS,
                             self.hold_time,
                             bgp_id_int,
                             opt_param_len)
        payload += opt_params

        return self._build_header(payload)

    @staticmethod
    def decode(data: bytes) -> Optional['BGPOpen']:
        """Decode OPEN message from wire format"""
        header_result = BGPMessage.parse_header(data)
        if not header_result:
            return None

        msg_type, length, payload = header_result

        if msg_type != MSG_OPEN:
            return None

        if len(payload) < 10:  # Minimum OPEN size
            return None

        # Parse OPEN fields
        version = payload[0]
        my_as = struct.unpack('!H', payload[1:3])[0]
        hold_time = struct.unpack('!H', payload[3:5])[0]
        bgp_id_int = struct.unpack('!I', payload[5:9])[0]
        bgp_identifier = socket.inet_ntoa(struct.pack('!I', bgp_id_int))
        opt_param_len = payload[9]

        if len(payload) < 10 + opt_param_len:
            return None

        # Parse Optional Parameters (Capabilities)
        capabilities = []
        offset = 10
        while offset < 10 + opt_param_len:
            if offset + 2 > len(payload):
                break

            param_type = payload[offset]
            param_len = payload[offset + 1]

            if offset + 2 + param_len > len(payload):
                break

            if param_type == 2:  # Capability parameter
                # Parse capabilities
                cap_offset = offset + 2
                cap_end = offset + 2 + param_len

                while cap_offset < cap_end:
                    cap, consumed = BGPCapability.decode(payload[cap_offset:cap_end])
                    if cap:
                        capabilities.append(cap)
                        cap_offset += consumed
                    else:
                        break

            offset += 2 + param_len

        return BGPOpen(version, my_as, hold_time, bgp_identifier, capabilities)


class BGPKeepalive(BGPMessage):
    """
    BGP KEEPALIVE Message (RFC 4271 Section 4.4)

    KEEPALIVE is just a 19-byte header with no payload
    """

    def __init__(self):
        super().__init__(MSG_KEEPALIVE)

    def encode(self) -> bytes:
        """Encode KEEPALIVE message (header only)"""
        return self._build_header(b'')

    @staticmethod
    def decode(data: bytes) -> Optional['BGPKeepalive']:
        """Decode KEEPALIVE message"""
        header_result = BGPMessage.parse_header(data)
        if not header_result:
            return None

        msg_type, length, payload = header_result

        if msg_type != MSG_KEEPALIVE:
            return None

        if len(payload) != 0:
            return None

        return BGPKeepalive()


class BGPNotification(BGPMessage):
    """
    BGP NOTIFICATION Message (RFC 4271 Section 4.5)

    Format:
    - Error Code (1 byte)
    - Error Subcode (1 byte)
    - Data (variable): Error-specific data
    """

    def __init__(self, error_code: int, error_subcode: int, data: bytes = b''):
        super().__init__(MSG_NOTIFICATION)
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.data = data

    def encode(self) -> bytes:
        """Encode NOTIFICATION message"""
        payload = struct.pack('!BB', self.error_code, self.error_subcode) + self.data
        return self._build_header(payload)

    @staticmethod
    def decode(data: bytes) -> Optional['BGPNotification']:
        """Decode NOTIFICATION message"""
        header_result = BGPMessage.parse_header(data)
        if not header_result:
            return None

        msg_type, length, payload = header_result

        if msg_type != MSG_NOTIFICATION:
            return None

        if len(payload) < 2:
            return None

        error_code = payload[0]
        error_subcode = payload[1]
        error_data = payload[2:] if len(payload) > 2 else b''

        return BGPNotification(error_code, error_subcode, error_data)

    def get_error_name(self) -> str:
        """Get human-readable error name"""
        return ERROR_CODE_NAMES.get(self.error_code, f"Unknown Error {self.error_code}")


class BGPUpdate(BGPMessage):
    """
    BGP UPDATE Message (RFC 4271 Section 4.3)

    Format:
    - Withdrawn Routes Length (2 bytes)
    - Withdrawn Routes (variable): Prefixes to remove
    - Total Path Attribute Length (2 bytes)
    - Path Attributes (variable)
    - Network Layer Reachability Information (variable): Prefixes to add/update
    """

    def __init__(self, withdrawn_routes: List[str] = None,
                 path_attributes: Dict[int, Any] = None,
                 nlri: List[str] = None):
        super().__init__(MSG_UPDATE)
        self.withdrawn_routes = withdrawn_routes or []
        self.path_attributes = path_attributes or {}
        self.nlri = nlri or []

    def encode(self) -> bytes:
        """Encode UPDATE message with path attributes"""
        # Encode withdrawn routes
        withdrawn_data = self._encode_prefixes(self.withdrawn_routes)
        withdrawn_len = len(withdrawn_data)

        # Encode path attributes
        from .attributes import encode_path_attributes
        attr_data = encode_path_attributes(self.path_attributes)
        attr_len = len(attr_data)

        # Encode NLRI
        nlri_data = self._encode_prefixes(self.nlri)

        # Build UPDATE payload
        payload = struct.pack('!H', withdrawn_len) + withdrawn_data
        payload += struct.pack('!H', attr_len) + attr_data
        payload += nlri_data

        return self._build_header(payload)

    @staticmethod
    def decode(data: bytes) -> Optional['BGPUpdate']:
        """Decode UPDATE message with path attributes"""
        header_result = BGPMessage.parse_header(data)
        if not header_result:
            return None

        msg_type, length, payload = header_result

        if msg_type != MSG_UPDATE:
            return None

        offset = 0

        # Parse withdrawn routes
        if len(payload) < 2:
            return None
        withdrawn_len = struct.unpack('!H', payload[offset:offset+2])[0]
        offset += 2

        if len(payload) < offset + withdrawn_len:
            return None
        withdrawn_data = payload[offset:offset+withdrawn_len]
        withdrawn_routes = BGPUpdate._decode_prefixes(withdrawn_data)
        offset += withdrawn_len

        # Parse path attributes
        if len(payload) < offset + 2:
            return None
        attr_len = struct.unpack('!H', payload[offset:offset+2])[0]
        offset += 2

        if len(payload) < offset + attr_len:
            return None
        attr_data = payload[offset:offset+attr_len]
        from .attributes import decode_path_attributes
        path_attributes = decode_path_attributes(attr_data)
        offset += attr_len

        # Parse NLRI
        nlri_data = payload[offset:]
        nlri = BGPUpdate._decode_prefixes(nlri_data)

        return BGPUpdate(withdrawn_routes, path_attributes, nlri)

    @staticmethod
    def _encode_prefixes(prefixes: List[str]) -> bytes:
        """
        Encode list of IPv4 prefixes for NLRI or withdrawn routes

        Format: <length> <prefix> where length is prefix bits
        Only significant octets are included
        """
        data = b''
        for prefix in prefixes:
            # Parse prefix (e.g., "203.0.113.0/24")
            if '/' in prefix:
                ip, prefix_len_str = prefix.split('/')
                prefix_len = int(prefix_len_str)
            else:
                ip = prefix
                prefix_len = 32

            # Convert IP to bytes
            ip_bytes = socket.inet_aton(ip)

            # Calculate number of significant octets
            num_octets = (prefix_len + 7) // 8

            # Encode: <length> <prefix bytes>
            data += struct.pack('!B', prefix_len) + ip_bytes[:num_octets]

        return data

    @staticmethod
    def _decode_prefixes(data: bytes) -> List[str]:
        """
        Decode IPv4 prefixes from NLRI or withdrawn routes

        Returns:
            List of prefix strings (e.g., ["203.0.113.0/24"])
        """
        prefixes = []
        offset = 0

        while offset < len(data):
            if offset >= len(data):
                break

            # Read prefix length
            prefix_len = data[offset]
            offset += 1

            # Calculate number of octets
            num_octets = (prefix_len + 7) // 8

            if offset + num_octets > len(data):
                break

            # Read prefix bytes and pad to 4 bytes
            prefix_bytes = data[offset:offset+num_octets]
            prefix_bytes += b'\x00' * (4 - num_octets)  # Pad to 4 bytes
            offset += num_octets

            # Convert to IP string
            ip = socket.inet_ntoa(prefix_bytes)
            prefixes.append(f"{ip}/{prefix_len}")

        return prefixes


class BGPRouteRefresh(BGPMessage):
    """
    BGP ROUTE-REFRESH Message (RFC 2918)

    Format:
    - AFI (2 bytes): Address Family Identifier
    - Reserved (1 byte): Must be 0
    - SAFI (1 byte): Subsequent Address Family Identifier
    """

    def __init__(self, afi: int, safi: int):
        super().__init__(MSG_ROUTE_REFRESH)
        self.afi = afi
        self.safi = safi

    def encode(self) -> bytes:
        """Encode ROUTE-REFRESH message"""
        payload = struct.pack('!HBB', self.afi, 0, self.safi)
        return self._build_header(payload)

    @staticmethod
    def decode(data: bytes) -> Optional['BGPRouteRefresh']:
        """Decode ROUTE-REFRESH message"""
        header_result = BGPMessage.parse_header(data)
        if not header_result:
            return None

        msg_type, length, payload = header_result

        if msg_type != MSG_ROUTE_REFRESH:
            return None

        if len(payload) != 4:
            return None

        afi = struct.unpack('!H', payload[0:2])[0]
        # Reserved byte at payload[2] is ignored
        safi = payload[3]

        return BGPRouteRefresh(afi, safi)
