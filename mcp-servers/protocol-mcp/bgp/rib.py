"""
BGP Routing Information Base (RIB) Management

Implements three RIBs per RFC 4271 Section 3.2:
- Adj-RIB-In: Routes received from peers before policy
- Loc-RIB: Best routes selected from Adj-RIB-In
- Adj-RIB-Out: Routes to advertise to each peer after policy

Each RIB stores BGPRoute objects containing prefix and path attributes.
"""

import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from ipaddress import IPv4Network, IPv6Network, ip_network

from .attributes import PathAttribute


@dataclass
class BGPRoute:
    """
    BGP Route entry

    Represents a single BGP route with prefix, path attributes, and metadata.
    """
    prefix: str  # "203.0.113.0/24" or "2001:db8::/32"
    prefix_len: int
    path_attributes: Dict[int, PathAttribute]
    peer_id: str  # Peer router ID
    peer_ip: str  # Peer IP address
    timestamp: float = field(default_factory=time.time)

    # Flags
    best: bool = False  # Selected as best path
    stale: bool = False  # Stale route (graceful restart)

    # Address family
    afi: int = 1  # 1=IPv4, 2=IPv6
    safi: int = 1  # 1=Unicast

    # Source
    source: str = "peer"  # "peer", "local", "aggregate"

    # RPKI validation state (0=Valid, 1=Invalid, 2=NotFound)
    validation_state: Optional[int] = None

    def __post_init__(self):
        """Post-initialization to parse prefix length"""
        if '/' in self.prefix:
            self.prefix_len = int(self.prefix.split('/')[1])

        # Determine AFI from prefix
        try:
            net = ip_network(self.prefix, strict=False)
            if isinstance(net, IPv4Network):
                self.afi = 1
            elif isinstance(net, IPv6Network):
                self.afi = 2
        except:
            pass

    def __hash__(self):
        """Hash for use in sets"""
        return hash((self.prefix, self.peer_id))

    def __eq__(self, other):
        """Equality comparison"""
        if not isinstance(other, BGPRoute):
            return False
        return self.prefix == other.prefix and self.peer_id == other.peer_id

    def copy(self) -> 'BGPRoute':
        """Create a copy of this route"""
        return BGPRoute(
            prefix=self.prefix,
            prefix_len=self.prefix_len,
            path_attributes=self.path_attributes.copy(),
            peer_id=self.peer_id,
            peer_ip=self.peer_ip,
            timestamp=self.timestamp,
            best=self.best,
            stale=self.stale,
            afi=self.afi,
            safi=self.safi,
            source=self.source
        )

    def get_attribute(self, attr_type: int) -> Optional[PathAttribute]:
        """Get path attribute by type"""
        return self.path_attributes.get(attr_type)

    def has_attribute(self, attr_type: int) -> bool:
        """Check if route has attribute"""
        return attr_type in self.path_attributes

    def set_attribute(self, attr: PathAttribute) -> None:
        """Set path attribute"""
        self.path_attributes[attr.type_code] = attr

    def remove_attribute(self, attr_type: int) -> None:
        """Remove path attribute"""
        if attr_type in self.path_attributes:
            del self.path_attributes[attr_type]

    @property
    def next_hop(self) -> Optional[str]:
        """
        Get BGP next hop from NEXT_HOP path attribute or IPv6 next hop

        Returns:
            Next hop IP address string or None
        """
        from .constants import ATTR_NEXT_HOP, AFI_IPV6

        # For IPv6 routes, check the stored IPv6 next hop first
        if self.afi == AFI_IPV6 and '_ipv6_next_hop' in self.path_attributes:
            return self.path_attributes['_ipv6_next_hop']

        # For IPv4 routes, check NEXT_HOP attribute
        attr = self.get_attribute(ATTR_NEXT_HOP)
        if attr and hasattr(attr, 'next_hop'):
            return attr.next_hop
        return None


class AdjRIBIn:
    """
    Adjacency RIB In (RFC 4271 Section 3.2)

    Stores routes received from peers before applying import policy
    Multiple routes per prefix (one from each peer)
    """

    def __init__(self):
        # routes[prefix] = [route1, route2, ...]
        self._routes: Dict[str, List[BGPRoute]] = {}

    def add_route(self, route: BGPRoute) -> None:
        """
        Add or update route in Adj-RIB-In

        Args:
            route: BGPRoute to add
        """
        prefix = route.prefix

        if prefix not in self._routes:
            self._routes[prefix] = []

        # Remove existing route from same peer
        self._routes[prefix] = [r for r in self._routes[prefix] if r.peer_id != route.peer_id]

        # Add new route
        self._routes[prefix].append(route)

    def remove_route(self, prefix: str, peer_id: str) -> Optional[BGPRoute]:
        """
        Remove route from Adj-RIB-In

        Args:
            prefix: Route prefix
            peer_id: Peer router ID

        Returns:
            Removed route or None
        """
        if prefix not in self._routes:
            return None

        for i, route in enumerate(self._routes[prefix]):
            if route.peer_id == peer_id:
                removed = self._routes[prefix].pop(i)

                # Clean up empty prefix lists
                if not self._routes[prefix]:
                    del self._routes[prefix]

                return removed

        return None

    def get_routes(self, prefix: str) -> List[BGPRoute]:
        """
        Get all routes for prefix

        Args:
            prefix: Route prefix

        Returns:
            List of routes (may be empty)
        """
        return self._routes.get(prefix, []).copy()

    def get_routes_from_peer(self, peer_id: str) -> List[BGPRoute]:
        """
        Get all routes from specific peer

        Args:
            peer_id: Peer router ID

        Returns:
            List of routes from peer
        """
        routes = []
        for prefix_routes in self._routes.values():
            for route in prefix_routes:
                if route.peer_id == peer_id:
                    routes.append(route)
        return routes

    def remove_all_from_peer(self, peer_id: str) -> List[BGPRoute]:
        """
        Remove all routes from peer (e.g., when peer goes down)

        Args:
            peer_id: Peer router ID

        Returns:
            List of removed routes
        """
        removed = []

        for prefix in list(self._routes.keys()):
            route = self.remove_route(prefix, peer_id)
            if route:
                removed.append(route)

        return removed

    def get_all_routes(self) -> List[BGPRoute]:
        """
        Get all routes in Adj-RIB-In

        Returns:
            List of all routes
        """
        routes = []
        for prefix_routes in self._routes.values():
            routes.extend(prefix_routes)
        return routes

    def get_prefixes(self) -> List[str]:
        """Get list of all prefixes"""
        return list(self._routes.keys())

    def size(self) -> int:
        """Get total number of routes"""
        return sum(len(routes) for routes in self._routes.values())

    def clear(self) -> None:
        """Clear all routes"""
        self._routes.clear()


class LocRIB:
    """
    Local RIB (RFC 4271 Section 3.2)

    Stores best routes selected from Adj-RIB-In after decision process
    One route per prefix (the best one)
    """

    def __init__(self):
        # routes[prefix] = best_route
        self._routes: Dict[str, BGPRoute] = {}

    def install_route(self, route: BGPRoute) -> Optional[BGPRoute]:
        """
        Install route in Loc-RIB

        Args:
            route: BGPRoute to install

        Returns:
            Previously installed route for this prefix, or None
        """
        prefix = route.prefix
        old_route = self._routes.get(prefix)

        # Mark as best
        route.best = True

        # Install
        self._routes[prefix] = route

        return old_route

    def remove_route(self, prefix: str) -> Optional[BGPRoute]:
        """
        Remove route from Loc-RIB

        Args:
            prefix: Route prefix

        Returns:
            Removed route or None
        """
        if prefix in self._routes:
            route = self._routes.pop(prefix)
            route.best = False
            return route
        return None

    def lookup(self, prefix: str) -> Optional[BGPRoute]:
        """
        Lookup route in Loc-RIB

        Args:
            prefix: Route prefix

        Returns:
            Route or None
        """
        return self._routes.get(prefix)

    def get_all_routes(self) -> List[BGPRoute]:
        """
        Get all routes in Loc-RIB

        Returns:
            List of all routes
        """
        return list(self._routes.values())

    def get_prefixes(self) -> List[str]:
        """Get list of all prefixes"""
        return list(self._routes.keys())

    def size(self) -> int:
        """Get number of routes"""
        return len(self._routes)

    def clear(self) -> None:
        """Clear all routes"""
        self._routes.clear()


class AdjRIBOut:
    """
    Adjacency RIB Out (RFC 4271 Section 3.2)

    Stores routes to advertise to each peer after export policy
    Separate RIB per peer
    """

    def __init__(self):
        # routes[peer_id][prefix] = route
        self._routes: Dict[str, Dict[str, BGPRoute]] = {}

    def add_route(self, peer_id: str, route: BGPRoute) -> None:
        """
        Add route to advertise to peer

        Args:
            peer_id: Peer router ID
            route: BGPRoute to advertise
        """
        if peer_id not in self._routes:
            self._routes[peer_id] = {}

        self._routes[peer_id][route.prefix] = route

    def remove_route(self, peer_id: str, prefix: str) -> Optional[BGPRoute]:
        """
        Remove route from Adj-RIB-Out

        Args:
            peer_id: Peer router ID
            prefix: Route prefix

        Returns:
            Removed route or None
        """
        if peer_id in self._routes and prefix in self._routes[peer_id]:
            return self._routes[peer_id].pop(prefix)
        return None

    def get_route(self, peer_id: str, prefix: str) -> Optional[BGPRoute]:
        """
        Get route for peer

        Args:
            peer_id: Peer router ID
            prefix: Route prefix

        Returns:
            Route or None
        """
        if peer_id in self._routes:
            return self._routes[peer_id].get(prefix)
        return None

    def get_routes_for_peer(self, peer_id: str) -> List[BGPRoute]:
        """
        Get all routes for peer

        Args:
            peer_id: Peer router ID

        Returns:
            List of routes
        """
        if peer_id in self._routes:
            return list(self._routes[peer_id].values())
        return []

    def get_prefixes_for_peer(self, peer_id: str) -> List[str]:
        """
        Get all prefixes for peer

        Args:
            peer_id: Peer router ID

        Returns:
            List of prefixes
        """
        if peer_id in self._routes:
            return list(self._routes[peer_id].keys())
        return []

    def remove_all_for_peer(self, peer_id: str) -> List[BGPRoute]:
        """
        Remove all routes for peer

        Args:
            peer_id: Peer router ID

        Returns:
            List of removed routes
        """
        if peer_id in self._routes:
            routes = list(self._routes[peer_id].values())
            del self._routes[peer_id]
            return routes
        return []

    def get_all_routes(self) -> List[BGPRoute]:
        """
        Get all routes across all peers

        Returns:
            List of all routes
        """
        routes = []
        for peer_routes in self._routes.values():
            routes.extend(peer_routes.values())
        return routes

    def get_peer_ids(self) -> List[str]:
        """Get list of peer IDs"""
        return list(self._routes.keys())

    def size(self) -> int:
        """Get total number of routes across all peers"""
        return sum(len(peer_routes) for peer_routes in self._routes.values())

    def clear(self) -> None:
        """Clear all routes for all peers"""
        self._routes.clear()


class RIBManager:
    """
    Manages all three RIBs and coordinates route updates

    Provides high-level operations for route installation and removal.
    """

    def __init__(self):
        self.adj_rib_in = AdjRIBIn()
        self.loc_rib = LocRIB()
        self.adj_rib_out = AdjRIBOut()

    def clear_all(self) -> None:
        """Clear all RIBs"""
        self.adj_rib_in.clear()
        self.loc_rib.clear()
        self.adj_rib_out.clear()

    def get_statistics(self) -> Dict[str, int]:
        """
        Get RIB statistics

        Returns:
            Dictionary with sizes of each RIB
        """
        return {
            'adj_rib_in': self.adj_rib_in.size(),
            'loc_rib': self.loc_rib.size(),
            'adj_rib_out': self.adj_rib_out.size()
        }
