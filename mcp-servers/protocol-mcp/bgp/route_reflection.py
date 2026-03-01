"""
BGP Route Reflection (RFC 4456)

Implements BGP route reflection to reduce iBGP mesh requirements.

Route Reflector (RR) reflects routes between clients without requiring
full mesh of iBGP sessions.

Topology:
- Route Reflector (RR): Central router
- Clients: Peers configured as route-reflector-client
- Non-clients: Regular iBGP peers

Reflection Rules (RFC 4456 Section 8):
1. Route from client → Reflect to all clients + all non-clients + all eBGP
2. Route from non-client → Reflect to clients only
3. Route from eBGP → Reflect to all clients + all non-clients

Loop Prevention (RFC 4456 Section 9):
- ORIGINATOR_ID: Router ID of route originator, reject if matches self
- CLUSTER_LIST: List of cluster IDs, reject if own cluster_id present
"""

import logging
from typing import Set, Optional

from .rib import BGPRoute
from .attributes import OriginatorIDAttribute, ClusterListAttribute
from .constants import *


class RouteReflector:
    """
    BGP Route Reflector (RFC 4456)

    Manages route reflection between clients and non-clients.
    """

    def __init__(self, cluster_id: str, router_id: str):
        """
        Initialize route reflector

        Args:
            cluster_id: Cluster ID (typically router ID or configured value)
            router_id: Local router ID
        """
        self.cluster_id = cluster_id
        self.router_id = router_id

        # Peer classification
        self.clients: Set[str] = set()  # Client peer IDs
        self.non_clients: Set[str] = set()  # Non-client iBGP peer IDs

        self.logger = logging.getLogger(f"RouteReflector[{cluster_id}]")

    def add_client(self, peer_id: str) -> None:
        """
        Add peer as route reflector client

        Args:
            peer_id: Peer router ID
        """
        self.clients.add(peer_id)
        if peer_id in self.non_clients:
            self.non_clients.remove(peer_id)
        self.logger.info(f"Added client: {peer_id}")

    def add_non_client(self, peer_id: str) -> None:
        """
        Add peer as non-client iBGP peer

        Args:
            peer_id: Peer router ID
        """
        self.non_clients.add(peer_id)
        if peer_id in self.clients:
            self.clients.remove(peer_id)
        self.logger.info(f"Added non-client: {peer_id}")

    def remove_peer(self, peer_id: str) -> None:
        """
        Remove peer from route reflector

        Args:
            peer_id: Peer router ID
        """
        self.clients.discard(peer_id)
        self.non_clients.discard(peer_id)

    def is_client(self, peer_id: str) -> bool:
        """Check if peer is a client"""
        return peer_id in self.clients

    def is_non_client(self, peer_id: str) -> bool:
        """Check if peer is a non-client"""
        return peer_id in self.non_clients

    def should_reflect(self, route: BGPRoute, from_peer: str, to_peer: str,
                      is_ebgp_source: bool = False) -> bool:
        """
        Determine if route should be reflected to peer

        Args:
            route: BGP route
            from_peer: Source peer ID
            to_peer: Destination peer ID
            is_ebgp_source: True if route originated from eBGP

        Returns:
            True if route should be reflected

        Rules (RFC 4456 Section 8):
        - From client → Reflect to all clients (except source) + all non-clients
        - From non-client → Reflect to clients only
        - From eBGP → Reflect to all clients + all non-clients
        """
        # Don't reflect back to source
        if from_peer == to_peer:
            return False

        # Check loop prevention first
        if self.check_loop(route):
            self.logger.debug(f"Loop detected for route {route.prefix}, not reflecting to {to_peer}")
            return False

        # Route from eBGP peer
        if is_ebgp_source:
            # Reflect to all iBGP peers (clients and non-clients)
            return self.is_client(to_peer) or self.is_non_client(to_peer)

        # Route from client
        if self.is_client(from_peer):
            # Reflect to all other clients and all non-clients
            return self.is_client(to_peer) or self.is_non_client(to_peer)

        # Route from non-client
        if self.is_non_client(from_peer):
            # Reflect to clients only
            return self.is_client(to_peer)

        # Unknown peer relationship, don't reflect
        return False

    def check_loop(self, route: BGPRoute) -> bool:
        """
        Check for routing loops (RFC 4456 Section 9)

        Args:
            route: BGP route

        Returns:
            True if loop detected
        """
        # Check ORIGINATOR_ID (RFC 4456 Section 9)
        if route.has_attribute(ATTR_ORIGINATOR_ID):
            attr = route.get_attribute(ATTR_ORIGINATOR_ID)
            if attr.originator_id == self.router_id:
                self.logger.warning(f"Loop detected: ORIGINATOR_ID matches our router ID")
                return True

        # Check CLUSTER_LIST (RFC 4456 Section 9)
        if route.has_attribute(ATTR_CLUSTER_LIST):
            attr = route.get_attribute(ATTR_CLUSTER_LIST)
            if attr.contains(self.cluster_id):
                self.logger.warning(f"Loop detected: CLUSTER_LIST contains our cluster ID")
                return True

        return False

    def prepare_for_reflection(self, route: BGPRoute, from_peer: str) -> BGPRoute:
        """
        Prepare route for reflection by adding/modifying RR attributes

        Args:
            route: Original route
            from_peer: Source peer ID

        Returns:
            Modified route ready for reflection

        Modifications (RFC 4456 Section 8):
        - Set ORIGINATOR_ID if not present (to source peer ID)
        - Prepend cluster_id to CLUSTER_LIST
        """
        # Create copy to avoid modifying original
        reflected_route = route.copy()

        # Set ORIGINATOR_ID if not present (RFC 4456 Section 8)
        if not reflected_route.has_attribute(ATTR_ORIGINATOR_ID):
            originator_attr = OriginatorIDAttribute(from_peer)
            reflected_route.set_attribute(originator_attr)
            self.logger.debug(f"Set ORIGINATOR_ID to {from_peer}")

        # Prepend cluster_id to CLUSTER_LIST (RFC 4456 Section 8)
        if reflected_route.has_attribute(ATTR_CLUSTER_LIST):
            cluster_attr = reflected_route.get_attribute(ATTR_CLUSTER_LIST)
            cluster_attr.prepend(self.cluster_id)
            self.logger.debug(f"Prepended cluster ID {self.cluster_id} to CLUSTER_LIST")
        else:
            # Create new CLUSTER_LIST with our cluster_id
            cluster_attr = ClusterListAttribute([self.cluster_id])
            reflected_route.set_attribute(cluster_attr)
            self.logger.debug(f"Created CLUSTER_LIST with {self.cluster_id}")

        return reflected_route

    def get_reflection_targets(self, from_peer: str, is_ebgp_source: bool = False) -> Set[str]:
        """
        Get set of peers to reflect route to

        Args:
            from_peer: Source peer ID
            is_ebgp_source: True if route originated from eBGP

        Returns:
            Set of peer IDs to reflect to
        """
        targets = set()

        # Route from eBGP
        if is_ebgp_source:
            # Reflect to all iBGP peers
            targets.update(self.clients)
            targets.update(self.non_clients)

        # Route from client
        elif self.is_client(from_peer):
            # Reflect to all other clients and all non-clients
            targets.update(self.clients)
            targets.update(self.non_clients)
            targets.discard(from_peer)  # Don't reflect back to source

        # Route from non-client
        elif self.is_non_client(from_peer):
            # Reflect to clients only
            targets.update(self.clients)

        return targets

    def get_statistics(self) -> dict:
        """
        Get route reflector statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'cluster_id': self.cluster_id,
            'router_id': self.router_id,
            'clients': len(self.clients),
            'non_clients': len(self.non_clients),
            'client_list': list(self.clients),
            'non_client_list': list(self.non_clients)
        }
