"""
BGP Finite State Machine (RFC 4271 Section 8)

Implements the 6-state BGP FSM with event handling and timers.

States:
- Idle (0): Initial state, refuse connections
- Connect (1): Waiting for TCP connection
- Active (2): TCP connection failed, retry
- OpenSent (3): TCP established, OPEN sent
- OpenConfirm (4): OPEN received, waiting for KEEPALIVE
- Established (5): Peering is up

Events trigger state transitions per RFC 4271 Section 8.2.2
"""

import asyncio
import logging
from typing import Optional, Callable, Dict
from enum import IntEnum

from .constants import *


class BGPEvent(IntEnum):
    """BGP FSM Events (RFC 4271 Section 8.1)"""
    # Administrative events
    ManualStart = 1
    ManualStop = 2
    AutomaticStart = 3
    ManualStart_with_PassiveTcpEstablishment = 4
    AutomaticStart_with_PassiveTcpEstablishment = 5
    AutomaticStart_with_DampPeerOscillations = 6
    AutomaticStart_with_DampPeerOscillations_and_PassiveTcpEstablishment = 7
    AutomaticStop = 8

    # Timer events
    ConnectRetryTimer_Expires = 9
    HoldTimer_Expires = 10
    KeepaliveTimer_Expires = 11
    DelayOpenTimer_Expires = 12
    IdleHoldTimer_Expires = 13

    # TCP events
    TcpConnection_Valid = 14
    Tcp_CR_Invalid = 15
    Tcp_CR_Acked = 16
    TcpConnectionConfirmed = 17
    TcpConnectionFails = 18

    # BGP Message events
    BGPOpen = 19
    BGPOpen_with_DelayOpenTimer_running = 20
    BGPHeaderErr = 21
    BGPOpenMsgErr = 22

    NotifMsgVerErr = 23
    NotifMsg = 24
    KeepAliveMsg = 25
    UpdateMsg = 26
    UpdateMsgErr = 27


class BGPFSM:
    """
    BGP Finite State Machine (RFC 4271 Section 8.2)

    Manages BGP peer state transitions, timers, and callbacks.
    """

    def __init__(self, peer_id: str, local_as: int, peer_as: int,
                 hold_time: int = DEFAULT_HOLD_TIME,
                 connect_retry_time: int = DEFAULT_CONNECT_RETRY_TIME):
        """
        Initialize BGP FSM

        Args:
            peer_id: Peer router ID (or IP if not yet known)
            local_as: Local AS number
            peer_as: Peer AS number
            hold_time: Hold time in seconds
            connect_retry_time: Connect retry time in seconds
        """
        self.peer_id = peer_id
        self.local_as = local_as
        self.peer_as = peer_as

        # Current state
        self.state = STATE_IDLE

        # Timers
        self.hold_time = hold_time
        self.keepalive_time = hold_time // 3 if hold_time > 0 else 0
        self.connect_retry_time = connect_retry_time

        # Timer tasks
        self._connect_retry_timer: Optional[asyncio.Task] = None
        self._hold_timer: Optional[asyncio.Task] = None
        self._keepalive_timer: Optional[asyncio.Task] = None

        # Negotiated hold time (from peer OPEN)
        self.negotiated_hold_time: Optional[int] = None

        # Logger
        self.logger = logging.getLogger(f"BGPFSM[{peer_id}]")

        # Callbacks (set by session manager)
        self.on_state_change: Optional[Callable[[int, int], None]] = None  # (old_state, new_state)
        self.on_established: Optional[Callable[[], None]] = None
        self.on_send_open: Optional[Callable[[], None]] = None
        self.on_send_keepalive: Optional[Callable[[], None]] = None
        self.on_send_notification: Optional[Callable[[int, int], None]] = None  # (error_code, subcode)
        self.on_tcp_connect: Optional[Callable[[], None]] = None
        self.on_tcp_disconnect: Optional[Callable[[], None]] = None

    def get_state(self) -> int:
        """Get current FSM state"""
        return self.state

    def get_state_name(self) -> str:
        """Get current state name"""
        return FSM_STATE_NAMES.get(self.state, f"Unknown({self.state})")

    async def process_event(self, event: BGPEvent) -> None:
        """
        Process BGP FSM event

        Args:
            event: BGP event to process

        This is the main FSM dispatcher following RFC 4271 Section 8.2.2
        """
        old_state = self.state

        self.logger.debug(f"Processing event {event.name} in state {self.get_state_name()}")

        # Dispatch to state-specific handler
        if self.state == STATE_IDLE:
            await self._process_idle(event)
        elif self.state == STATE_CONNECT:
            await self._process_connect(event)
        elif self.state == STATE_ACTIVE:
            await self._process_active(event)
        elif self.state == STATE_OPENSENT:
            await self._process_opensent(event)
        elif self.state == STATE_OPENCONFIRM:
            await self._process_openconfirm(event)
        elif self.state == STATE_ESTABLISHED:
            await self._process_established(event)

        # Call state change callback if state changed
        if self.state != old_state:
            self.logger.info(f"State transition: {FSM_STATE_NAMES[old_state]} → {FSM_STATE_NAMES[self.state]}")
            if self.on_state_change:
                # Callback can be sync or async
                result = self.on_state_change(old_state, self.state)
                if asyncio.iscoroutine(result):
                    await result

            # Call established callback
            if self.state == STATE_ESTABLISHED and self.on_established:
                result = self.on_established()
                if asyncio.iscoroutine(result):
                    await result

    async def _process_idle(self, event: BGPEvent) -> None:
        """Process events in Idle state (RFC 4271 Section 8.2.2)"""
        if event in (BGPEvent.ManualStart, BGPEvent.AutomaticStart):
            # Start connect retry timer
            self._start_connect_retry_timer()

            # Initiate TCP connection
            if self.on_tcp_connect:
                self.on_tcp_connect()

            # Transition to Connect
            self.state = STATE_CONNECT

        elif event in (BGPEvent.ManualStart_with_PassiveTcpEstablishment,
                       BGPEvent.AutomaticStart_with_PassiveTcpEstablishment):
            # Passive mode - wait for incoming connection
            # Start connect retry timer (for failover)
            self._start_connect_retry_timer()

            # Stay in Idle state, waiting for incoming connection
            # When connection comes in, TcpConnectionConfirmed will be sent

        elif event == BGPEvent.TcpConnectionConfirmed:
            # Incoming passive connection accepted
            self._stop_connect_retry_timer()

            # Send OPEN message
            if self.on_send_open:
                self.on_send_open()

            # Start hold timer
            self._start_hold_timer()

            # Transition to OpenSent
            self.state = STATE_OPENSENT

        # All other events are ignored in Idle state

    async def _process_connect(self, event: BGPEvent) -> None:
        """Process events in Connect state"""
        if event == BGPEvent.ManualStop:
            # Stop timers, disconnect, go to Idle
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

        elif event == BGPEvent.TcpConnectionConfirmed:
            # TCP connection established
            self._stop_connect_retry_timer()

            # Send OPEN message
            if self.on_send_open:
                self.on_send_open()

            # Start hold timer
            self._start_hold_timer()

            # Transition to OpenSent
            self.state = STATE_OPENSENT

        elif event == BGPEvent.TcpConnectionFails:
            # TCP connection failed
            self._stop_connect_retry_timer()

            # Restart connect retry timer
            self._start_connect_retry_timer()

            # Transition to Active
            self.state = STATE_ACTIVE

        elif event == BGPEvent.ConnectRetryTimer_Expires:
            # Retry TCP connection
            if self.on_tcp_connect:
                self.on_tcp_connect()

            # Restart timer
            self._start_connect_retry_timer()

            # Stay in Connect

    async def _process_active(self, event: BGPEvent) -> None:
        """Process events in Active state"""
        if event == BGPEvent.ManualStop:
            # Stop timers, disconnect, go to Idle
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

        elif event == BGPEvent.TcpConnectionConfirmed:
            # TCP connection established
            self._stop_connect_retry_timer()

            # Send OPEN message
            if self.on_send_open:
                self.on_send_open()

            # Start hold timer
            self._start_hold_timer()

            # Transition to OpenSent
            self.state = STATE_OPENSENT

        elif event == BGPEvent.ConnectRetryTimer_Expires:
            # Retry TCP connection
            if self.on_tcp_connect:
                self.on_tcp_connect()

            # Restart timer
            self._start_connect_retry_timer()

            # Transition to Connect
            self.state = STATE_CONNECT

    async def _process_opensent(self, event: BGPEvent) -> None:
        """Process events in OpenSent state"""
        if event == BGPEvent.ManualStop:
            # Send NOTIFICATION (Cease), disconnect, go to Idle
            if self.on_send_notification:
                self.on_send_notification(ERR_CEASE, 0)
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

        elif event == BGPEvent.TcpConnectionFails:
            # Connection closed
            self._stop_all_timers()
            self._start_connect_retry_timer()
            self.state = STATE_ACTIVE

        elif event == BGPEvent.BGPOpen:
            # Received valid OPEN message
            # Negotiate hold time (minimum of local and peer)
            # (Hold time negotiation handled by caller)

            # CRITICAL FIX: Restart hold timer (not stop!), start keepalive timer
            # Per RFC 4271, hold timer must continue running in OpenConfirm state
            self._start_hold_timer()  # Restart hold timer with negotiated hold time
            self._start_keepalive_timer()

            # Send KEEPALIVE
            if self.on_send_keepalive:
                self.on_send_keepalive()

            # Transition to OpenConfirm
            self.state = STATE_OPENCONFIRM

        elif event in (BGPEvent.BGPHeaderErr, BGPEvent.BGPOpenMsgErr):
            # Error in OPEN message
            # Send NOTIFICATION, disconnect, go to Idle
            if event == BGPEvent.BGPHeaderErr:
                if self.on_send_notification:
                    self.on_send_notification(ERR_MESSAGE_HEADER, 0)
            else:  # BGPOpenMsgErr
                if self.on_send_notification:
                    self.on_send_notification(ERR_OPEN_MESSAGE, 0)

            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

        elif event == BGPEvent.HoldTimer_Expires:
            # Hold timer expired
            if self.on_send_notification:
                self.on_send_notification(ERR_HOLD_TIMER_EXPIRED, 0)
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

    async def _process_openconfirm(self, event: BGPEvent) -> None:
        """Process events in OpenConfirm state"""
        if event == BGPEvent.ManualStop:
            # Send NOTIFICATION (Cease), disconnect, go to Idle
            if self.on_send_notification:
                self.on_send_notification(ERR_CEASE, 0)
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

        elif event == BGPEvent.TcpConnectionFails:
            # Connection closed
            self._stop_all_timers()
            self.state = STATE_IDLE

        elif event == BGPEvent.KeepAliveMsg:
            # Received KEEPALIVE
            # Restart hold timer
            self._start_hold_timer()

            # Transition to Established
            self.state = STATE_ESTABLISHED

        elif event == BGPEvent.KeepaliveTimer_Expires:
            # Send KEEPALIVE
            if self.on_send_keepalive:
                self.on_send_keepalive()

            # Restart keepalive timer
            self._start_keepalive_timer()

            # Stay in OpenConfirm

        elif event == BGPEvent.HoldTimer_Expires:
            # Hold timer expired
            if self.on_send_notification:
                self.on_send_notification(ERR_HOLD_TIMER_EXPIRED, 0)
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

        elif event in (BGPEvent.BGPHeaderErr, BGPEvent.BGPOpenMsgErr):
            # Protocol error
            if self.on_send_notification:
                self.on_send_notification(ERR_FSM, 0)
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

    async def _process_established(self, event: BGPEvent) -> None:
        """Process events in Established state"""
        if event == BGPEvent.ManualStop:
            # Send NOTIFICATION (Cease), disconnect, go to Idle
            if self.on_send_notification:
                self.on_send_notification(ERR_CEASE, 0)
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

        elif event == BGPEvent.TcpConnectionFails:
            # Connection closed
            self._stop_all_timers()
            self.state = STATE_IDLE

        elif event in (BGPEvent.KeepAliveMsg, BGPEvent.UpdateMsg):
            # Received KEEPALIVE or UPDATE
            # Restart hold timer
            self._start_hold_timer()

            # Stay in Established

        elif event == BGPEvent.KeepaliveTimer_Expires:
            # Send KEEPALIVE
            if self.on_send_keepalive:
                self.on_send_keepalive()

            # Restart keepalive timer
            self._start_keepalive_timer()

            # Stay in Established

        elif event == BGPEvent.HoldTimer_Expires:
            # Hold timer expired
            if self.on_send_notification:
                self.on_send_notification(ERR_HOLD_TIMER_EXPIRED, 0)
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

        elif event in (BGPEvent.BGPHeaderErr, BGPEvent.UpdateMsgErr):
            # Protocol error
            if event == BGPEvent.BGPHeaderErr:
                if self.on_send_notification:
                    self.on_send_notification(ERR_MESSAGE_HEADER, 0)
            else:
                if self.on_send_notification:
                    self.on_send_notification(ERR_UPDATE_MESSAGE, 0)

            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

        elif event == BGPEvent.NotifMsg:
            # Received NOTIFICATION
            self._stop_all_timers()
            if self.on_tcp_disconnect:
                self.on_tcp_disconnect()
            self.state = STATE_IDLE

    # Timer management

    def _start_connect_retry_timer(self) -> None:
        """Start connect retry timer"""
        self._stop_connect_retry_timer()
        if self.connect_retry_time > 0:
            self._connect_retry_timer = asyncio.create_task(
                self._timer_task(self.connect_retry_time, BGPEvent.ConnectRetryTimer_Expires)
            )

    def _stop_connect_retry_timer(self) -> None:
        """Stop connect retry timer"""
        if self._connect_retry_timer:
            self._connect_retry_timer.cancel()
            self._connect_retry_timer = None

    def _start_hold_timer(self) -> None:
        """Start hold timer"""
        self._stop_hold_timer()
        hold_time = self.negotiated_hold_time if self.negotiated_hold_time else self.hold_time
        if hold_time > 0:
            self._hold_timer = asyncio.create_task(
                self._timer_task(hold_time, BGPEvent.HoldTimer_Expires)
            )

    def _stop_hold_timer(self) -> None:
        """Stop hold timer"""
        if self._hold_timer:
            self._hold_timer.cancel()
            self._hold_timer = None

    def _start_keepalive_timer(self) -> None:
        """Start keepalive timer"""
        self._stop_keepalive_timer()
        hold_time = self.negotiated_hold_time if self.negotiated_hold_time else self.hold_time
        keepalive_time = hold_time // 3 if hold_time > 0 else 0
        if keepalive_time > 0:
            self.logger.debug(f"Starting keepalive timer: {keepalive_time} seconds (hold_time={hold_time})")
            self._keepalive_timer = asyncio.create_task(
                self._timer_task(keepalive_time, BGPEvent.KeepaliveTimer_Expires)
            )
        else:
            self.logger.warning(f"Keepalive timer not started: hold_time={hold_time}, keepalive_time={keepalive_time}")

    def _stop_keepalive_timer(self) -> None:
        """Stop keepalive timer"""
        if self._keepalive_timer:
            self._keepalive_timer.cancel()
            self._keepalive_timer = None

    def _stop_all_timers(self) -> None:
        """Stop all FSM timers"""
        self._stop_connect_retry_timer()
        self._stop_hold_timer()
        self._stop_keepalive_timer()

    async def stop(self) -> None:
        """Stop the FSM and clean up resources"""
        self._stop_all_timers()
        self.state = STATE_IDLE
        self.logger.info("FSM stopped")

    async def _timer_task(self, delay: int, event: BGPEvent) -> None:
        """
        Timer task that fires an event after delay

        Args:
            delay: Delay in seconds
            event: Event to fire
        """
        try:
            await asyncio.sleep(delay)
            await self.process_event(event)
        except asyncio.CancelledError:
            # Timer was cancelled
            pass

    def negotiate_hold_time(self, peer_hold_time: int) -> int:
        """
        Negotiate hold time with peer (RFC 4271 Section 4.2)

        Args:
            peer_hold_time: Peer's proposed hold time

        Returns:
            Negotiated hold time (minimum of local and peer)
        """
        if peer_hold_time == 0:
            negotiated = 0
        elif self.hold_time == 0:
            negotiated = 0
        else:
            negotiated = min(self.hold_time, peer_hold_time)

        # Validate negotiated hold time
        if negotiated != 0 and negotiated < MIN_HOLD_TIME:
            # Unacceptable hold time
            return -1

        self.negotiated_hold_time = negotiated
        self.keepalive_time = negotiated // 3 if negotiated > 0 else 0

        return negotiated
