"""
OSPFv3 Link State Database (LSDB)
RFC 5340 Section 4.4
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from .constants import *
from .packets import LSAHeader
from .lsa import *


@dataclass
class LSAInstance:
    """Wrapper for LSA with metadata"""
    header: LSAHeader
    body: bytes
    lsa_object: object = None  # Decoded LSA object
    install_time: float = field(default_factory=time.time)
    received_time: float = field(default_factory=time.time)

    def get_age(self) -> int:
        """Get current LSA age in seconds"""
        current_age = self.header.ls_age + int(time.time() - self.received_time)
        return min(current_age, MAX_AGE)

    def is_maxage(self) -> bool:
        """Check if LSA has reached MaxAge"""
        return self.get_age() >= MAX_AGE

    def get_key(self) -> Tuple:
        """Get unique key for this LSA"""
        return (
            self.header.ls_type,
            self.header.advertising_router,
            self.header.link_state_id
        )


class OSPFv3LSDB:
    """
    OSPFv3 Link State Database

    Stores and manages LSAs organized by flooding scope and type
    """

    def __init__(self, area_id: str = "0.0.0.0"):
        self.area_id = area_id
        self.logger = logging.getLogger(f"OSPFv3LSDB[{area_id}]")

        # LSA storage: key = (ls_type, adv_router, ls_id) -> LSAInstance
        self.lsas: Dict[Tuple, LSAInstance] = {}

        # Statistics
        self.stats = {
            'total_lsas': 0,
            'router_lsas': 0,
            'network_lsas': 0,
            'link_lsas': 0,
            'intra_area_prefix_lsas': 0,
            'inter_area_prefix_lsas': 0,
            'as_external_lsas': 0,
            'maxage_lsas': 0,
            'lsas_installed': 0,
            'lsas_updated': 0,
            'lsas_removed': 0
        }

    def install_lsa(self, header: LSAHeader, body: bytes,
                    from_self: bool = False) -> Optional[LSAInstance]:
        """
        Install or update LSA in database

        Args:
            header: LSA header
            body: LSA body bytes
            from_self: True if this is a self-originated LSA

        Returns:
            LSAInstance if installed/updated, None if rejected
        """
        key = (header.ls_type, header.advertising_router, header.link_state_id)

        # Decode LSA
        lsa_object = decode_lsa(header, body)

        # Check if we already have this LSA
        existing = self.lsas.get(key)

        if existing:
            # Compare sequence numbers to determine if this is newer
            if self._is_newer(header, existing.header):
                self.logger.debug(f"Updating LSA: {self._lsa_str(header)}")

                # Update existing LSA
                existing.header = header
                existing.body = body
                existing.lsa_object = lsa_object
                existing.received_time = time.time()

                self.stats['lsas_updated'] += 1
                self._update_stats()

                return existing
            else:
                self.logger.debug(f"Rejecting older LSA: {self._lsa_str(header)}")
                return None
        else:
            # New LSA
            self.logger.info(f"Installing new LSA: {self._lsa_str(header)}")

            instance = LSAInstance(
                header=header,
                body=body,
                lsa_object=lsa_object
            )

            self.lsas[key] = instance
            self.stats['lsas_installed'] += 1
            self._update_stats()

            return instance

    def remove_lsa(self, ls_type: int, adv_router: str, link_state_id: int) -> bool:
        """Remove LSA from database"""
        key = (ls_type, adv_router, link_state_id)

        if key in self.lsas:
            lsa = self.lsas[key]
            self.logger.info(f"Removing LSA: {self._lsa_str(lsa.header)}")

            del self.lsas[key]
            self.stats['lsas_removed'] += 1
            self._update_stats()

            return True

        return False

    def lookup_lsa(self, ls_type: int, adv_router: str,
                   link_state_id: int) -> Optional[LSAInstance]:
        """Lookup LSA by key"""
        key = (ls_type, adv_router, link_state_id)
        return self.lsas.get(key)

    def get_lsas_by_type(self, ls_type: int) -> List[LSAInstance]:
        """Get all LSAs of a specific type"""
        return [lsa for lsa in self.lsas.values()
                if lsa.header.ls_type == ls_type]

    def get_lsas_by_router(self, adv_router: str) -> List[LSAInstance]:
        """Get all LSAs from a specific router"""
        return [lsa for lsa in self.lsas.values()
                if lsa.header.advertising_router == adv_router]

    def get_all_lsas(self) -> List[LSAInstance]:
        """Get all LSAs in database"""
        return list(self.lsas.values())

    def get_lsa_headers(self) -> List[LSAHeader]:
        """Get headers of all LSAs"""
        return [lsa.header for lsa in self.lsas.values()]

    def age_lsas(self) -> List[LSAInstance]:
        """
        Age all LSAs and return list of MaxAge LSAs

        Should be called periodically
        """
        maxage_lsas = []

        for lsa in self.lsas.values():
            current_age = lsa.get_age()

            if current_age >= MAX_AGE:
                maxage_lsas.append(lsa)

        return maxage_lsas

    def flush_maxage_lsas(self):
        """Remove all MaxAge LSAs from database"""
        to_remove = []

        for key, lsa in self.lsas.items():
            if lsa.is_maxage():
                to_remove.append(key)

        for key in to_remove:
            self.logger.debug(f"Flushing MaxAge LSA: {key}")
            del self.lsas[key]
            self.stats['lsas_removed'] += 1

        if to_remove:
            self._update_stats()

    def _is_newer(self, new_header: LSAHeader, old_header: LSAHeader) -> bool:
        """
        Determine if new LSA is more recent than old LSA
        RFC 5340 Section 4.6 (same as OSPFv2)
        """
        # Compare sequence numbers
        if new_header.ls_sequence_number > old_header.ls_sequence_number:
            return True
        elif new_header.ls_sequence_number < old_header.ls_sequence_number:
            return False

        # Sequence numbers equal, compare checksums
        if new_header.ls_checksum > old_header.ls_checksum:
            return True
        elif new_header.ls_checksum < old_header.ls_checksum:
            return False

        # Checksums equal, check if only new one is MaxAge
        new_age = new_header.ls_age
        old_age = old_header.ls_age

        if new_age == MAX_AGE and old_age != MAX_AGE:
            return True

        # Check age difference
        if abs(new_age - old_age) > MAX_AGE_DIFF:
            if new_age < old_age:
                return True

        return False

    def _update_stats(self):
        """Update statistics counters"""
        self.stats['total_lsas'] = len(self.lsas)
        self.stats['router_lsas'] = len(self.get_lsas_by_type(ROUTER_LSA))
        self.stats['network_lsas'] = len(self.get_lsas_by_type(NETWORK_LSA))
        self.stats['link_lsas'] = len(self.get_lsas_by_type(LINK_LSA))
        self.stats['intra_area_prefix_lsas'] = len(self.get_lsas_by_type(INTRA_AREA_PREFIX_LSA))
        self.stats['inter_area_prefix_lsas'] = len(self.get_lsas_by_type(INTER_AREA_PREFIX_LSA))
        self.stats['as_external_lsas'] = len(self.get_lsas_by_type(AS_EXTERNAL_LSA))

        # Count MaxAge LSAs
        self.stats['maxage_lsas'] = sum(1 for lsa in self.lsas.values() if lsa.is_maxage())

    def _lsa_str(self, header: LSAHeader) -> str:
        """Format LSA for logging"""
        lsa_type_name = LSA_TYPE_NAMES.get(header.ls_type, f"0x{header.ls_type:04x}")
        return (f"{lsa_type_name} from {header.advertising_router} "
                f"ID={header.link_state_id} Seq=0x{header.ls_sequence_number:08x}")

    def get_statistics(self) -> Dict:
        """Get LSDB statistics"""
        self._update_stats()
        return dict(self.stats)

    def __len__(self) -> int:
        """Return number of LSAs in database"""
        return len(self.lsas)

    def __str__(self) -> str:
        """String representation"""
        return f"OSPFv3 LSDB Area {self.area_id}: {len(self.lsas)} LSAs"
