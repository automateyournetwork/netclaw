"""
RPKI (Resource Public Key Infrastructure) Validation (RFC 6811)

Implements RPKI route origin validation against ROAs (Route Origin Authorizations).
RPKI validates that an AS is authorized to originate a prefix.

Validation States:
- Valid: ROA exists, AS and prefix match
- Invalid: ROA exists, but AS or prefix doesn't match
- NotFound (Unknown): No ROA exists for prefix

ROA (Route Origin Authorization):
- Prefix: IP prefix (e.g., 192.0.2.0/24)
- Max Length: Maximum prefix length allowed
- AS Number: Authorized origin AS
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import IntEnum
from ipaddress import ip_network, IPv4Network, IPv6Network


class ValidationState(IntEnum):
    """RPKI validation states (RFC 6811)"""
    VALID = 0           # Route is valid
    INVALID = 1         # Route is invalid (unauthorized origin)
    NOT_FOUND = 2       # No ROA found (unknown)


@dataclass
class ROA:
    """
    Route Origin Authorization

    Represents an RPKI ROA entry
    """
    prefix: str                 # IP prefix (e.g., "192.0.2.0/24")
    max_length: int            # Maximum prefix length
    asn: int                   # Authorized AS number
    source: str = "manual"     # Source of ROA (manual, cache, validator)

    def __post_init__(self):
        """Validate ROA on initialization"""
        # Parse and validate prefix
        try:
            network = ip_network(self.prefix, strict=False)
            self.prefix = str(network)

            # Validate max_length
            if isinstance(network, IPv4Network):
                if self.max_length < network.prefixlen or self.max_length > 32:
                    raise ValueError(f"Invalid max_length {self.max_length} for IPv4 prefix")
            elif isinstance(network, IPv6Network):
                if self.max_length < network.prefixlen or self.max_length > 128:
                    raise ValueError(f"Invalid max_length {self.max_length} for IPv6 prefix")
        except Exception as e:
            raise ValueError(f"Invalid ROA prefix {self.prefix}: {e}")

    def covers(self, prefix: str, prefix_len: int) -> bool:
        """
        Check if this ROA covers a prefix

        Args:
            prefix: Prefix to check
            prefix_len: Prefix length

        Returns:
            True if ROA covers this prefix
        """
        try:
            # Parse both prefixes
            roa_network = ip_network(self.prefix, strict=False)
            check_network = ip_network(f"{prefix}/{prefix_len}", strict=False)

            # Check if check_network is subnet of ROA prefix
            if not check_network.subnet_of(roa_network):
                return False

            # Check max_length
            if prefix_len > self.max_length:
                return False

            return True

        except Exception:
            return False


class RPKIValidator:
    """
    RPKI Origin Validation Manager

    Validates BGP routes against RPKI ROAs
    """

    def __init__(self):
        """Initialize RPKI validator"""
        self.logger = logging.getLogger("RPKIValidator")

        # ROA database indexed by prefix
        self.roas: Dict[str, List[ROA]] = {}

        # Statistics
        self.stats = {
            'total_roas': 0,
            'validations': 0,
            'valid_routes': 0,
            'invalid_routes': 0,
            'not_found_routes': 0
        }

        # Cache validation results (prefix+ASN -> state)
        self.validation_cache: Dict[Tuple[str, int], ValidationState] = {}

    def add_roa(self, roa: ROA) -> bool:
        """
        Add a ROA to the database

        Args:
            roa: ROA to add

        Returns:
            True if added successfully
        """
        prefix_key = self._get_prefix_key(roa.prefix)

        if prefix_key not in self.roas:
            self.roas[prefix_key] = []

        # Check for duplicate
        for existing_roa in self.roas[prefix_key]:
            if (existing_roa.prefix == roa.prefix and
                existing_roa.max_length == roa.max_length and
                existing_roa.asn == roa.asn):
                self.logger.debug(f"ROA already exists: {roa.prefix} AS{roa.asn}")
                return False

        self.roas[prefix_key].append(roa)
        self.stats['total_roas'] += 1

        # Invalidate cache entries that might be affected
        self._invalidate_cache_for_prefix(roa.prefix)

        self.logger.info(f"Added ROA: {roa.prefix} max-length {roa.max_length} AS{roa.asn} "
                        f"(source: {roa.source})")

        return True

    def remove_roa(self, prefix: str, asn: int) -> bool:
        """
        Remove a ROA from the database

        Args:
            prefix: ROA prefix
            asn: ROA ASN

        Returns:
            True if removed
        """
        prefix_key = self._get_prefix_key(prefix)

        if prefix_key not in self.roas:
            return False

        # Find and remove matching ROA
        for i, roa in enumerate(self.roas[prefix_key]):
            if roa.prefix == prefix and roa.asn == asn:
                self.roas[prefix_key].pop(i)
                self.stats['total_roas'] -= 1

                if not self.roas[prefix_key]:
                    del self.roas[prefix_key]

                # Invalidate cache
                self._invalidate_cache_for_prefix(prefix)

                self.logger.info(f"Removed ROA: {prefix} AS{asn}")
                return True

        return False

    def validate_route(self, prefix: str, prefix_len: int, origin_asn: int) -> ValidationState:
        """
        Validate a BGP route against RPKI ROAs

        Args:
            prefix: Route prefix (without length)
            prefix_len: Prefix length
            origin_asn: Origin AS number

        Returns:
            Validation state (VALID, INVALID, or NOT_FOUND)
        """
        self.stats['validations'] += 1

        # Check cache
        cache_key = (f"{prefix}/{prefix_len}", origin_asn)
        if cache_key in self.validation_cache:
            return self.validation_cache[cache_key]

        # Find covering ROAs
        covering_roas = self._find_covering_roas(prefix, prefix_len)

        if not covering_roas:
            # No ROA found
            self.stats['not_found_routes'] += 1
            state = ValidationState.NOT_FOUND
            self.logger.debug(f"RPKI validation: {prefix}/{prefix_len} AS{origin_asn} -> NOT_FOUND")
        else:
            # Check if any ROA matches
            valid = False
            for roa in covering_roas:
                if roa.asn == origin_asn:
                    valid = True
                    break

            if valid:
                state = ValidationState.VALID
                self.stats['valid_routes'] += 1
                self.logger.info(f"RPKI validation: {prefix}/{prefix_len} AS{origin_asn} -> VALID")
            else:
                state = ValidationState.INVALID
                self.stats['invalid_routes'] += 1
                self.logger.warning(f"RPKI validation: {prefix}/{prefix_len} AS{origin_asn} -> INVALID "
                                  f"(authorized ASNs: {[roa.asn for roa in covering_roas]})")

        # Cache result
        self.validation_cache[cache_key] = state

        return state

    def get_roas_for_prefix(self, prefix: str) -> List[ROA]:
        """
        Get all ROAs that cover a prefix

        Args:
            prefix: Prefix with length (e.g., "192.0.2.0/24")

        Returns:
            List of covering ROAs
        """
        try:
            network = ip_network(prefix, strict=False)
            return self._find_covering_roas(str(network.network_address), network.prefixlen)
        except Exception:
            return []

    def _find_covering_roas(self, prefix: str, prefix_len: int) -> List[ROA]:
        """
        Find all ROAs that cover a prefix

        Args:
            prefix: Prefix (without length)
            prefix_len: Prefix length

        Returns:
            List of covering ROAs
        """
        covering = []

        # Check all ROAs (in production, would use more efficient lookup)
        for roa_list in self.roas.values():
            for roa in roa_list:
                if roa.covers(prefix, prefix_len):
                    covering.append(roa)

        return covering

    def _get_prefix_key(self, prefix: str) -> str:
        """
        Get normalized prefix key for indexing

        Args:
            prefix: Prefix string

        Returns:
            Normalized prefix key
        """
        try:
            network = ip_network(prefix, strict=False)
            return f"{network.network_address}/{network.prefixlen}"
        except Exception:
            return prefix

    def _invalidate_cache_for_prefix(self, prefix: str) -> None:
        """
        Invalidate validation cache entries for a prefix

        Args:
            prefix: Prefix that changed
        """
        # Simple approach: clear entire cache
        # Production would be more selective
        self.validation_cache.clear()
        self.logger.debug(f"Invalidated validation cache for {prefix}")

    def load_roas_from_file(self, filename: str) -> int:
        """
        Load ROAs from JSON file

        Args:
            filename: Path to JSON file with ROAs

        Returns:
            Number of ROAs loaded
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            count = 0
            for roa_data in data.get('roas', []):
                try:
                    roa = ROA(
                        prefix=roa_data['prefix'],
                        max_length=roa_data['maxLength'],
                        asn=roa_data['asn'],
                        source=roa_data.get('source', 'file')
                    )
                    if self.add_roa(roa):
                        count += 1
                except Exception as e:
                    self.logger.error(f"Error loading ROA: {e}")

            self.logger.info(f"Loaded {count} ROAs from {filename}")
            return count

        except Exception as e:
            self.logger.error(f"Error loading ROAs from {filename}: {e}")
            return 0

    def export_roas_to_file(self, filename: str) -> bool:
        """
        Export ROAs to JSON file

        Args:
            filename: Path to output JSON file

        Returns:
            True if successful
        """
        try:
            roa_list = []
            for roa_group in self.roas.values():
                for roa in roa_group:
                    roa_list.append({
                        'prefix': roa.prefix,
                        'maxLength': roa.max_length,
                        'asn': roa.asn,
                        'source': roa.source
                    })

            data = {'roas': roa_list}

            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info(f"Exported {len(roa_list)} ROAs to {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting ROAs to {filename}: {e}")
            return False

    def get_statistics(self) -> Dict:
        """
        Get RPKI validation statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'total_roas': self.stats['total_roas'],
            'validations_performed': self.stats['validations'],
            'valid_routes': self.stats['valid_routes'],
            'invalid_routes': self.stats['invalid_routes'],
            'not_found_routes': self.stats['not_found_routes'],
            'cache_size': len(self.validation_cache),
            'roa_prefixes': len(self.roas)
        }

    def clear_all_roas(self) -> None:
        """Clear all ROAs from database"""
        self.roas.clear()
        self.validation_cache.clear()
        self.stats['total_roas'] = 0
        self.logger.info("Cleared all ROAs")
