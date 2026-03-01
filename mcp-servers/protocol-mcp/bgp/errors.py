"""
BGP Error Handling

Defines BGP error codes, subcodes, and exception classes
per RFC 4271 Section 6 (NOTIFICATION Message Error Codes).
"""

from typing import Optional
from .constants import *


class BGPError(Exception):
    """Base exception for BGP errors"""

    def __init__(self, error_code: int, error_subcode: int,
                 data: bytes = b'', message: Optional[str] = None):
        """
        Initialize BGP error

        Args:
            error_code: BGP error code
            error_subcode: BGP error subcode
            data: Error data bytes
            message: Human-readable message
        """
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.data = data

        if not message:
            message = self._format_error_message()

        super().__init__(message)

    def _format_error_message(self) -> str:
        """Format human-readable error message"""
        error_name = ERROR_CODE_NAMES.get(self.error_code, f"Unknown({self.error_code})")
        return f"BGP Error: {error_name} (code={self.error_code}, subcode={self.error_subcode})"


class MessageHeaderError(BGPError):
    """Message Header Error (Error Code 1)"""

    def __init__(self, subcode: int, data: bytes = b'', message: Optional[str] = None):
        super().__init__(ERR_MESSAGE_HEADER, subcode, data, message)


class OpenMessageError(BGPError):
    """OPEN Message Error (Error Code 2)"""

    def __init__(self, subcode: int, data: bytes = b'', message: Optional[str] = None):
        super().__init__(ERR_OPEN_MESSAGE, subcode, data, message)


class UpdateMessageError(BGPError):
    """UPDATE Message Error (Error Code 3)"""

    def __init__(self, subcode: int, data: bytes = b'', message: Optional[str] = None):
        super().__init__(ERR_UPDATE_MESSAGE, subcode, data, message)


class HoldTimerExpiredError(BGPError):
    """Hold Timer Expired (Error Code 4)"""

    def __init__(self, data: bytes = b'', message: Optional[str] = None):
        super().__init__(ERR_HOLD_TIMER_EXPIRED, 0, data, message)


class FSMError(BGPError):
    """Finite State Machine Error (Error Code 5)"""

    def __init__(self, data: bytes = b'', message: Optional[str] = None):
        super().__init__(ERR_FSM, 0, data, message)


class CeaseError(BGPError):
    """Cease (Error Code 6)"""

    def __init__(self, subcode: int = 0, data: bytes = b'', message: Optional[str] = None):
        super().__init__(ERR_CEASE, subcode, data, message)


# Convenience functions for common errors

def connection_not_synchronized() -> MessageHeaderError:
    """Connection Not Synchronized (1.1)"""
    return MessageHeaderError(1, message="Connection Not Synchronized")


def bad_message_length(length: int) -> MessageHeaderError:
    """Bad Message Length (1.2)"""
    import struct
    data = struct.pack('!H', length)
    return MessageHeaderError(2, data, f"Bad Message Length: {length}")


def bad_message_type(msg_type: int) -> MessageHeaderError:
    """Bad Message Type (1.3)"""
    data = bytes([msg_type])
    return MessageHeaderError(3, data, f"Bad Message Type: {msg_type}")


def unsupported_version_number(version: int) -> OpenMessageError:
    """Unsupported Version Number (2.1)"""
    import struct
    data = struct.pack('!H', BGP_VERSION)  # Supported version
    return OpenMessageError(1, data, f"Unsupported Version: {version}")


def bad_peer_as() -> OpenMessageError:
    """Bad Peer AS (2.2)"""
    return OpenMessageError(2, message="Bad Peer AS")


def bad_bgp_identifier() -> OpenMessageError:
    """Bad BGP Identifier (2.3)"""
    return OpenMessageError(3, message="Bad BGP Identifier")


def unsupported_optional_parameter() -> OpenMessageError:
    """Unsupported Optional Parameter (2.4)"""
    return OpenMessageError(4, message="Unsupported Optional Parameter")


def unacceptable_hold_time() -> OpenMessageError:
    """Unacceptable Hold Time (2.6)"""
    return OpenMessageError(6, message="Unacceptable Hold Time")


def malformed_attribute_list() -> UpdateMessageError:
    """Malformed Attribute List (3.1)"""
    return UpdateMessageError(1, message="Malformed Attribute List")


def unrecognized_well_known_attribute(attr_type: int) -> UpdateMessageError:
    """Unrecognized Well-known Attribute (3.2)"""
    data = bytes([attr_type])
    return UpdateMessageError(2, data, f"Unrecognized Well-known Attribute: {attr_type}")


def missing_well_known_attribute(attr_type: int) -> UpdateMessageError:
    """Missing Well-known Attribute (3.3)"""
    data = bytes([attr_type])
    return UpdateMessageError(3, data, f"Missing Well-known Attribute: {attr_type}")


def attribute_flags_error(attr_type: int) -> UpdateMessageError:
    """Attribute Flags Error (3.4)"""
    data = bytes([attr_type])
    return UpdateMessageError(4, data, f"Attribute Flags Error: {attr_type}")


def attribute_length_error(attr_type: int) -> UpdateMessageError:
    """Attribute Length Error (3.5)"""
    data = bytes([attr_type])
    return UpdateMessageError(5, data, f"Attribute Length Error: {attr_type}")


def invalid_origin_attribute() -> UpdateMessageError:
    """Invalid ORIGIN Attribute (3.6)"""
    return UpdateMessageError(6, message="Invalid ORIGIN Attribute")


def invalid_next_hop_attribute() -> UpdateMessageError:
    """Invalid NEXT_HOP Attribute (3.8)"""
    return UpdateMessageError(8, message="Invalid NEXT_HOP Attribute")


def optional_attribute_error(attr_type: int) -> UpdateMessageError:
    """Optional Attribute Error (3.9)"""
    data = bytes([attr_type])
    return UpdateMessageError(9, data, f"Optional Attribute Error: {attr_type}")


def invalid_network_field() -> UpdateMessageError:
    """Invalid Network Field (3.10)"""
    return UpdateMessageError(10, message="Invalid Network Field")


def malformed_as_path() -> UpdateMessageError:
    """Malformed AS_PATH (3.11)"""
    return UpdateMessageError(11, message="Malformed AS_PATH")


def hold_timer_expired() -> HoldTimerExpiredError:
    """Hold Timer Expired (4)"""
    return HoldTimerExpiredError(message="Hold Timer Expired")


def fsm_error() -> FSMError:
    """FSM Error (5)"""
    return FSMError(message="Finite State Machine Error")


def administrative_shutdown() -> CeaseError:
    """Administrative Shutdown (6.2)"""
    return CeaseError(2, message="Administrative Shutdown")


def peer_deconfigured() -> CeaseError:
    """Peer De-configured (6.3)"""
    return CeaseError(3, message="Peer De-configured")


def administrative_reset() -> CeaseError:
    """Administrative Reset (6.4)"""
    return CeaseError(4, message="Administrative Reset")


def connection_rejected() -> CeaseError:
    """Connection Rejected (6.5)"""
    return CeaseError(5, message="Connection Rejected")


def other_configuration_change() -> CeaseError:
    """Other Configuration Change (6.6)"""
    return CeaseError(6, message="Other Configuration Change")


def connection_collision_resolution() -> CeaseError:
    """Connection Collision Resolution (6.7)"""
    return CeaseError(7, message="Connection Collision Resolution")


def out_of_resources() -> CeaseError:
    """Out of Resources (6.8)"""
    return CeaseError(8, message="Out of Resources")
