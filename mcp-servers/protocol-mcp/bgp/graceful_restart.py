"""
BGP Graceful Restart (RFC 4724)

Implements graceful restart procedures to minimize routing disruption
when BGP sessions go down temporarily.

Key Concepts:
- Stale routes: Routes that survive a session restart
- Restart time: How long to wait for peer to re-establish
- Forwarding state: Keep forwarding during restart
"""

import asyncio
import logging
import time
from typing import Dict, Set, Optional
from enum import IntEnum

from .constants import *
from .rib import BGPRoute


class RestartState(IntEnum):
    """Graceful restart states"""
    NORMAL = 0          # Normal operation
    RESTARTING = 1      # We are restarting
    HELPER = 2          # Peer is restarting, we are helping


class GracefulRestartManager:
    """
    Manages graceful restart procedures per RFC 4724

    Responsibilities:
    - Mark routes as stale when session goes down
    - Start restart timer
    - Remove stale routes after timer expires
    - Handle End-of-RIB markers
    """

    def __init__(self, router_id: str, default_restart_time: int = 120):
        """
        Initialize graceful restart manager

        Args:
            router_id: Local router ID
            default_restart_time: Default restart time in seconds
        """
        self.router_id = router_id
        self.default_restart_time = default_restart_time
        self.logger = logging.getLogger(f"GracefulRestart[{router_id}]")

        # Track per-peer restart state
        self.peer_states: Dict[str, RestartState] = {}

        # Track stale routes per peer
        self.stale_routes: Dict[str, Set[str]] = {}  # peer_ip -> set of prefixes

        # Restart timers per peer
        self.restart_timers: Dict[str, asyncio.Task] = {}

        # Track if we're restarting
        self.is_restarting = False
        self.restart_start_time: Optional[float] = None

    def start_restart(self) -> None:
        """
        Start graceful restart for this router

        Called when we are restarting and want to preserve forwarding state
        """
        self.is_restarting = True
        self.restart_start_time = time.time()
        self.logger.info("Started graceful restart - preserving forwarding state")

    def finish_restart(self) -> None:
        """
        Finish graceful restart

        Called when we've re-established all sessions
        """
        if self.is_restarting:
            elapsed = time.time() - self.restart_start_time if self.restart_start_time else 0
            self.logger.info(f"Completed graceful restart after {elapsed:.1f}s")
            self.is_restarting = False
            self.restart_start_time = None

    def peer_session_down(self, peer_ip: str, routes: Dict[str, BGPRoute],
                          restart_time: Optional[int] = None) -> None:
        """
        Handle peer session going down

        Args:
            peer_ip: Peer IP address
            routes: Current routes from this peer (prefix -> route)
            restart_time: Peer's advertised restart time (or None)
        """
        if restart_time is None:
            restart_time = self.default_restart_time

        # Mark all routes from this peer as stale
        stale_prefixes = set()
        for prefix, route in routes.items():
            route.stale = True
            stale_prefixes.add(prefix)
            self.logger.debug(f"Marked route {prefix} from {peer_ip} as STALE")

        self.stale_routes[peer_ip] = stale_prefixes
        self.peer_states[peer_ip] = RestartState.HELPER

        # Start restart timer
        self._start_restart_timer(peer_ip, restart_time)

        self.logger.info(f"Peer {peer_ip} session down - marked {len(stale_prefixes)} routes as stale, "
                        f"starting {restart_time}s restart timer")

    def peer_session_up(self, peer_ip: str, supports_graceful_restart: bool) -> None:
        """
        Handle peer session coming up

        Args:
            peer_ip: Peer IP address
            supports_graceful_restart: Does peer support graceful restart
        """
        # Cancel restart timer if running
        self._cancel_restart_timer(peer_ip)

        if peer_ip in self.peer_states and self.peer_states[peer_ip] == RestartState.HELPER:
            self.logger.info(f"Peer {peer_ip} re-established session - waiting for End-of-RIB")
            # Keep stale routes until we receive End-of-RIB
        else:
            # New session, no stale routes
            self.peer_states[peer_ip] = RestartState.NORMAL
            if peer_ip in self.stale_routes:
                del self.stale_routes[peer_ip]

    def handle_end_of_rib(self, peer_ip: str, afi: int, safi: int) -> Set[str]:
        """
        Handle End-of-RIB marker from peer

        Args:
            peer_ip: Peer IP address
            afi: Address Family Identifier
            safi: Subsequent Address Family Identifier

        Returns:
            Set of prefix strings to remove (stale routes not refreshed)
        """
        if peer_ip not in self.stale_routes:
            self.logger.debug(f"Received End-of-RIB from {peer_ip} but no stale routes")
            return set()

        # All stale routes not refreshed should be removed
        prefixes_to_remove = self.stale_routes[peer_ip].copy()

        if prefixes_to_remove:
            self.logger.info(f"End-of-RIB from {peer_ip}: removing {len(prefixes_to_remove)} stale routes "
                           f"for AFI={afi} SAFI={safi}")
        else:
            self.logger.info(f"End-of-RIB from {peer_ip}: all routes refreshed for AFI={afi} SAFI={safi}")

        # Clean up
        if peer_ip in self.stale_routes:
            del self.stale_routes[peer_ip]

        self.peer_states[peer_ip] = RestartState.NORMAL

        return prefixes_to_remove

    def route_refreshed(self, peer_ip: str, prefix: str) -> None:
        """
        Mark a route as refreshed (no longer stale)

        Args:
            peer_ip: Peer IP address
            prefix: Route prefix
        """
        if peer_ip in self.stale_routes and prefix in self.stale_routes[peer_ip]:
            self.stale_routes[peer_ip].discard(prefix)
            self.logger.debug(f"Route {prefix} from {peer_ip} refreshed (no longer stale)")

    def _start_restart_timer(self, peer_ip: str, restart_time: int) -> None:
        """
        Start restart timer for peer

        Args:
            peer_ip: Peer IP address
            restart_time: Timer duration in seconds
        """
        # Cancel existing timer if any
        self._cancel_restart_timer(peer_ip)

        # Start new timer
        timer_task = asyncio.create_task(self._restart_timer_expired(peer_ip, restart_time))
        self.restart_timers[peer_ip] = timer_task

    def _cancel_restart_timer(self, peer_ip: str) -> None:
        """
        Cancel restart timer for peer

        Args:
            peer_ip: Peer IP address
        """
        if peer_ip in self.restart_timers:
            self.restart_timers[peer_ip].cancel()
            del self.restart_timers[peer_ip]

    async def _restart_timer_expired(self, peer_ip: str, restart_time: int) -> None:
        """
        Handle restart timer expiration

        Args:
            peer_ip: Peer IP address
            restart_time: Timer duration that expired
        """
        try:
            await asyncio.sleep(restart_time)

            # Timer expired - remove all stale routes
            if peer_ip in self.stale_routes:
                stale_count = len(self.stale_routes[peer_ip])
                self.logger.warning(f"Restart timer expired for {peer_ip} - "
                                  f"removing {stale_count} stale routes")

                # Return stale prefixes (caller should remove them)
                # This would need a callback mechanism

                del self.stale_routes[peer_ip]

            self.peer_states[peer_ip] = RestartState.NORMAL

        except asyncio.CancelledError:
            # Timer was cancelled (peer came back up)
            self.logger.debug(f"Restart timer cancelled for {peer_ip}")

    def is_peer_restarting(self, peer_ip: str) -> bool:
        """
        Check if peer is currently restarting

        Args:
            peer_ip: Peer IP address

        Returns:
            True if peer is in restart state
        """
        return self.peer_states.get(peer_ip, RestartState.NORMAL) == RestartState.HELPER

    def get_stale_route_count(self, peer_ip: str) -> int:
        """
        Get count of stale routes for peer

        Args:
            peer_ip: Peer IP address

        Returns:
            Number of stale routes
        """
        return len(self.stale_routes.get(peer_ip, set()))

    def cleanup_peer(self, peer_ip: str) -> None:
        """
        Clean up state for peer

        Args:
            peer_ip: Peer IP address
        """
        self._cancel_restart_timer(peer_ip)

        if peer_ip in self.stale_routes:
            del self.stale_routes[peer_ip]

        if peer_ip in self.peer_states:
            del self.peer_states[peer_ip]

        self.logger.debug(f"Cleaned up graceful restart state for {peer_ip}")

    def get_statistics(self) -> Dict:
        """
        Get graceful restart statistics

        Returns:
            Dictionary with statistics
        """
        total_stale = sum(len(routes) for routes in self.stale_routes.values())
        restarting_peers = sum(1 for state in self.peer_states.values()
                              if state == RestartState.HELPER)

        return {
            'is_restarting': self.is_restarting,
            'total_stale_routes': total_stale,
            'restarting_peers': restarting_peers,
            'peers_with_stale_routes': len(self.stale_routes),
            'peer_states': {ip: state.name for ip, state in self.peer_states.items()}
        }
