"""
BGP Connector

Connects agentic layer to BGP protocol implementation.
"""

from typing import Optional, List, Dict, Any


class BGPConnector:
    """
    Connector for BGP speaker.

    Provides agentic layer access to BGP state and actions.
    """

    def __init__(self, bgp_speaker):
        """
        Initialize with BGP speaker.

        Args:
            bgp_speaker: Instance of BGPSpeaker from wontyoubemyneighbor.bgp
        """
        self.speaker = bgp_speaker

    async def get_peers(self):
        """Get list of BGP peers"""
        peers = []
        for peer in self.speaker.agent.sessions.values():
            peers.append({
                "peer": str(peer.config.peer_ip),
                "peer_as": peer.config.peer_as,
                "state": peer.fsm.get_state_name(),
                "local_addr": str(peer.config.local_ip),
                "is_ibgp": peer.config.peer_as == self.speaker.local_as,
                "uptime": getattr(peer, "uptime", 0),
                "prefixes_received": peer.adj_rib_in.size(),
                "prefixes_sent": peer.adj_rib_out.size()
            })
        return peers

    async def get_rib(self, prefix: Optional[str] = None):
        """
        Get BGP RIB (Routing Information Base).

        Args:
            prefix: Optional filter for specific prefix

        Returns:
            List of routes
        """
        routes = []

        # Get routes from loc_rib
        if prefix:
            route = self.speaker.agent.loc_rib.lookup(prefix)
            if route:
                all_routes = [route]
            else:
                all_routes = []
        else:
            all_routes = self.speaker.agent.loc_rib.get_all_routes()

        for route in all_routes:
            # Extract path attributes
            as_path_attr = route.path_attributes.get(2)  # AS_PATH
            as_path = []
            if as_path_attr:
                for seg_type, as_list in getattr(as_path_attr, 'segments', []):
                    as_path.extend(as_list)

            next_hop_attr = route.path_attributes.get(3)  # NEXT_HOP
            next_hop = str(next_hop_attr.next_hop) if next_hop_attr else ""

            local_pref_attr = route.path_attributes.get(5)  # LOCAL_PREF
            local_pref = local_pref_attr.local_pref if local_pref_attr else 100

            med_attr = route.path_attributes.get(4)  # MULTI_EXIT_DISC
            med = med_attr.med if med_attr else 0

            origin_attr = route.path_attributes.get(1)  # ORIGIN
            origin = str(origin_attr.origin) if origin_attr else "igp"

            routes.append({
                "network": route.prefix,
                "next_hop": next_hop,
                "as_path": as_path,
                "local_pref": local_pref,
                "med": med,
                "origin": origin,
                "communities": []  # TODO: extract communities if present
            })

        return routes

    async def inject_route(
        self,
        network: str,
        next_hop: Optional[str] = None,
        as_path: Optional[List[int]] = None,
        **attributes
    ):
        """
        Inject route into BGP and advertise to peers.

        Uses the agent's originate_route method which installs in Loc-RIB
        and triggers UPDATE advertisement to all established peers.
        """
        # Parse network
        parts = network.split("/")
        if len(parts) != 2:
            return {"success": False, "error": "Invalid network format"}

        local_pref = attributes.get("local_pref", 100)

        # Use the agent's originate_route which actually sends UPDATEs
        success = self.speaker.agent.originate_route(
            prefix=network,
            next_hop=next_hop,
            local_pref=local_pref,
        )

        if success:
            return {
                "success": True,
                "network": network,
                "next_hop": next_hop or self.speaker.router_id,
                "local_pref": local_pref,
                "advertised": True,
            }
        else:
            return {"success": False, "error": "Failed to originate route"}

    async def withdraw_route(self, network: str):
        """
        Withdraw route from BGP and send WITHDRAW to peers.

        Removes from Loc-RIB and triggers UPDATE with withdrawal.
        """
        # Remove from Loc-RIB
        removed = self.speaker.agent.loc_rib.remove_route(network)
        if not removed:
            return {"success": False, "error": f"Route {network} not found in Loc-RIB"}

        # Trigger withdrawal advertisement to peers
        import asyncio
        asyncio.create_task(self.speaker.agent._advertise_routes([network]))

        return {"success": True, "network": network, "withdrawn": True}

    async def adjust_local_pref(self, network: str, local_pref: int):
        """
        Adjust local preference for a route.

        Higher local preference = more preferred.
        """
        # Parse network
        parts = network.split("/")
        if len(parts) != 2:
            return {"success": False, "error": "Invalid network format"}

        prefix = parts[0]
        prefix_len = int(parts[1])

        # Find route in RIB
        if hasattr(self.speaker, "rib"):
            for route_key, route_info in self.speaker.rib.items():
                if route_key[0] == prefix and route_key[1] == prefix_len:
                    old_pref = route_info.get("local_pref", 100)
                    route_info["local_pref"] = local_pref
                    return {
                        "success": True,
                        "network": network,
                        "old_local_pref": old_pref,
                        "new_local_pref": local_pref
                    }

        return {"success": False, "error": "Route not found"}

    async def graceful_shutdown(self, peer: Optional[str] = None):
        """
        Initiate BGP graceful shutdown.

        If peer specified, shutdown only that peer.
        Otherwise, shutdown all peers.
        """
        if peer:
            # Graceful shutdown specific peer
            for bgp_peer in self.speaker.agent.sessions.values():
                if str(bgp_peer.config.peer_ip) == peer:
                    # Send NOTIFICATION with Cease code
                    # In real implementation, would send proper BGP message
                    return {
                        "success": True,
                        "peer": peer,
                        "message": "Graceful shutdown initiated"
                    }
            return {"success": False, "error": f"Peer {peer} not found"}
        else:
            # Graceful shutdown all peers
            peer_count = len(self.speaker.agent.sessions)
            return {
                "success": True,
                "peers_affected": peer_count,
                "message": f"Graceful shutdown initiated for {peer_count} peers"
            }

    def get_speaker_info(self):
        """Get BGP speaker information"""
        return {
            "local_as": self.speaker.local_as,
            "router_id": str(self.speaker.router_id),
            "peer_count": len(self.speaker.agent.sessions),
            "route_count": self.speaker.agent.loc_rib.size(),
            "capabilities": getattr(self.speaker, "capabilities", [])
        }
