"""
BGP Best Path Selection Algorithm (RFC 4271 Section 9.1)

Implements the BGP decision process for selecting the best path
from multiple candidate routes to the same destination.

Decision process (RFC 4271 Section 9.1.2):
1. Highest LOCAL_PREF
2. Shortest AS_PATH
3. Lowest ORIGIN (IGP < EGP < INCOMPLETE)
4. Lowest MED (if from same neighbor AS)
5. eBGP > iBGP
6. Lowest IGP metric to NEXT_HOP
7. Oldest route (route stability)
8. Lowest Router ID
9. Lowest peer IP address
"""

import logging
from typing import List, Optional
from ipaddress import ip_address

from .rib import BGPRoute
from .constants import *


class BestPathSelector:
    """
    BGP Best Path Selection

    Selects best path from multiple candidate routes per RFC 4271 Section 9.1.2
    """

    def __init__(self, local_as: int, router_id: str, igp_cost_lookup=None):
        """
        Initialize best path selector

        Args:
            local_as: Local AS number
            router_id: Local router ID
            igp_cost_lookup: Optional callback function to get IGP cost to a next-hop
                            Signature: igp_cost_lookup(next_hop_ip: str) -> Optional[int]
                            Returns None if next-hop is not reachable via IGP
        """
        self.local_as = local_as
        self.router_id = router_id
        self.igp_cost_lookup = igp_cost_lookup
        self.logger = logging.getLogger("BestPathSelector")

    def set_igp_cost_lookup(self, lookup_func):
        """
        Set the IGP cost lookup function for step 6 of best path selection.

        Args:
            lookup_func: Callback function with signature (next_hop_ip: str) -> Optional[int]
        """
        self.igp_cost_lookup = lookup_func
        self.logger.info("IGP cost lookup enabled for best path selection")

    def select_best(self, routes: List[BGPRoute]) -> Optional[BGPRoute]:
        """
        Select best path from candidate routes

        Args:
            routes: List of candidate routes to same prefix

        Returns:
            Best route or None if no routes
        """
        if not routes:
            return None

        if len(routes) == 1:
            return routes[0]

        # Sort routes by decision process
        candidates = routes.copy()

        # Apply decision process
        best = candidates[0]
        for candidate in candidates[1:]:
            result = self.compare(best, candidate)
            if result > 0:  # candidate is better
                best = candidate

        return best

    def compare(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare two routes using BGP decision process

        Args:
            route_a: First route
            route_b: Second route

        Returns:
            -1 if route_a is better
             1 if route_b is better
             0 if equal (should not happen with full tiebreakers)
        """
        # 1. Highest LOCAL_PREF (RFC 4271 Section 9.1.2.1)
        result = self._compare_local_pref(route_a, route_b)
        if result != 0:
            return result

        # 2. Shortest AS_PATH (RFC 4271 Section 9.1.2.2a)
        result = self._compare_as_path_length(route_a, route_b)
        if result != 0:
            return result

        # 3. Lowest ORIGIN (RFC 4271 Section 9.1.2.2b)
        result = self._compare_origin(route_a, route_b)
        if result != 0:
            return result

        # 4. Lowest MED (RFC 4271 Section 9.1.2.2c)
        # Only compare if from same neighbor AS
        result = self._compare_med(route_a, route_b)
        if result != 0:
            return result

        # 5. eBGP > iBGP (RFC 4271 Section 9.1.2.2d)
        result = self._compare_ebgp_ibgp(route_a, route_b)
        if result != 0:
            return result

        # 6. Lowest IGP metric to NEXT_HOP (RFC 4271 Section 9.1.2.2e)
        result = self._compare_igp_metric(route_a, route_b)
        if result != 0:
            return result

        # 7. Oldest route (RFC 4271 Section 9.1.2.2f)
        result = self._compare_age(route_a, route_b)
        if result != 0:
            return result

        # 8. Lowest Router ID (RFC 4271 Section 9.1.2.2g)
        result = self._compare_router_id(route_a, route_b)
        if result != 0:
            return result

        # 9. Lowest peer IP (RFC 4271 Section 9.1.2.2h)
        result = self._compare_peer_ip(route_a, route_b)
        if result != 0:
            return result

        # Should not reach here if all tiebreakers are implemented
        return 0

    def _compare_local_pref(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare LOCAL_PREF (higher is better)

        LOCAL_PREF is a well-known discretionary attribute used for iBGP only.
        If not present, default to 100.
        """
        local_pref_a = 100  # Default
        local_pref_b = 100

        if route_a.has_attribute(ATTR_LOCAL_PREF):
            attr_a = route_a.get_attribute(ATTR_LOCAL_PREF)
            local_pref_a = attr_a.local_pref

        if route_b.has_attribute(ATTR_LOCAL_PREF):
            attr_b = route_b.get_attribute(ATTR_LOCAL_PREF)
            local_pref_b = attr_b.local_pref

        if local_pref_a > local_pref_b:
            return -1  # route_a is better
        elif local_pref_a < local_pref_b:
            return 1  # route_b is better
        else:
            return 0

    def _compare_as_path_length(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare AS_PATH length (shorter is better)

        AS_SET counts as 1, AS_SEQUENCE counts each AS.
        """
        length_a = 0
        length_b = 0

        if route_a.has_attribute(ATTR_AS_PATH):
            attr_a = route_a.get_attribute(ATTR_AS_PATH)
            length_a = attr_a.length()

        if route_b.has_attribute(ATTR_AS_PATH):
            attr_b = route_b.get_attribute(ATTR_AS_PATH)
            length_b = attr_b.length()

        if length_a < length_b:
            return -1  # route_a is better
        elif length_a > length_b:
            return 1  # route_b is better
        else:
            return 0

    def _compare_origin(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare ORIGIN (lower is better: IGP=0 < EGP=1 < INCOMPLETE=2)
        """
        origin_a = ORIGIN_INCOMPLETE  # Default to worst
        origin_b = ORIGIN_INCOMPLETE

        if route_a.has_attribute(ATTR_ORIGIN):
            attr_a = route_a.get_attribute(ATTR_ORIGIN)
            origin_a = attr_a.origin

        if route_b.has_attribute(ATTR_ORIGIN):
            attr_b = route_b.get_attribute(ATTR_ORIGIN)
            origin_b = attr_b.origin

        if origin_a < origin_b:
            return -1  # route_a is better
        elif origin_a > origin_b:
            return 1  # route_b is better
        else:
            return 0

    def _compare_med(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare MED (lower is better)

        MED should only be compared if routes are from the same neighbor AS.
        If not from same AS, skip this comparison.
        """
        # Get neighbor AS from AS_PATH
        neighbor_as_a = self._get_neighbor_as(route_a)
        neighbor_as_b = self._get_neighbor_as(route_b)

        # Only compare MED if from same neighbor AS
        if neighbor_as_a != neighbor_as_b:
            return 0

        med_a = 0  # Default MED is 0 if not present
        med_b = 0

        if route_a.has_attribute(ATTR_MED):
            attr_a = route_a.get_attribute(ATTR_MED)
            med_a = attr_a.med

        if route_b.has_attribute(ATTR_MED):
            attr_b = route_b.get_attribute(ATTR_MED)
            med_b = attr_b.med

        if med_a < med_b:
            return -1  # route_a is better
        elif med_a > med_b:
            return 1  # route_b is better
        else:
            return 0

    def _compare_ebgp_ibgp(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare eBGP vs iBGP (eBGP is better)

        Determine if route is eBGP or iBGP based on neighbor AS.
        """
        neighbor_as_a = self._get_neighbor_as(route_a)
        neighbor_as_b = self._get_neighbor_as(route_b)

        is_ebgp_a = neighbor_as_a != self.local_as
        is_ebgp_b = neighbor_as_b != self.local_as

        if is_ebgp_a and not is_ebgp_b:
            return -1  # route_a is better (eBGP)
        elif not is_ebgp_a and is_ebgp_b:
            return 1  # route_b is better (eBGP)
        else:
            return 0

    def _compare_igp_metric(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare IGP metric to NEXT_HOP (lower is better)

        RFC 4271 Section 9.1.2.2e: Prefer the route with the lowest
        IGP metric to the BGP NEXT_HOP.

        This step requires integration with an IGP (OSPF, IS-IS) to
        determine the cost to reach the next-hop.
        """
        # If no IGP lookup is configured, skip this step
        if not self.igp_cost_lookup:
            return 0

        # Get next-hop from routes
        next_hop_a = route_a.next_hop
        next_hop_b = route_b.next_hop

        if not next_hop_a or not next_hop_b:
            return 0

        # Look up IGP cost to each next-hop
        try:
            cost_a = self.igp_cost_lookup(next_hop_a)
            cost_b = self.igp_cost_lookup(next_hop_b)

            # If either next-hop is unreachable via IGP, skip comparison
            if cost_a is None and cost_b is None:
                return 0
            if cost_a is None:
                return 1  # route_b is better (reachable)
            if cost_b is None:
                return -1  # route_a is better (reachable)

            # Compare costs
            if cost_a < cost_b:
                return -1  # route_a is better (lower cost)
            elif cost_a > cost_b:
                return 1  # route_b is better (lower cost)
            else:
                return 0

        except Exception as e:
            self.logger.debug(f"Error comparing IGP metrics: {e}")
            return 0

    def _compare_age(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare route age (older is better for stability)
        """
        if route_a.timestamp < route_b.timestamp:
            return -1  # route_a is older (better)
        elif route_a.timestamp > route_b.timestamp:
            return 1  # route_b is older (better)
        else:
            return 0

    def _compare_router_id(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare router ID (lower is better)

        Router ID is the BGP identifier from OPEN message, stored in peer_id.
        """
        # Convert to comparable format (IP address integer)
        try:
            id_a = int(ip_address(route_a.peer_id))
            id_b = int(ip_address(route_b.peer_id))

            if id_a < id_b:
                return -1
            elif id_a > id_b:
                return 1
            else:
                return 0
        except (ValueError, TypeError) as e:
            # Fallback to string comparison for invalid IPs
            logging.getLogger("BGP.PathSelection").debug(f"Router ID comparison fallback: {e}")
            if route_a.peer_id < route_b.peer_id:
                return -1
            elif route_a.peer_id > route_b.peer_id:
                return 1
            else:
                return 0

    def _compare_peer_ip(self, route_a: BGPRoute, route_b: BGPRoute) -> int:
        """
        Compare peer IP address (lower is better)

        This is the final tiebreaker.
        """
        try:
            ip_a = int(ip_address(route_a.peer_ip))
            ip_b = int(ip_address(route_b.peer_ip))

            if ip_a < ip_b:
                return -1
            elif ip_a > ip_b:
                return 1
            else:
                return 0
        except (ValueError, TypeError) as e:
            # Fallback to string comparison for invalid IPs
            logging.getLogger("BGP.PathSelection").debug(f"Peer IP comparison fallback: {e}")
            if route_a.peer_ip < route_b.peer_ip:
                return -1
            elif route_a.peer_ip > route_b.peer_ip:
                return 1
            else:
                return 0

    def _get_neighbor_as(self, route: BGPRoute) -> Optional[int]:
        """
        Get neighbor AS number from AS_PATH

        Returns the first AS in the AS_PATH (the neighbor AS).
        """
        if not route.has_attribute(ATTR_AS_PATH):
            return None

        attr = route.get_attribute(ATTR_AS_PATH)

        # Get first AS from AS_PATH
        if attr.segments:
            seg_type, as_list = attr.segments[0]
            if as_list:
                return as_list[0]

        return None

    def run_decision_process(self, adj_rib_in, loc_rib) -> List[str]:
        """
        Run decision process for all prefixes

        Args:
            adj_rib_in: Adjacency RIB In
            loc_rib: Local RIB

        Returns:
            List of prefixes that changed
        """
        changed_prefixes = []

        # Get all prefixes from Adj-RIB-In
        prefixes = adj_rib_in.get_prefixes()

        for prefix in prefixes:
            # Get all candidate routes for this prefix
            routes = adj_rib_in.get_routes(prefix)

            if not routes:
                # No routes, remove from Loc-RIB if present
                if loc_rib.lookup(prefix):
                    loc_rib.remove_route(prefix)
                    changed_prefixes.append(prefix)
                continue

            # Select best path
            best = self.select_best(routes)

            # Check if best path changed
            current_best = loc_rib.lookup(prefix)

            if current_best is None:
                # No current best, install new
                loc_rib.install_route(best)
                changed_prefixes.append(prefix)
            elif current_best.peer_id != best.peer_id:
                # Best path changed
                loc_rib.install_route(best)
                changed_prefixes.append(prefix)

        return changed_prefixes
