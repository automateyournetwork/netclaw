"""
OSPFv3 Neighbor State Machine
RFC 5340 Section 4.2.3
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional, List
from .constants import *


@dataclass
class OSPFv3Neighbor:
    """
    OSPFv3 Neighbor representation

    Tracks the state of a neighbor relationship on an interface
    """
    # Neighbor identification
    neighbor_id: str  # Router ID
    neighbor_interface_id: int  # Interface ID from Hello
    neighbor_address: str  # IPv6 link-local address

    # State
    state: int = STATE_DOWN

    # Hello packet fields
    priority: int = 1
    designated_router: str = "0.0.0.0"
    backup_designated_router: str = "0.0.0.0"
    options: int = 0

    # Timers
    inactivity_timer: float = 0.0
    dead_interval: int = DEFAULT_DEAD_INTERVAL

    # Database Description exchange
    dd_sequence_number: int = 0
    last_received_dd_sequence: int = 0
    is_master: bool = False
    dd_flags: int = 0

    # Database synchronization
    db_summary_list: List = field(default_factory=list)  # LSA headers to send
    link_state_request_list: List = field(default_factory=list)  # LSAs to request
    link_state_retransmission_list: List = field(default_factory=list)  # LSAs awaiting ack

    # Statistics
    hello_received: int = 0
    dd_received: int = 0
    last_hello_time: float = field(default_factory=time.time)

    def __post_init__(self):
        self.logger = logging.getLogger(f"OSPFv3Neighbor[{self.neighbor_id}@{self.neighbor_address}]")
        self.reset_inactivity_timer()

    def reset_inactivity_timer(self):
        """Reset the inactivity timer based on dead_interval"""
        self.inactivity_timer = time.time() + self.dead_interval

    def is_inactive(self) -> bool:
        """Check if neighbor has timed out"""
        return time.time() > self.inactivity_timer

    def update_from_hello(self, hello_packet) -> bool:
        """
        Update neighbor state from received Hello packet

        Returns:
            True if this is a valid update, False if there's a mismatch
        """
        # Update hello packet fields
        self.priority = hello_packet.router_priority
        self.designated_router = hello_packet.designated_router
        self.backup_designated_router = hello_packet.backup_designated_router
        self.options = hello_packet.options
        self.dead_interval = hello_packet.dead_interval

        # Reset inactivity timer
        self.reset_inactivity_timer()

        # Update statistics
        self.hello_received += 1
        self.last_hello_time = time.time()

        return True

    def transition_state(self, new_state: int, event: str = ""):
        """Transition to a new state with logging"""
        if new_state != self.state:
            old_state_name = STATE_NAMES.get(self.state, f"Unknown-{self.state}")
            new_state_name = STATE_NAMES.get(new_state, f"Unknown-{new_state}")

            self.logger.info(f"State transition: {old_state_name} → {new_state_name} "
                           f"(event: {event})")

            self.state = new_state

    def process_event(self, event: str, **kwargs) -> int:
        """
        Process neighbor event and return new state

        Implements OSPFv3 neighbor state machine (RFC 5340 Section 4.2.3)
        """
        old_state = self.state

        if event == EVENT_HELLO_RECEIVED:
            if self.state == STATE_DOWN:
                self.transition_state(STATE_INIT, event)
            elif self.state >= STATE_INIT:
                # Stay in current state, just reset timer
                self.reset_inactivity_timer()

        elif event == EVENT_2WAY_RECEIVED:
            if self.state == STATE_INIT:
                # Check if we should form adjacency
                should_form_adjacency = kwargs.get('should_form_adjacency', True)
                if should_form_adjacency:
                    self.transition_state(STATE_EXSTART, event)
                else:
                    self.transition_state(STATE_2WAY, event)

        elif event == EVENT_NEGOTIATION_DONE:
            if self.state == STATE_EXSTART:
                self.transition_state(STATE_EXCHANGE, event)

        elif event == EVENT_EXCHANGE_DONE:
            if self.state == STATE_EXCHANGE:
                if len(self.link_state_request_list) == 0:
                    self.transition_state(STATE_FULL, event)
                else:
                    self.transition_state(STATE_LOADING, event)

        elif event == EVENT_LOADING_DONE:
            if self.state == STATE_LOADING:
                self.transition_state(STATE_FULL, event)

        elif event == EVENT_ADJ_OK:
            should_form_adjacency = kwargs.get('should_form_adjacency', True)
            if self.state == STATE_2WAY and should_form_adjacency:
                self.transition_state(STATE_EXSTART, event)
            elif self.state >= STATE_EXSTART and not should_form_adjacency:
                self.transition_state(STATE_2WAY, event)

        elif event == EVENT_1WAY:
            if self.state >= STATE_2WAY:
                self.transition_state(STATE_INIT, event)

        elif event == EVENT_INACTIVITY_TIMER or event == EVENT_KILL_NBR or event == EVENT_LL_DOWN:
            self.transition_state(STATE_DOWN, event)

        elif event == EVENT_SEQ_NUMBER_MISMATCH or event == EVENT_BAD_LS_REQ:
            if self.state >= STATE_EXCHANGE:
                self.transition_state(STATE_EXSTART, event)

        return self.state

    def is_adjacent(self) -> bool:
        """Check if neighbor is in a state where adjacency exists"""
        return self.state >= STATE_EXSTART

    def is_full(self) -> bool:
        """Check if neighbor is fully adjacent"""
        return self.state == STATE_FULL

    def is_two_way_or_better(self) -> bool:
        """Check if neighbor is at least in 2-Way state"""
        return self.state >= STATE_2WAY

    def get_statistics(self) -> dict:
        """Get neighbor statistics"""
        return {
            'neighbor_id': self.neighbor_id,
            'neighbor_address': self.neighbor_address,
            'state': STATE_NAMES.get(self.state, f"Unknown-{self.state}"),
            'state_value': self.state,
            'priority': self.priority,
            'designated_router': self.designated_router,
            'backup_designated_router': self.backup_designated_router,
            'hello_received': self.hello_received,
            'dd_received': self.dd_received,
            'is_master': self.is_master,
            'dead_time_remaining': max(0, int(self.inactivity_timer - time.time())),
            'db_summary_list_size': len(self.db_summary_list),
            'request_list_size': len(self.link_state_request_list),
            'retransmit_list_size': len(self.link_state_retransmission_list)
        }

    def __str__(self) -> str:
        state_name = STATE_NAMES.get(self.state, f"Unknown-{self.state}")
        return (f"Neighbor {self.neighbor_id} [{self.neighbor_address}] "
                f"State={state_name} Priority={self.priority}")
