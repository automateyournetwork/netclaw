"""
BGP Path Attributes (RFC 4271 Section 5)

This module implements all BGP path attributes including:
- Well-known mandatory: ORIGIN, AS_PATH, NEXT_HOP
- Well-known discretionary: LOCAL_PREF, ATOMIC_AGGREGATE
- Optional transitive: AGGREGATOR, COMMUNITIES
- Optional non-transitive: MED, ORIGINATOR_ID, CLUSTER_LIST
- Multiprotocol: MP_REACH_NLRI, MP_UNREACH_NLRI
"""

import struct
import socket
from typing import Optional, List, Tuple, Any
from abc import ABC, abstractmethod

from .constants import *


class PathAttribute(ABC):
    """
    Base class for BGP path attributes (RFC 4271 Section 5)

    Attribute format:
    - Flags (1 byte): Optional, Transitive, Partial, Extended
    - Type Code (1 byte)
    - Length (1 or 2 bytes): Extended length if flag bit set
    - Value (variable)
    """

    def __init__(self, type_code: int, flags: int, value: bytes = b''):
        self.type_code = type_code
        self.flags = flags
        self.value = value

    @abstractmethod
    def encode_value(self) -> bytes:
        """Encode attribute-specific value"""
        pass

    @abstractmethod
    def decode_value(self, data: bytes) -> bool:
        """Decode attribute-specific value, return True if successful"""
        pass

    def encode(self) -> bytes:
        """
        Encode attribute to wire format

        Returns:
            Encoded attribute bytes
        """
        value = self.encode_value()
        length = len(value)

        # Check if extended length needed (length > 255)
        if length > 255:
            flags = self.flags | ATTR_FLAG_EXTENDED
            return struct.pack('!BBH', flags, self.type_code, length) + value
        else:
            flags = self.flags & ~ATTR_FLAG_EXTENDED
            return struct.pack('!BBB', flags, self.type_code, length) + value

    @staticmethod
    def decode(data: bytes) -> Tuple[Optional['PathAttribute'], int]:
        """
        Decode path attribute from bytes

        Args:
            data: Attribute bytes

        Returns:
            (PathAttribute instance, bytes_consumed) or (None, 0)
        """
        if len(data) < 3:
            return (None, 0)

        flags = data[0]
        type_code = data[1]

        # Check for extended length
        if flags & ATTR_FLAG_EXTENDED:
            if len(data) < 4:
                return (None, 0)
            length = struct.unpack('!H', data[2:4])[0]
            value_offset = 4
        else:
            length = data[2]
            value_offset = 3

        if len(data) < value_offset + length:
            return (None, 0)

        value = data[value_offset:value_offset + length]

        # Dispatch to specific attribute class
        attr = AttributeFactory.create(type_code, flags, value)
        if attr and attr.decode_value(value):
            return (attr, value_offset + length)
        else:
            return (None, 0)


class OriginAttribute(PathAttribute):
    """
    ORIGIN Attribute (Type 1, RFC 4271 Section 5.1.1)

    Well-known mandatory attribute
    Values: IGP (0), EGP (1), INCOMPLETE (2)
    """

    def __init__(self, origin: int):
        # Well-known mandatory: Transitive, not optional
        flags = ATTR_FLAG_TRANSITIVE
        super().__init__(ATTR_ORIGIN, flags)
        self.origin = origin

    def encode_value(self) -> bytes:
        return struct.pack('!B', self.origin)

    def decode_value(self, data: bytes) -> bool:
        if len(data) != 1:
            return False
        self.origin = data[0]
        if self.origin not in (ORIGIN_IGP, ORIGIN_EGP, ORIGIN_INCOMPLETE):
            return False
        return True

    def __repr__(self) -> str:
        return f"ORIGIN({ORIGIN_NAMES.get(self.origin, self.origin)})"


class ASPathAttribute(PathAttribute):
    """
    AS_PATH Attribute (Type 2, RFC 4271 Section 5.1.2)

    Well-known mandatory attribute
    Contains AS_SEQUENCE and/or AS_SET segments
    """

    def __init__(self, segments: List[Tuple[int, List[int]]] = None):
        # Well-known mandatory: Transitive, not optional
        flags = ATTR_FLAG_TRANSITIVE
        super().__init__(ATTR_AS_PATH, flags)
        # segments: List of (segment_type, [ASNs])
        self.segments = segments or []

    def encode_value(self, four_byte_as: bool = True) -> bytes:
        """
        Encode AS_PATH value.

        Args:
            four_byte_as: Use 4-byte AS numbers (RFC 6793). Default True since
                          most modern implementations support it.
        """
        data = b''
        for seg_type, as_list in self.segments:
            data += struct.pack('!BB', seg_type, len(as_list))
            for asn in as_list:
                if four_byte_as:
                    data += struct.pack('!I', asn)  # 4-byte AS
                else:
                    data += struct.pack('!H', asn if asn <= 65535 else AS_TRANS)
        return data

    def decode_value(self, data: bytes, four_byte_as: bool = True) -> bool:
        """
        Decode AS_PATH value.

        Args:
            data: Attribute value bytes
            four_byte_as: Expect 4-byte AS numbers (RFC 6793). Default True.
        """
        self.segments = []
        offset = 0
        as_size = 4 if four_byte_as else 2

        while offset < len(data):
            if offset + 2 > len(data):
                return False

            seg_type = data[offset]
            seg_len = data[offset + 1]
            offset += 2

            if offset + seg_len * as_size > len(data):
                return False

            as_list = []
            for i in range(seg_len):
                if four_byte_as:
                    asn = struct.unpack('!I', data[offset:offset+4])[0]
                    offset += 4
                else:
                    asn = struct.unpack('!H', data[offset:offset+2])[0]
                    offset += 2
                as_list.append(asn)

            self.segments.append((seg_type, as_list))

        return True

    def prepend(self, asn: int) -> None:
        """
        Prepend AS number to AS_PATH (RFC 4271 Section 5.1.2)

        Adds ASN to beginning of first AS_SEQUENCE, or creates new AS_SEQUENCE
        """
        if self.segments and self.segments[0][0] == AS_SEQUENCE:
            # Prepend to existing AS_SEQUENCE
            seg_type, as_list = self.segments[0]
            as_list.insert(0, asn)
        else:
            # Create new AS_SEQUENCE at beginning
            self.segments.insert(0, (AS_SEQUENCE, [asn]))

    def length(self) -> int:
        """
        Calculate AS_PATH length for best path selection

        AS_SET counts as 1, AS_SEQUENCE counts each AS
        """
        total = 0
        for seg_type, as_list in self.segments:
            if seg_type == AS_SET:
                total += 1
            else:  # AS_SEQUENCE
                total += len(as_list)
        return total

    def contains_as(self, asn: int) -> bool:
        """Check if AS_PATH contains specific AS number"""
        for seg_type, as_list in self.segments:
            if asn in as_list:
                return True
        return False

    @property
    def as_path(self) -> List[int]:
        """
        Get flattened AS_PATH as a list of AS numbers

        Returns all AS numbers from all AS_SEQUENCE segments in order.
        AS_SET segments are included but order within set is arbitrary.
        """
        path = []
        for seg_type, as_list in self.segments:
            path.extend(as_list)
        return path

    def __repr__(self) -> str:
        parts = []
        for seg_type, as_list in self.segments:
            if seg_type == AS_SET:
                parts.append("{" + " ".join(str(a) for a in as_list) + "}")
            else:
                parts.append(" ".join(str(a) for a in as_list))
        return f"AS_PATH({' '.join(parts)})"


class NextHopAttribute(PathAttribute):
    """
    NEXT_HOP Attribute (Type 3, RFC 4271 Section 5.1.3)

    Well-known mandatory attribute (for IPv4)
    Contains IPv4 address of next hop
    """

    def __init__(self, next_hop: str):
        # Well-known mandatory: Transitive, not optional
        flags = ATTR_FLAG_TRANSITIVE
        super().__init__(ATTR_NEXT_HOP, flags)
        self.next_hop = next_hop  # IPv4 address string

    def encode_value(self) -> bytes:
        return socket.inet_aton(self.next_hop)

    def decode_value(self, data: bytes) -> bool:
        if len(data) != 4:
            return False
        self.next_hop = socket.inet_ntoa(data)
        return True

    def __repr__(self) -> str:
        return f"NEXT_HOP({self.next_hop})"


class MEDAttribute(PathAttribute):
    """
    MULTI_EXIT_DISC (MED) Attribute (Type 4, RFC 4271 Section 5.1.4)

    Optional non-transitive attribute
    32-bit metric, lower is better
    """

    def __init__(self, med: int):
        # Optional non-transitive
        flags = ATTR_FLAG_OPTIONAL
        super().__init__(ATTR_MED, flags)
        self.med = med

    def encode_value(self) -> bytes:
        return struct.pack('!I', self.med)

    def decode_value(self, data: bytes) -> bool:
        if len(data) != 4:
            return False
        self.med = struct.unpack('!I', data)[0]
        return True

    def __repr__(self) -> str:
        return f"MED({self.med})"


class LocalPrefAttribute(PathAttribute):
    """
    LOCAL_PREF Attribute (Type 5, RFC 4271 Section 5.1.5)

    Well-known discretionary attribute (iBGP only)
    32-bit preference, higher is better
    """

    def __init__(self, local_pref: int):
        # Well-known discretionary: Transitive, not optional
        flags = ATTR_FLAG_TRANSITIVE
        super().__init__(ATTR_LOCAL_PREF, flags)
        self.local_pref = local_pref

    def encode_value(self) -> bytes:
        return struct.pack('!I', self.local_pref)

    def decode_value(self, data: bytes) -> bool:
        if len(data) != 4:
            return False
        self.local_pref = struct.unpack('!I', data)[0]
        return True

    def __repr__(self) -> str:
        return f"LOCAL_PREF({self.local_pref})"


class AtomicAggregateAttribute(PathAttribute):
    """
    ATOMIC_AGGREGATE Attribute (Type 6, RFC 4271 Section 5.1.6)

    Well-known discretionary attribute
    Zero-length attribute (flag only)
    """

    def __init__(self):
        # Well-known discretionary: Transitive, not optional
        flags = ATTR_FLAG_TRANSITIVE
        super().__init__(ATTR_ATOMIC_AGGREGATE, flags)

    def encode_value(self) -> bytes:
        return b''

    def decode_value(self, data: bytes) -> bool:
        return len(data) == 0

    def __repr__(self) -> str:
        return "ATOMIC_AGGREGATE"


class AggregatorAttribute(PathAttribute):
    """
    AGGREGATOR Attribute (Type 7, RFC 4271 Section 5.1.7)

    Optional transitive attribute
    Contains AS number and Router ID of aggregator
    """

    def __init__(self, asn: int, router_id: str):
        # Optional transitive
        flags = ATTR_FLAG_OPTIONAL | ATTR_FLAG_TRANSITIVE
        super().__init__(ATTR_AGGREGATOR, flags)
        self.asn = asn
        self.router_id = router_id  # IPv4 address string

    def encode_value(self) -> bytes:
        asn_bytes = struct.pack('!H', self.asn if self.asn <= 65535 else AS_TRANS)
        router_id_bytes = socket.inet_aton(self.router_id)
        return asn_bytes + router_id_bytes

    def decode_value(self, data: bytes) -> bool:
        if len(data) != 6:
            return False
        self.asn = struct.unpack('!H', data[0:2])[0]
        self.router_id = socket.inet_ntoa(data[2:6])
        return True

    def __repr__(self) -> str:
        return f"AGGREGATOR(AS{self.asn}, {self.router_id})"


class CommunitiesAttribute(PathAttribute):
    """
    COMMUNITIES Attribute (Type 8, RFC 1997)

    Optional transitive attribute
    Set of 32-bit community values
    Format: AS:Value (16 bits each)
    """

    def __init__(self, communities: List[int] = None):
        # Optional transitive
        flags = ATTR_FLAG_OPTIONAL | ATTR_FLAG_TRANSITIVE
        super().__init__(ATTR_COMMUNITIES, flags)
        self.communities = communities or []

    def encode_value(self) -> bytes:
        data = b''
        for comm in self.communities:
            data += struct.pack('!I', comm)
        return data

    def decode_value(self, data: bytes) -> bool:
        if len(data) % 4 != 0:
            return False

        self.communities = []
        for i in range(0, len(data), 4):
            comm = struct.unpack('!I', data[i:i+4])[0]
            self.communities.append(comm)

        return True

    def add(self, community: int) -> None:
        """Add community if not already present"""
        if community not in self.communities:
            self.communities.append(community)

    def remove(self, community: int) -> None:
        """Remove community if present"""
        if community in self.communities:
            self.communities.remove(community)

    def has(self, community: int) -> bool:
        """Check if community is present"""
        return community in self.communities

    def __repr__(self) -> str:
        comm_strs = []
        for comm in self.communities:
            if comm in WELL_KNOWN_COMMUNITIES:
                comm_strs.append(WELL_KNOWN_COMMUNITIES[comm])
            else:
                # Format as AS:Value
                asn = (comm >> 16) & 0xFFFF
                val = comm & 0xFFFF
                comm_strs.append(f"{asn}:{val}")
        return f"COMMUNITIES({', '.join(comm_strs)})"


class OriginatorIDAttribute(PathAttribute):
    """
    ORIGINATOR_ID Attribute (Type 9, RFC 4456)

    Optional non-transitive attribute for route reflection
    Contains Router ID of route originator (for loop prevention)
    """

    def __init__(self, originator_id: str):
        # Optional non-transitive
        flags = ATTR_FLAG_OPTIONAL
        super().__init__(ATTR_ORIGINATOR_ID, flags)
        self.originator_id = originator_id  # IPv4 address string

    def encode_value(self) -> bytes:
        return socket.inet_aton(self.originator_id)

    def decode_value(self, data: bytes) -> bool:
        if len(data) != 4:
            return False
        self.originator_id = socket.inet_ntoa(data)
        return True

    def __repr__(self) -> str:
        return f"ORIGINATOR_ID({self.originator_id})"


class ClusterListAttribute(PathAttribute):
    """
    CLUSTER_LIST Attribute (Type 10, RFC 4456)

    Optional non-transitive attribute for route reflection
    Contains list of cluster IDs (for loop prevention)
    """

    def __init__(self, cluster_list: List[str] = None):
        # Optional non-transitive
        flags = ATTR_FLAG_OPTIONAL
        super().__init__(ATTR_CLUSTER_LIST, flags)
        self.cluster_list = cluster_list or []  # List of IPv4 address strings

    def encode_value(self) -> bytes:
        data = b''
        for cluster_id in self.cluster_list:
            data += socket.inet_aton(cluster_id)
        return data

    def decode_value(self, data: bytes) -> bool:
        if len(data) % 4 != 0:
            return False

        self.cluster_list = []
        for i in range(0, len(data), 4):
            cluster_id = socket.inet_ntoa(data[i:i+4])
            self.cluster_list.append(cluster_id)

        return True

    def prepend(self, cluster_id: str) -> None:
        """Prepend cluster ID to list"""
        self.cluster_list.insert(0, cluster_id)

    def contains(self, cluster_id: str) -> bool:
        """Check if cluster ID is in list (loop detection)"""
        return cluster_id in self.cluster_list

    def __repr__(self) -> str:
        return f"CLUSTER_LIST({', '.join(self.cluster_list)})"


class MPReachNLRIAttribute(PathAttribute):
    """
    MP_REACH_NLRI Attribute (Type 14, RFC 4760 Section 3)

    Used to advertise reachable destinations with next hops for
    multiprotocol extensions (e.g., IPv6, VPNs, etc.)

    Format:
    - AFI (2 bytes): Address Family Identifier
    - SAFI (1 byte): Subsequent Address Family Identifier
    - Next Hop Length (1 byte)
    - Next Hop (variable)
    - Reserved (1 byte)
    - NLRI (variable)
    """

    def __init__(self, afi: int = AFI_IPV6, safi: int = SAFI_UNICAST,
                 next_hop: str = "", nlri: List[str] = None):
        # Optional non-transitive
        flags = ATTR_FLAG_OPTIONAL
        super().__init__(ATTR_MP_REACH_NLRI, flags)
        self.afi = afi
        self.safi = safi
        self.next_hop = next_hop
        self.nlri = nlri or []  # List of prefix strings (e.g., ["2001:db8::/32"])

    def encode_value(self) -> bytes:
        """Encode MP_REACH_NLRI value"""
        data = b''

        # AFI (2 bytes) + SAFI (1 byte)
        data += struct.pack('!HB', self.afi, self.safi)

        # Next Hop
        if self.afi == AFI_IPV6:
            # IPv6 next hop (16 bytes)
            try:
                nh_bytes = socket.inet_pton(socket.AF_INET6, self.next_hop)
                data += struct.pack('!B', len(nh_bytes))  # Next hop length
                data += nh_bytes
            except:
                # Default to ::
                data += struct.pack('!B', 16)
                data += b'\x00' * 16
        elif self.afi == AFI_IPV4:
            # IPv4 next hop (4 bytes)
            try:
                nh_bytes = socket.inet_pton(socket.AF_INET, self.next_hop)
                data += struct.pack('!B', len(nh_bytes))
                data += nh_bytes
            except:
                data += struct.pack('!B', 4)
                data += b'\x00' * 4

        # Reserved (1 byte)
        data += b'\x00'

        # NLRI
        for prefix_str in self.nlri:
            nlri_bytes = self._encode_nlri_prefix(prefix_str, self.afi)
            data += nlri_bytes

        return data

    def decode_value(self, data: bytes) -> bool:
        """Decode MP_REACH_NLRI value"""
        try:
            if len(data) < 5:  # Minimum: AFI(2) + SAFI(1) + NH_Len(1) + Reserved(1)
                return False

            offset = 0

            # Parse AFI and SAFI
            self.afi = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            self.safi = data[offset]
            offset += 1

            # Parse Next Hop Length
            nh_length = data[offset]
            offset += 1

            if len(data) < offset + nh_length + 1:  # +1 for reserved byte
                return False

            # Parse Next Hop
            nh_bytes = data[offset:offset+nh_length]
            if self.afi == AFI_IPV6 and nh_length >= 16:
                # IPv6 next hop
                self.next_hop = socket.inet_ntop(socket.AF_INET6, nh_bytes[:16])
            elif self.afi == AFI_IPV4 and nh_length >= 4:
                # IPv4 next hop
                self.next_hop = socket.inet_ntop(socket.AF_INET, nh_bytes[:4])
            else:
                return False

            offset += nh_length

            # Reserved byte
            offset += 1

            # Parse NLRI
            self.nlri = []
            while offset < len(data):
                prefix_str, consumed = self._decode_nlri_prefix(data[offset:], self.afi)
                if not prefix_str:
                    break
                self.nlri.append(prefix_str)
                offset += consumed

            return True

        except Exception as e:
            return False

    def _encode_nlri_prefix(self, prefix_str: str, afi: int) -> bytes:
        """
        Encode NLRI prefix

        Format:
        - Length (1 byte): Prefix length in bits
        - Prefix (variable): Only significant octets
        """
        try:
            if '/' in prefix_str:
                addr, length_str = prefix_str.split('/')
                prefix_len = int(length_str)
            else:
                # Assume /32 for IPv4, /128 for IPv6
                addr = prefix_str
                prefix_len = 32 if afi == AFI_IPV4 else 128

            # Convert address to bytes
            if afi == AFI_IPV6:
                addr_bytes = socket.inet_pton(socket.AF_INET6, addr)
            else:
                addr_bytes = socket.inet_pton(socket.AF_INET, addr)

            # Calculate number of significant octets
            num_octets = (prefix_len + 7) // 8

            # Build NLRI
            nlri = struct.pack('!B', prefix_len) + addr_bytes[:num_octets]
            return nlri

        except:
            return b''

    def _decode_nlri_prefix(self, data: bytes, afi: int) -> Tuple[str, int]:
        """
        Decode NLRI prefix

        Returns:
            (prefix_string, bytes_consumed) or ("", 0)
        """
        try:
            if len(data) < 1:
                return ("", 0)

            # Parse prefix length
            prefix_len = data[0]

            # Calculate number of octets
            num_octets = (prefix_len + 7) // 8

            if len(data) < 1 + num_octets:
                return ("", 0)

            # Parse prefix bytes
            prefix_bytes = data[1:1+num_octets]

            # Pad to full address length
            if afi == AFI_IPV6:
                # Pad to 16 bytes for IPv6
                prefix_bytes += b'\x00' * (16 - len(prefix_bytes))
                addr_str = socket.inet_ntop(socket.AF_INET6, prefix_bytes)
            else:
                # Pad to 4 bytes for IPv4
                prefix_bytes += b'\x00' * (4 - len(prefix_bytes))
                addr_str = socket.inet_ntop(socket.AF_INET, prefix_bytes)

            prefix_str = f"{addr_str}/{prefix_len}"
            return (prefix_str, 1 + num_octets)

        except Exception:
            return ("", 0)

    def __repr__(self) -> str:
        afi_name = AFI_NAMES.get(self.afi, self.afi)
        safi_name = SAFI_NAMES.get(self.safi, self.safi)
        return f"MP_REACH_NLRI({afi_name}/{safi_name}, NH={self.next_hop}, {len(self.nlri)} prefixes)"


class MPUnreachNLRIAttribute(PathAttribute):
    """
    MP_UNREACH_NLRI Attribute (Type 15, RFC 4760 Section 4)

    Used to withdraw unfeasible routes for multiprotocol extensions

    Format:
    - AFI (2 bytes): Address Family Identifier
    - SAFI (1 byte): Subsequent Address Family Identifier
    - Withdrawn Routes (variable)
    """

    def __init__(self, afi: int = AFI_IPV6, safi: int = SAFI_UNICAST,
                 withdrawn_routes: List[str] = None):
        # Optional non-transitive
        flags = ATTR_FLAG_OPTIONAL
        super().__init__(ATTR_MP_UNREACH_NLRI, flags)
        self.afi = afi
        self.safi = safi
        self.withdrawn_routes = withdrawn_routes or []

    def encode_value(self) -> bytes:
        """Encode MP_UNREACH_NLRI value"""
        data = b''

        # AFI (2 bytes) + SAFI (1 byte)
        data += struct.pack('!HB', self.afi, self.safi)

        # Withdrawn Routes
        for prefix_str in self.withdrawn_routes:
            nlri_bytes = self._encode_nlri_prefix(prefix_str, self.afi)
            data += nlri_bytes

        return data

    def decode_value(self, data: bytes) -> bool:
        """Decode MP_UNREACH_NLRI value"""
        try:
            if len(data) < 3:  # Minimum: AFI(2) + SAFI(1)
                return False

            offset = 0

            # Parse AFI and SAFI
            self.afi = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            self.safi = data[offset]
            offset += 1

            # Parse Withdrawn Routes
            self.withdrawn_routes = []
            while offset < len(data):
                prefix_str, consumed = self._decode_nlri_prefix(data[offset:], self.afi)
                if not prefix_str:
                    break
                self.withdrawn_routes.append(prefix_str)
                offset += consumed

            return True

        except Exception:
            return False

    def _encode_nlri_prefix(self, prefix_str: str, afi: int) -> bytes:
        """Encode NLRI prefix (same as MP_REACH_NLRI)"""
        try:
            if '/' in prefix_str:
                addr, length_str = prefix_str.split('/')
                prefix_len = int(length_str)
            else:
                addr = prefix_str
                prefix_len = 32 if afi == AFI_IPV4 else 128

            if afi == AFI_IPV6:
                addr_bytes = socket.inet_pton(socket.AF_INET6, addr)
            else:
                addr_bytes = socket.inet_pton(socket.AF_INET, addr)

            num_octets = (prefix_len + 7) // 8
            nlri = struct.pack('!B', prefix_len) + addr_bytes[:num_octets]
            return nlri

        except:
            return b''

    def _decode_nlri_prefix(self, data: bytes, afi: int) -> Tuple[str, int]:
        """Decode NLRI prefix (same as MP_REACH_NLRI)"""
        try:
            if len(data) < 1:
                return ("", 0)

            prefix_len = data[0]
            num_octets = (prefix_len + 7) // 8

            if len(data) < 1 + num_octets:
                return ("", 0)

            prefix_bytes = data[1:1+num_octets]

            if afi == AFI_IPV6:
                prefix_bytes += b'\x00' * (16 - len(prefix_bytes))
                addr_str = socket.inet_ntop(socket.AF_INET6, prefix_bytes)
            else:
                prefix_bytes += b'\x00' * (4 - len(prefix_bytes))
                addr_str = socket.inet_ntop(socket.AF_INET, prefix_bytes)

            prefix_str = f"{addr_str}/{prefix_len}"
            return (prefix_str, 1 + num_octets)

        except Exception:
            return ("", 0)

    def __repr__(self) -> str:
        afi_name = AFI_NAMES.get(self.afi, self.afi)
        safi_name = SAFI_NAMES.get(self.safi, self.safi)
        return f"MP_UNREACH_NLRI({afi_name}/{safi_name}, {len(self.withdrawn_routes)} withdrawn)"


class AttributeFactory:
    """Factory for creating path attribute instances"""

    @staticmethod
    def create(type_code: int, flags: int, value: bytes) -> Optional[PathAttribute]:
        """
        Create path attribute instance based on type code

        Args:
            type_code: Attribute type code
            flags: Attribute flags
            value: Attribute value bytes

        Returns:
            PathAttribute instance or None
        """
        attr_classes = {
            ATTR_ORIGIN: OriginAttribute,
            ATTR_AS_PATH: ASPathAttribute,
            ATTR_NEXT_HOP: NextHopAttribute,
            ATTR_MED: MEDAttribute,
            ATTR_LOCAL_PREF: LocalPrefAttribute,
            ATTR_ATOMIC_AGGREGATE: AtomicAggregateAttribute,
            ATTR_AGGREGATOR: AggregatorAttribute,
            ATTR_COMMUNITIES: CommunitiesAttribute,
            ATTR_ORIGINATOR_ID: OriginatorIDAttribute,
            ATTR_CLUSTER_LIST: ClusterListAttribute,
            ATTR_MP_REACH_NLRI: MPReachNLRIAttribute,
            ATTR_MP_UNREACH_NLRI: MPUnreachNLRIAttribute,
        }

        attr_class = attr_classes.get(type_code)
        if not attr_class:
            # Unknown attribute type
            return None

        # Create instance with dummy values
        if type_code == ATTR_ORIGIN:
            attr = OriginAttribute(ORIGIN_IGP)
        elif type_code == ATTR_AS_PATH:
            attr = ASPathAttribute()
        elif type_code == ATTR_NEXT_HOP:
            attr = NextHopAttribute("0.0.0.0")
        elif type_code == ATTR_MED:
            attr = MEDAttribute(0)
        elif type_code == ATTR_LOCAL_PREF:
            attr = LocalPrefAttribute(100)
        elif type_code == ATTR_ATOMIC_AGGREGATE:
            attr = AtomicAggregateAttribute()
        elif type_code == ATTR_AGGREGATOR:
            attr = AggregatorAttribute(0, "0.0.0.0")
        elif type_code == ATTR_COMMUNITIES:
            attr = CommunitiesAttribute()
        elif type_code == ATTR_ORIGINATOR_ID:
            attr = OriginatorIDAttribute("0.0.0.0")
        elif type_code == ATTR_CLUSTER_LIST:
            attr = ClusterListAttribute()
        elif type_code == ATTR_MP_REACH_NLRI:
            attr = MPReachNLRIAttribute()
        elif type_code == ATTR_MP_UNREACH_NLRI:
            attr = MPUnreachNLRIAttribute()
        else:
            return None

        # Override flags with actual flags from wire
        attr.flags = flags

        return attr


def encode_path_attributes(attributes: dict) -> bytes:
    """
    Encode dictionary of path attributes to wire format

    Args:
        attributes: Dict mapping type_code to PathAttribute

    Returns:
        Encoded attributes bytes
    """
    data = b''
    for attr in attributes.values():
        data += attr.encode()
    return data


def decode_path_attributes(data: bytes) -> dict:
    """
    Decode path attributes from wire format

    Args:
        data: Attributes bytes

    Returns:
        Dict mapping type_code to PathAttribute
    """
    attributes = {}
    offset = 0

    while offset < len(data):
        attr, consumed = PathAttribute.decode(data[offset:])
        if attr:
            attributes[attr.type_code] = attr
            offset += consumed
        else:
            # Failed to decode attribute
            break

    return attributes
