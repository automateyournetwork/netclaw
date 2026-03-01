"""
BGP-4 Protocol Implementation (RFC 4271)

This package implements a production-grade BGP speaker supporting:
- eBGP and iBGP sessions
- Route reflection (RFC 4456)
- BGP communities (RFC 1997)
- IPv4 and IPv6 address families (RFC 4760)
- Route filtering and policy
- Capabilities negotiation (RFC 5492)
- Best path selection (RFC 4271 Section 9.1)

Main Classes:
    BGPSpeaker: High-level interface for running BGP speaker
    BGPAgent: Lower-level agent managing sessions and RIBs
    BGPSession: Individual peer session manager

    Policy: BGP policy for import/export filtering
    PolicyRule: Individual policy rule with match/action
    BGPRoute: BGP route representation

Example:
    from bgp import BGPSpeaker

    speaker = BGPSpeaker(local_as=65001, router_id="192.0.2.1")
    speaker.add_peer(peer_ip="192.0.2.2", peer_as=65002)
    await speaker.run()
"""

__version__ = "0.1.0"

# Main exports
from .speaker import BGPSpeaker, run_bgp_speaker
from .agent import BGPAgent
from .session import BGPSession, BGPSessionConfig
from .rib import BGPRoute, AdjRIBIn, AdjRIBOut, LocRIB

# Policy
from .policy import (
    Policy, PolicyRule, PolicyEngine,
    MatchCondition, Action,
    PrefixMatch, ASPathMatch, CommunityMatch, NextHopMatch,
    LocalPrefMatch, MEDMatch, OriginMatch,
    AcceptAction, RejectAction,
    SetLocalPrefAction, SetMEDAction, SetNextHopAction,
    PrependASPathAction, AddCommunityAction, RemoveCommunityAction,
    SetCommunityAction
)

# Messages
from .messages import (
    BGPMessage, BGPOpen, BGPUpdate, BGPKeepalive,
    BGPNotification, BGPRouteRefresh, BGPCapability
)

# Attributes
from .attributes import (
    PathAttribute, OriginAttribute, ASPathAttribute, NextHopAttribute,
    MEDAttribute, LocalPrefAttribute, AtomicAggregateAttribute,
    AggregatorAttribute, CommunitiesAttribute, OriginatorIDAttribute,
    ClusterListAttribute
)

# Route Reflection
from .route_reflection import RouteReflector

# Path Selection
from .path_selection import BestPathSelector

# Capabilities
from .capabilities import CapabilityManager, CapabilityInfo

# Address Family
from .address_family import (
    AddressFamily, MPReachNLRIAttribute, MPUnreachNLRIAttribute
)

# Communities
from .communities import (
    parse_community, format_community, is_well_known, matches_regex
)

# Errors
from .errors import (
    BGPError, MessageHeaderError, OpenMessageError, UpdateMessageError,
    HoldTimerExpiredError, FSMError, CeaseError
)

# Constants
from .constants import (
    BGP_VERSION, BGP_PORT,
    MSG_OPEN, MSG_UPDATE, MSG_KEEPALIVE, MSG_NOTIFICATION, MSG_ROUTE_REFRESH,
    STATE_IDLE, STATE_CONNECT, STATE_ACTIVE, STATE_OPENSENT,
    STATE_OPENCONFIRM, STATE_ESTABLISHED,
    ORIGIN_IGP, ORIGIN_EGP, ORIGIN_INCOMPLETE,
    ATTR_ORIGIN, ATTR_AS_PATH, ATTR_NEXT_HOP, ATTR_MED, ATTR_LOCAL_PREF,
    ATTR_ATOMIC_AGGREGATE, ATTR_AGGREGATOR, ATTR_COMMUNITIES,
    AFI_IPV4, AFI_IPV6, SAFI_UNICAST, SAFI_MULTICAST,
    COMMUNITY_NO_EXPORT, COMMUNITY_NO_ADVERTISE, COMMUNITY_NO_EXPORT_SUBCONFED
)

__all__ = [
    # Main classes
    'BGPSpeaker', 'run_bgp_speaker',
    'BGPAgent', 'BGPSession', 'BGPSessionConfig',
    'BGPRoute', 'AdjRIBIn', 'AdjRIBOut', 'LocRIB',

    # Policy
    'Policy', 'PolicyRule', 'PolicyEngine',
    'MatchCondition', 'Action',
    'PrefixMatch', 'ASPathMatch', 'CommunityMatch', 'NextHopMatch',
    'LocalPrefMatch', 'MEDMatch', 'OriginMatch',
    'AcceptAction', 'RejectAction',
    'SetLocalPrefAction', 'SetMEDAction', 'SetNextHopAction',
    'PrependASPathAction', 'AddCommunityAction', 'RemoveCommunityAction',
    'SetCommunityAction',

    # Messages
    'BGPMessage', 'BGPOpen', 'BGPUpdate', 'BGPKeepalive',
    'BGPNotification', 'BGPRouteRefresh', 'BGPCapability',

    # Attributes
    'PathAttribute', 'OriginAttribute', 'ASPathAttribute', 'NextHopAttribute',
    'MEDAttribute', 'LocalPrefAttribute', 'AtomicAggregateAttribute',
    'AggregatorAttribute', 'CommunitiesAttribute', 'OriginatorIDAttribute',
    'ClusterListAttribute',

    # Other components
    'RouteReflector', 'BestPathSelector', 'CapabilityManager',
    'AddressFamily', 'MPReachNLRIAttribute', 'MPUnreachNLRIAttribute',

    # Utilities
    'parse_community', 'format_community',

    # Errors
    'BGPError', 'MessageHeaderError', 'OpenMessageError', 'UpdateMessageError',
    'HoldTimerExpiredError', 'FSMError', 'CeaseError',
]
