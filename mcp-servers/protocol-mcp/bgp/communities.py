"""
BGP Communities Helper Utilities (RFC 1997)

Utilities for parsing, formatting, and matching BGP communities.
"""

import re
from typing import List, Optional
from .constants import *


def parse_community(s: str) -> Optional[int]:
    """
    Parse community string to 32-bit integer

    Args:
        s: Community string (e.g., "65001:100" or well-known name)

    Returns:
        32-bit community value or None if invalid

    Examples:
        >>> parse_community("65001:100")
        4259954788
        >>> parse_community("NO_EXPORT")
        4294967041
    """
    # Check for well-known community names
    if s == "NO_EXPORT":
        return COMMUNITY_NO_EXPORT
    elif s == "NO_ADVERTISE":
        return COMMUNITY_NO_ADVERTISE
    elif s == "NO_EXPORT_SUBCONFED":
        return COMMUNITY_NO_EXPORT_SUBCONFED
    elif s == "NOPEER":
        return COMMUNITY_NOPEER

    # Parse AS:Value format
    match = re.match(r'^(\d+):(\d+)$', s)
    if not match:
        return None

    asn = int(match.group(1))
    value = int(match.group(2))

    # Validate ranges
    if asn > 65535 or value > 65535:
        return None

    return (asn << 16) | value


def format_community(val: int) -> str:
    """
    Format 32-bit community value to string

    Args:
        val: 32-bit community value

    Returns:
        Community string (e.g., "65001:100" or well-known name)

    Examples:
        >>> format_community(4259954788)
        "65001:100"
        >>> format_community(COMMUNITY_NO_EXPORT)
        "NO_EXPORT"
    """
    # Check for well-known communities
    if val in WELL_KNOWN_COMMUNITIES:
        return WELL_KNOWN_COMMUNITIES[val]

    # Format as AS:Value
    asn = (val >> 16) & 0xFFFF
    value = val & 0xFFFF
    return f"{asn}:{value}"


def parse_community_list(s: str) -> List[int]:
    """
    Parse comma-separated list of communities

    Args:
        s: Community list string (e.g., "65001:100,65001:200,NO_EXPORT")

    Returns:
        List of 32-bit community values

    Examples:
        >>> parse_community_list("65001:100,65001:200,NO_EXPORT")
        [4259954788, 4259954888, 4294967041]
    """
    communities = []
    for part in s.split(','):
        part = part.strip()
        if part:
            comm = parse_community(part)
            if comm is not None:
                communities.append(comm)
    return communities


def format_community_list(communities: List[int]) -> str:
    """
    Format list of communities to comma-separated string

    Args:
        communities: List of 32-bit community values

    Returns:
        Comma-separated community string

    Examples:
        >>> format_community_list([4259954788, 4259954888, COMMUNITY_NO_EXPORT])
        "65001:100,65001:200,NO_EXPORT"
    """
    return ','.join(format_community(c) for c in communities)


def is_well_known(val: int) -> bool:
    """
    Check if community is a well-known community

    Args:
        val: 32-bit community value

    Returns:
        True if well-known

    Examples:
        >>> is_well_known(COMMUNITY_NO_EXPORT)
        True
        >>> is_well_known(4259954788)  # 65001:100
        False
    """
    return val in WELL_KNOWN_COMMUNITIES


def matches_regex(community: int, pattern: str) -> bool:
    """
    Match community against regex pattern

    Args:
        community: 32-bit community value
        pattern: Regex pattern (e.g., "65001:*", "*:100", "6500[0-9]:*")

    Returns:
        True if matches

    Examples:
        >>> matches_regex(parse_community("65001:100"), "65001:*")
        True
        >>> matches_regex(parse_community("65001:100"), "*:100")
        True
        >>> matches_regex(parse_community("65001:100"), "65002:*")
        False
    """
    # Convert community to string
    comm_str = format_community(community)

    # Convert simple wildcard pattern to regex
    # Replace * with \d+
    regex_pattern = pattern.replace('*', r'\d+')

    # Try to match
    return bool(re.fullmatch(regex_pattern, comm_str))


def matches_any(community: int, patterns: List[str]) -> bool:
    """
    Check if community matches any of the given patterns

    Args:
        community: 32-bit community value
        patterns: List of regex patterns

    Returns:
        True if matches any pattern

    Examples:
        >>> matches_any(parse_community("65001:100"), ["65001:*", "65002:*"])
        True
        >>> matches_any(parse_community("65003:100"), ["65001:*", "65002:*"])
        False
    """
    for pattern in patterns:
        if matches_regex(community, pattern):
            return True
    return False


def has_no_export(communities: List[int]) -> bool:
    """
    Check if community list contains NO_EXPORT

    Args:
        communities: List of 32-bit community values

    Returns:
        True if NO_EXPORT present
    """
    return COMMUNITY_NO_EXPORT in communities


def has_no_advertise(communities: List[int]) -> bool:
    """
    Check if community list contains NO_ADVERTISE

    Args:
        communities: List of 32-bit community values

    Returns:
        True if NO_ADVERTISE present
    """
    return COMMUNITY_NO_ADVERTISE in communities


def filter_well_known(communities: List[int]) -> List[int]:
    """
    Filter out well-known communities from list

    Args:
        communities: List of 32-bit community values

    Returns:
        List without well-known communities
    """
    return [c for c in communities if not is_well_known(c)]


def extract_as(community: int) -> int:
    """
    Extract AS number from community

    Args:
        community: 32-bit community value

    Returns:
        AS number (upper 16 bits)

    Examples:
        >>> extract_as(parse_community("65001:100"))
        65001
    """
    return (community >> 16) & 0xFFFF


def extract_value(community: int) -> int:
    """
    Extract value from community

    Args:
        community: 32-bit community value

    Returns:
        Value (lower 16 bits)

    Examples:
        >>> extract_value(parse_community("65001:100"))
        100
    """
    return community & 0xFFFF


def create_community(asn: int, value: int) -> Optional[int]:
    """
    Create community from AS number and value

    Args:
        asn: AS number (0-65535)
        value: Value (0-65535)

    Returns:
        32-bit community value or None if invalid

    Examples:
        >>> create_community(65001, 100)
        4259954788
        >>> create_community(99999, 100)  # Invalid AS
        None
    """
    if asn < 0 or asn > 65535 or value < 0 or value > 65535:
        return None

    return (asn << 16) | value


def sort_communities(communities: List[int]) -> List[int]:
    """
    Sort communities for canonical ordering

    Well-known communities come first, then sorted by AS:Value

    Args:
        communities: List of 32-bit community values

    Returns:
        Sorted list
    """
    well_known = [c for c in communities if is_well_known(c)]
    regular = [c for c in communities if not is_well_known(c)]

    # Sort well-known by value
    well_known.sort()

    # Sort regular by AS, then value
    regular.sort()

    return well_known + regular
