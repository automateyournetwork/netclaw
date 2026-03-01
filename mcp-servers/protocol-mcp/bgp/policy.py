"""
BGP Policy Engine

Implements import/export policy for route filtering and attribute manipulation.

Policy consists of ordered rules. Each rule has match conditions and actions.
Rules are evaluated in order. First matching rule applies its actions.
"""

import re
import logging
from typing import List, Optional, Dict
from abc import ABC, abstractmethod
from ipaddress import ip_network

from .rib import BGPRoute
from .attributes import *
from .communities import parse_community, matches_regex as community_matches
from .constants import *


# Match Conditions

class MatchCondition(ABC):
    """Base class for match conditions"""

    @abstractmethod
    def matches(self, route: BGPRoute) -> bool:
        """Check if route matches this condition"""
        pass


class PrefixMatch(MatchCondition):
    """Match route prefix"""

    def __init__(self, prefix: str, exact: bool = False, ge: Optional[int] = None, le: Optional[int] = None):
        """
        Args:
            prefix: Prefix to match (e.g., "203.0.113.0/24")
            exact: Exact match only
            ge: Greater or equal prefix length
            le: Less or equal prefix length
        """
        self.prefix = prefix
        self.exact = exact
        self.ge = ge
        self.le = le

    def matches(self, route: BGPRoute) -> bool:
        try:
            route_net = ip_network(route.prefix, strict=False)
            match_net = ip_network(self.prefix, strict=False)

            # Check if route is within match prefix
            if not (route_net.network_address >= match_net.network_address and
                    route_net.broadcast_address <= match_net.broadcast_address):
                return False

            # Exact match
            if self.exact:
                return route.prefix == self.prefix

            # Check prefix length constraints
            if self.ge is not None and route.prefix_len < self.ge:
                return False
            if self.le is not None and route.prefix_len > self.le:
                return False

            return True
        except:
            return False


class ASPathMatch(MatchCondition):
    """Match AS_PATH"""

    def __init__(self, regex: Optional[str] = None, length: Optional[int] = None,
                 length_ge: Optional[int] = None, length_le: Optional[int] = None):
        """
        Args:
            regex: Regular expression to match AS_PATH
            length: Exact AS_PATH length
            length_ge: Greater or equal length
            length_le: Less or equal length
        """
        self.regex = regex
        self.length = length
        self.length_ge = length_ge
        self.length_le = length_le

    def matches(self, route: BGPRoute) -> bool:
        if not route.has_attribute(ATTR_AS_PATH):
            return False

        attr = route.get_attribute(ATTR_AS_PATH)

        # Check length constraints
        path_len = attr.length()
        if self.length is not None and path_len != self.length:
            return False
        if self.length_ge is not None and path_len < self.length_ge:
            return False
        if self.length_le is not None and path_len > self.length_le:
            return False

        # Check regex match
        if self.regex:
            # Convert AS_PATH to string for regex matching
            path_str = str(attr)
            if not re.search(self.regex, path_str):
                return False

        return True


class CommunityMatch(MatchCondition):
    """Match BGP communities"""

    def __init__(self, community: Optional[str] = None, any_of: Optional[List[str]] = None):
        """
        Args:
            community: Single community to match (e.g., "65001:100" or "NO_EXPORT")
            any_of: Match any of these communities
        """
        self.community = community
        self.any_of = any_of

    def matches(self, route: BGPRoute) -> bool:
        if not route.has_attribute(ATTR_COMMUNITIES):
            return False

        attr = route.get_attribute(ATTR_COMMUNITIES)

        if self.community:
            # Match single community (supports wildcards like "65001:*")
            for comm in attr.communities:
                if community_matches(comm, self.community):
                    return True

        if self.any_of:
            # Match any of the listed communities
            for pattern in self.any_of:
                for comm in attr.communities:
                    if community_matches(comm, pattern):
                        return True

        return False


class NextHopMatch(MatchCondition):
    """Match NEXT_HOP attribute"""

    def __init__(self, next_hop: str):
        """
        Args:
            next_hop: Next hop IP to match
        """
        self.next_hop = next_hop

    def matches(self, route: BGPRoute) -> bool:
        if not route.has_attribute(ATTR_NEXT_HOP):
            return False

        attr = route.get_attribute(ATTR_NEXT_HOP)
        return attr.next_hop == self.next_hop


class LocalPrefMatch(MatchCondition):
    """Match LOCAL_PREF attribute"""

    def __init__(self, value: Optional[int] = None, ge: Optional[int] = None, le: Optional[int] = None):
        """
        Args:
            value: Exact value
            ge: Greater or equal
            le: Less or equal
        """
        self.value = value
        self.ge = ge
        self.le = le

    def matches(self, route: BGPRoute) -> bool:
        if not route.has_attribute(ATTR_LOCAL_PREF):
            return False

        attr = route.get_attribute(ATTR_LOCAL_PREF)
        pref = attr.local_pref

        if self.value is not None and pref != self.value:
            return False
        if self.ge is not None and pref < self.ge:
            return False
        if self.le is not None and pref > self.le:
            return False

        return True


class MEDMatch(MatchCondition):
    """Match MED attribute"""

    def __init__(self, value: Optional[int] = None, ge: Optional[int] = None, le: Optional[int] = None):
        """
        Args:
            value: Exact value
            ge: Greater or equal
            le: Less or equal
        """
        self.value = value
        self.ge = ge
        self.le = le

    def matches(self, route: BGPRoute) -> bool:
        if not route.has_attribute(ATTR_MED):
            return False

        attr = route.get_attribute(ATTR_MED)
        med = attr.med

        if self.value is not None and med != self.value:
            return False
        if self.ge is not None and med < self.ge:
            return False
        if self.le is not None and med > self.le:
            return False

        return True


class OriginMatch(MatchCondition):
    """Match ORIGIN attribute"""

    def __init__(self, origin: int):
        """
        Args:
            origin: ORIGIN value (IGP=0, EGP=1, INCOMPLETE=2)
        """
        self.origin = origin

    def matches(self, route: BGPRoute) -> bool:
        if not route.has_attribute(ATTR_ORIGIN):
            return False

        attr = route.get_attribute(ATTR_ORIGIN)
        return attr.origin == self.origin


# Actions

class Action(ABC):
    """Base class for policy actions"""

    @abstractmethod
    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        """
        Apply action to route

        Returns:
            Modified route or None if route should be rejected
        """
        pass


class AcceptAction(Action):
    """Accept route"""

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        return route


class RejectAction(Action):
    """Reject route"""

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        return None


class SetLocalPrefAction(Action):
    """Set LOCAL_PREF attribute"""

    def __init__(self, value: int):
        self.value = value

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        attr = LocalPrefAttribute(self.value)
        route.set_attribute(attr)
        return route


class SetMEDAction(Action):
    """Set MED attribute"""

    def __init__(self, value: int):
        self.value = value

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        attr = MEDAttribute(self.value)
        route.set_attribute(attr)
        return route


class SetNextHopAction(Action):
    """Set NEXT_HOP attribute"""

    def __init__(self, next_hop: str):
        self.next_hop = next_hop

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        attr = NextHopAttribute(self.next_hop)
        route.set_attribute(attr)
        return route


class PrependASPathAction(Action):
    """Prepend AS to AS_PATH"""

    def __init__(self, asn: int, count: int = 1):
        """
        Args:
            asn: AS number to prepend
            count: Number of times to prepend
        """
        self.asn = asn
        self.count = count

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        if route.has_attribute(ATTR_AS_PATH):
            attr = route.get_attribute(ATTR_AS_PATH)
            for _ in range(self.count):
                attr.prepend(self.asn)
        else:
            # Create new AS_PATH with prepended AS
            segments = [(AS_SEQUENCE, [self.asn] * self.count)]
            attr = ASPathAttribute(segments)
            route.set_attribute(attr)
        return route


class AddCommunityAction(Action):
    """Add community to COMMUNITIES attribute"""

    def __init__(self, community: str):
        """
        Args:
            community: Community to add (e.g., "65001:100" or "NO_EXPORT")
        """
        from .communities import parse_community
        self.community = parse_community(community)

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        if route.has_attribute(ATTR_COMMUNITIES):
            attr = route.get_attribute(ATTR_COMMUNITIES)
            attr.add(self.community)
        else:
            attr = CommunitiesAttribute([self.community])
            route.set_attribute(attr)
        return route


class RemoveCommunityAction(Action):
    """Remove community from COMMUNITIES attribute"""

    def __init__(self, community: str):
        """
        Args:
            community: Community to remove (supports wildcards like "65001:*")
        """
        self.community = community

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        if route.has_attribute(ATTR_COMMUNITIES):
            attr = route.get_attribute(ATTR_COMMUNITIES)
            # Remove matching communities
            attr.communities = [c for c in attr.communities if not community_matches(c, self.community)]
        return route


class SetCommunityAction(Action):
    """Set COMMUNITIES attribute (replaces existing)"""

    def __init__(self, communities: List[str]):
        """
        Args:
            communities: List of communities to set
        """
        from .communities import parse_community
        self.communities = [parse_community(c) for c in communities if parse_community(c) is not None]

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        attr = CommunitiesAttribute(self.communities)
        route.set_attribute(attr)
        return route


# Policy Rules and Engine

class PolicyRule:
    """Policy rule with match conditions and actions"""

    def __init__(self, name: str, matches: List[MatchCondition], actions: List[Action]):
        """
        Args:
            name: Rule name
            matches: List of match conditions (all must match)
            actions: List of actions to apply
        """
        self.name = name
        self.matches = matches
        self.actions = actions

    def evaluate(self, route: BGPRoute) -> Optional[BGPRoute]:
        """
        Evaluate rule against route

        Returns:
            Modified route if matched, None if rejected, or original route if not matched
        """
        # Check all match conditions
        for match in self.matches:
            if not match.matches(route):
                return route  # Not matched, continue to next rule

        # All conditions matched, apply actions
        modified_route = route.copy()
        for action in self.actions:
            modified_route = action.apply(modified_route)
            if modified_route is None:
                return None  # Route rejected

        return modified_route


class Policy:
    """BGP Policy with ordered rules"""

    def __init__(self, name: str, rules: List[PolicyRule], default_accept: bool = True):
        """
        Args:
            name: Policy name
            rules: Ordered list of rules
            default_accept: Accept route if no rules match
        """
        self.name = name
        self.rules = rules
        self.default_accept = default_accept

    def apply(self, route: BGPRoute) -> Optional[BGPRoute]:
        """
        Apply policy to route

        Returns:
            Modified route or None if rejected
        """
        for rule in self.rules:
            result = rule.evaluate(route)
            if result != route:
                # Rule matched and modified/rejected route
                return result

        # No rule matched, apply default
        if self.default_accept:
            return route
        else:
            return None


class PolicyEngine:
    """BGP Policy Engine managing import/export policies"""

    def __init__(self):
        self.import_policies: Dict[str, Policy] = {}  # Key: peer_id
        self.export_policies: Dict[str, Policy] = {}  # Key: peer_id
        self.logger = logging.getLogger("PolicyEngine")

    def set_import_policy(self, peer_id: str, policy: Policy) -> None:
        """Set import policy for peer"""
        self.import_policies[peer_id] = policy
        self.logger.info(f"Set import policy '{policy.name}' for peer {peer_id}")

    def set_export_policy(self, peer_id: str, policy: Policy) -> None:
        """Set export policy for peer"""
        self.export_policies[peer_id] = policy
        self.logger.info(f"Set export policy '{policy.name}' for peer {peer_id}")

    def apply_import_policy(self, route: BGPRoute, peer_id: str) -> Optional[BGPRoute]:
        """
        Apply import policy for peer

        Args:
            route: Received route
            peer_id: Peer ID

        Returns:
            Modified route or None if rejected
        """
        if peer_id in self.import_policies:
            policy = self.import_policies[peer_id]
            result = policy.apply(route)
            if result is None:
                self.logger.debug(f"Route {route.prefix} from {peer_id} rejected by import policy")
            return result
        return route  # No policy, accept

    def apply_export_policy(self, route: BGPRoute, peer_id: str) -> Optional[BGPRoute]:
        """
        Apply export policy for peer

        Args:
            route: Route to advertise
            peer_id: Peer ID

        Returns:
            Modified route or None if rejected
        """
        if peer_id in self.export_policies:
            policy = self.export_policies[peer_id]
            result = policy.apply(route)
            if result is None:
                self.logger.debug(f"Route {route.prefix} to {peer_id} rejected by export policy")
            return result
        return route  # No policy, accept
