"""
BGP Flow Specification (RFC 5575)

Implements BGP Flowspec for traffic filtering and DDoS mitigation.
Flowspec allows distributing traffic flow specifications via BGP.

Flow Specification Components:
1. Destination Prefix
2. Source Prefix
3. Protocol (TCP=6, UDP=17, ICMP=1)
4. Port (source/destination)
5. DSCP
6. Packet Length
7. Fragment encoding

Actions (Extended Communities):
- Traffic-rate: Rate limit (bytes/sec)
- Traffic-action: Sample, terminate
- Redirect: Redirect to VRF
- Traffic-marking: Set DSCP
"""

import struct
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import IntEnum


class FlowspecComponent(IntEnum):
    """Flowspec component types (RFC 5575 Section 4)"""
    DEST_PREFIX = 1
    SOURCE_PREFIX = 2
    IP_PROTOCOL = 3
    PORT = 4
    DEST_PORT = 5
    SOURCE_PORT = 6
    ICMP_TYPE = 7
    ICMP_CODE = 8
    TCP_FLAGS = 9
    PACKET_LENGTH = 10
    DSCP = 11
    FRAGMENT = 12


class FlowspecAction(IntEnum):
    """Flowspec extended community actions"""
    TRAFFIC_RATE = 0x8006          # Rate limiting
    TRAFFIC_ACTION = 0x8007        # Traffic action (sample/term)
    REDIRECT = 0x8008              # Redirect to VRF
    TRAFFIC_MARKING = 0x8009       # Set DSCP
    REDIRECT_IP = 0x800A           # Redirect to IP


class NumericOperator(IntEnum):
    """Numeric operators for flowspec matching"""
    LESS_THAN = 0x04
    GREATER_THAN = 0x02
    EQUAL = 0x01
    NOT_EQUAL = 0x00


@dataclass
class FlowspecRule:
    """
    A complete flowspec rule with match conditions and actions

    Represents a traffic flow specification
    """
    # Match conditions
    dest_prefix: Optional[str] = None
    source_prefix: Optional[str] = None
    protocols: Optional[List[int]] = None       # IP protocol numbers
    source_ports: Optional[List[int]] = None
    dest_ports: Optional[List[int]] = None
    icmp_types: Optional[List[int]] = None
    icmp_codes: Optional[List[int]] = None
    tcp_flags: Optional[List[Tuple[int, int]]] = None  # (flags, mask)
    packet_lengths: Optional[List[int]] = None
    dscp_values: Optional[List[int]] = None
    fragment_types: Optional[List[str]] = None

    # Actions (extended communities)
    rate_limit: Optional[int] = None            # bytes/sec (0 = drop)
    redirect_vrf: Optional[str] = None
    redirect_ip: Optional[str] = None
    dscp_marking: Optional[int] = None
    sample: bool = False
    terminate: bool = False

    # Metadata
    name: Optional[str] = None
    priority: int = 100

    def matches_traffic(self, packet_info: Dict[str, Any]) -> bool:
        """
        Check if packet matches this flowspec rule

        Args:
            packet_info: Dictionary with packet fields

        Returns:
            True if packet matches all conditions
        """
        # Destination prefix
        if self.dest_prefix and packet_info.get('dest_ip'):
            if not self._prefix_matches(packet_info['dest_ip'], self.dest_prefix):
                return False

        # Source prefix
        if self.source_prefix and packet_info.get('source_ip'):
            if not self._prefix_matches(packet_info['source_ip'], self.source_prefix):
                return False

        # Protocol
        if self.protocols and packet_info.get('protocol'):
            if packet_info['protocol'] not in self.protocols:
                return False

        # Source port
        if self.source_ports and packet_info.get('source_port'):
            if packet_info['source_port'] not in self.source_ports:
                return False

        # Destination port
        if self.dest_ports and packet_info.get('dest_port'):
            if packet_info['dest_port'] not in self.dest_ports:
                return False

        # ICMP type
        if self.icmp_types and packet_info.get('icmp_type') is not None:
            if packet_info['icmp_type'] not in self.icmp_types:
                return False

        # ICMP code
        if self.icmp_codes and packet_info.get('icmp_code') is not None:
            if packet_info['icmp_code'] not in self.icmp_codes:
                return False

        # TCP flags
        if self.tcp_flags and packet_info.get('tcp_flags') is not None:
            matched = False
            for flags, mask in self.tcp_flags:
                if (packet_info['tcp_flags'] & mask) == (flags & mask):
                    matched = True
                    break
            if not matched:
                return False

        # Packet length
        if self.packet_lengths and packet_info.get('packet_length'):
            if packet_info['packet_length'] not in self.packet_lengths:
                return False

        # DSCP
        if self.dscp_values and packet_info.get('dscp') is not None:
            if packet_info['dscp'] not in self.dscp_values:
                return False

        return True

    @staticmethod
    def _prefix_matches(ip: str, prefix: str) -> bool:
        """
        Check if IP matches prefix

        Args:
            ip: IP address string
            prefix: Prefix string (e.g., "192.0.2.0/24")

        Returns:
            True if IP is within prefix
        """
        from ipaddress import ip_address, ip_network
        try:
            ip_obj = ip_address(ip)
            network = ip_network(prefix, strict=False)
            return ip_obj in network
        except ValueError:
            return False


class FlowspecManager:
    """
    Manages BGP Flowspec rules

    Handles flowspec rule installation, matching, and action application
    """

    def __init__(self):
        """Initialize flowspec manager"""
        self.logger = logging.getLogger("FlowspecManager")

        # Active flowspec rules (indexed by priority)
        self.rules: Dict[int, List[FlowspecRule]] = {}

        # Statistics
        self.stats = {
            'total_rules': 0,
            'rules_installed': 0,
            'rules_removed': 0,
            'packets_matched': 0,
            'packets_dropped': 0,
            'packets_rate_limited': 0
        }

    def install_rule(self, rule: FlowspecRule) -> bool:
        """
        Install a flowspec rule

        Args:
            rule: Flowspec rule to install

        Returns:
            True if successfully installed
        """
        priority = rule.priority

        if priority not in self.rules:
            self.rules[priority] = []

        # Check for duplicate
        for existing in self.rules[priority]:
            if self._rules_equal(existing, rule):
                self.logger.debug(f"Flowspec rule already exists: {rule.name}")
                return False

        self.rules[priority].append(rule)
        self.stats['rules_installed'] += 1
        self.stats['total_rules'] += 1

        self.logger.info(f"Installed flowspec rule: {rule.name} (priority {priority})")
        self._log_rule_details(rule)

        return True

    def remove_rule(self, rule: FlowspecRule) -> bool:
        """
        Remove a flowspec rule

        Args:
            rule: Flowspec rule to remove

        Returns:
            True if successfully removed
        """
        priority = rule.priority

        if priority not in self.rules:
            return False

        # Find and remove matching rule
        for i, existing in enumerate(self.rules[priority]):
            if self._rules_equal(existing, rule):
                self.rules[priority].pop(i)
                self.stats['rules_removed'] += 1
                self.stats['total_rules'] -= 1

                if not self.rules[priority]:
                    del self.rules[priority]

                self.logger.info(f"Removed flowspec rule: {rule.name}")
                return True

        return False

    def match_packet(self, packet_info: Dict[str, Any]) -> Optional[FlowspecRule]:
        """
        Match packet against flowspec rules

        Args:
            packet_info: Dictionary with packet fields

        Returns:
            Matching flowspec rule (highest priority) or None
        """
        # Check rules in priority order (lower number = higher priority)
        for priority in sorted(self.rules.keys()):
            for rule in self.rules[priority]:
                if rule.matches_traffic(packet_info):
                    self.stats['packets_matched'] += 1
                    self.logger.debug(f"Packet matched flowspec rule: {rule.name}")
                    return rule

        return None

    def apply_action(self, rule: FlowspecRule, packet_info: Dict[str, Any]) -> str:
        """
        Apply flowspec action to packet

        Args:
            rule: Matching flowspec rule
            packet_info: Packet information

        Returns:
            Action taken ("drop", "rate_limit", "redirect", "mark", "pass")
        """
        # Rate limit (0 = drop)
        if rule.rate_limit is not None:
            if rule.rate_limit == 0:
                self.stats['packets_dropped'] += 1
                self.logger.debug(f"Dropping packet per flowspec rule: {rule.name}")
                return "drop"
            else:
                self.stats['packets_rate_limited'] += 1
                self.logger.debug(f"Rate limiting packet to {rule.rate_limit} bps: {rule.name}")
                return "rate_limit"

        # Redirect to VRF
        if rule.redirect_vrf:
            self.logger.debug(f"Redirecting packet to VRF {rule.redirect_vrf}: {rule.name}")
            return "redirect"

        # Redirect to IP
        if rule.redirect_ip:
            self.logger.debug(f"Redirecting packet to {rule.redirect_ip}: {rule.name}")
            return "redirect"

        # Mark DSCP
        if rule.dscp_marking is not None:
            self.logger.debug(f"Marking packet DSCP to {rule.dscp_marking}: {rule.name}")
            return "mark"

        # Terminate (drop)
        if rule.terminate:
            self.stats['packets_dropped'] += 1
            self.logger.debug(f"Terminating packet per flowspec rule: {rule.name}")
            return "drop"

        # Sample (log and pass)
        if rule.sample:
            self.logger.info(f"Sampling packet: {packet_info}")
            return "pass"

        return "pass"

    def _rules_equal(self, rule1: FlowspecRule, rule2: FlowspecRule) -> bool:
        """
        Check if two rules are equal

        Args:
            rule1: First rule
            rule2: Second rule

        Returns:
            True if rules match
        """
        # Compare all match conditions
        return (rule1.dest_prefix == rule2.dest_prefix and
                rule1.source_prefix == rule2.source_prefix and
                rule1.protocols == rule2.protocols and
                rule1.source_ports == rule2.source_ports and
                rule1.dest_ports == rule2.dest_ports and
                rule1.icmp_types == rule2.icmp_types and
                rule1.icmp_codes == rule2.icmp_codes and
                rule1.tcp_flags == rule2.tcp_flags and
                rule1.packet_lengths == rule2.packet_lengths and
                rule1.dscp_values == rule2.dscp_values)

    def _log_rule_details(self, rule: FlowspecRule) -> None:
        """
        Log flowspec rule details

        Args:
            rule: Flowspec rule
        """
        details = []

        if rule.dest_prefix:
            details.append(f"dest={rule.dest_prefix}")
        if rule.source_prefix:
            details.append(f"src={rule.source_prefix}")
        if rule.protocols:
            details.append(f"proto={rule.protocols}")
        if rule.dest_ports:
            details.append(f"dport={rule.dest_ports}")
        if rule.source_ports:
            details.append(f"sport={rule.source_ports}")

        if rule.rate_limit is not None:
            details.append(f"rate={rule.rate_limit}bps")
        if rule.redirect_vrf:
            details.append(f"redirect-vrf={rule.redirect_vrf}")
        if rule.dscp_marking is not None:
            details.append(f"mark-dscp={rule.dscp_marking}")
        if rule.terminate:
            details.append("action=terminate")

        self.logger.debug(f"  Rule details: {', '.join(details)}")

    def get_statistics(self) -> Dict:
        """
        Get flowspec statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'total_rules': self.stats['total_rules'],
            'rules_by_priority': {p: len(rules) for p, rules in self.rules.items()},
            'packets_matched': self.stats['packets_matched'],
            'packets_dropped': self.stats['packets_dropped'],
            'packets_rate_limited': self.stats['packets_rate_limited'],
            'rules_installed': self.stats['rules_installed'],
            'rules_removed': self.stats['rules_removed']
        }

    def get_all_rules(self) -> List[FlowspecRule]:
        """
        Get all installed rules

        Returns:
            List of all flowspec rules
        """
        all_rules = []
        for priority in sorted(self.rules.keys()):
            all_rules.extend(self.rules[priority])
        return all_rules
