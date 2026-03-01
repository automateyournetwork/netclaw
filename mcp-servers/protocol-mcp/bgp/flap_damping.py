"""
BGP Route Flap Damping (RFC 2439)

Implements route flap damping to reduce the impact of route instability.
Routes that flap (withdraw/announce repeatedly) accumulate penalties.
When penalty exceeds suppress threshold, the route is suppressed.

Key Parameters (RFC 2439 recommendations):
- Suppress threshold: 3000 (route is suppressed)
- Reuse threshold: 750 (route is unsuppressed)
- Half-life: 15 minutes (penalty decays by half)
- Max suppress time: 60 minutes

Penalty Calculation:
- Route withdrawal: +1000 penalty
- Attribute change: +500 penalty
- Penalty decays exponentially with half-life
"""

import time
import math
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class FlapInfo:
    """
    Flap damping information for a route

    Tracks flap history, penalty, and damping state
    """
    prefix: str

    # Penalty state
    penalty: float = 0.0
    last_update: float = field(default_factory=time.time)

    # Flap history
    flap_count: int = 0
    first_flap: float = field(default_factory=time.time)
    last_flap: float = field(default_factory=time.time)

    # Damping state
    is_suppressed: bool = False
    suppress_time: Optional[float] = None

    # History tracking
    withdrawal_count: int = 0
    attribute_change_count: int = 0


class FlapDampingConfig:
    """
    Configuration for route flap damping

    RFC 2439 recommended defaults
    """

    def __init__(self):
        # Thresholds
        self.suppress_threshold = 3000      # Penalty to suppress route
        self.reuse_threshold = 750          # Penalty to reuse route
        self.cutoff_threshold = 1000        # Minimum penalty to track

        # Time parameters
        self.half_life = 15 * 60            # 15 minutes in seconds
        self.max_suppress_time = 60 * 60    # 60 minutes in seconds

        # Penalty weights
        self.withdrawal_penalty = 1000
        self.attribute_change_penalty = 500

        # Calculation constants (derived from half-life)
        self._decay_constant = math.log(2) / self.half_life

    def get_decay_constant(self) -> float:
        """Get decay constant for exponential decay"""
        return self._decay_constant

    def set_half_life(self, half_life_seconds: int) -> None:
        """
        Set half-life and recalculate decay constant

        Args:
            half_life_seconds: Half-life in seconds
        """
        self.half_life = half_life_seconds
        self._decay_constant = math.log(2) / self.half_life


class RouteFlapDamping:
    """
    Route flap damping manager

    Tracks route flaps and applies exponential penalty decay
    """

    def __init__(self, config: Optional[FlapDampingConfig] = None):
        """
        Initialize flap damping

        Args:
            config: Damping configuration (uses defaults if None)
        """
        self.config = config or FlapDampingConfig()
        self.logger = logging.getLogger("RouteFlapDamping")

        # Track flap info per prefix
        self.flap_info: Dict[str, FlapInfo] = {}

        # Statistics
        self.stats = {
            'total_flaps': 0,
            'suppressed_routes': 0,
            'reused_routes': 0,
            'penalties_applied': 0
        }

    def route_withdrawn(self, prefix: str) -> bool:
        """
        Handle route withdrawal event

        Args:
            prefix: Route prefix

        Returns:
            True if route should be suppressed
        """
        info = self._get_or_create_flap_info(prefix)

        # Decay existing penalty
        self._decay_penalty(info)

        # Add withdrawal penalty
        info.penalty += self.config.withdrawal_penalty
        info.withdrawal_count += 1
        info.flap_count += 1
        info.last_flap = time.time()
        info.last_update = time.time()

        self.stats['total_flaps'] += 1
        self.stats['penalties_applied'] += 1

        self.logger.debug(f"Route {prefix} withdrawn - penalty now {info.penalty:.0f} "
                         f"(flaps: {info.flap_count})")

        # Check if should suppress
        if not info.is_suppressed and info.penalty >= self.config.suppress_threshold:
            self._suppress_route(info)
            return True

        return info.is_suppressed

    def route_announced(self, prefix: str, attribute_changed: bool = False) -> bool:
        """
        Handle route announcement event

        Args:
            prefix: Route prefix
            attribute_changed: True if attributes changed from previous announcement

        Returns:
            True if route should be suppressed
        """
        info = self._get_or_create_flap_info(prefix)

        # Decay existing penalty
        self._decay_penalty(info)

        # Add penalty if this is a re-announcement after withdrawal
        if attribute_changed:
            info.penalty += self.config.attribute_change_penalty
            info.attribute_change_count += 1
            info.flap_count += 1
            info.last_flap = time.time()

            self.stats['total_flaps'] += 1
            self.stats['penalties_applied'] += 1

            self.logger.debug(f"Route {prefix} attribute changed - penalty now {info.penalty:.0f}")

        info.last_update = time.time()

        # Check if should suppress
        if not info.is_suppressed and info.penalty >= self.config.suppress_threshold:
            self._suppress_route(info)
            return True

        # Check if should reuse (unsuppress)
        if info.is_suppressed and info.penalty <= self.config.reuse_threshold:
            self._reuse_route(info)
            return False

        return info.is_suppressed

    def is_suppressed(self, prefix: str) -> bool:
        """
        Check if route is currently suppressed

        Args:
            prefix: Route prefix

        Returns:
            True if route is suppressed
        """
        if prefix not in self.flap_info:
            return False

        info = self.flap_info[prefix]

        # Check if suppress time expired
        if info.is_suppressed and info.suppress_time:
            suppress_duration = time.time() - info.suppress_time
            if suppress_duration >= self.config.max_suppress_time:
                self.logger.info(f"Route {prefix} max suppress time reached - forcing reuse")
                self._reuse_route(info)
                return False

        return info.is_suppressed

    def get_penalty(self, prefix: str) -> float:
        """
        Get current penalty for route

        Args:
            prefix: Route prefix

        Returns:
            Current penalty value (decayed)
        """
        if prefix not in self.flap_info:
            return 0.0

        info = self.flap_info[prefix]
        self._decay_penalty(info)
        return info.penalty

    def clear_history(self, prefix: str) -> None:
        """
        Clear flap history for route

        Args:
            prefix: Route prefix
        """
        if prefix in self.flap_info:
            self.logger.info(f"Clearing flap history for {prefix}")
            del self.flap_info[prefix]

    def _get_or_create_flap_info(self, prefix: str) -> FlapInfo:
        """
        Get or create flap info for prefix

        Args:
            prefix: Route prefix

        Returns:
            FlapInfo object
        """
        if prefix not in self.flap_info:
            self.flap_info[prefix] = FlapInfo(prefix=prefix)

        return self.flap_info[prefix]

    def _decay_penalty(self, info: FlapInfo) -> None:
        """
        Apply exponential decay to penalty

        Args:
            info: Flap info object
        """
        if info.penalty <= 0:
            return

        # Calculate time since last update
        elapsed = time.time() - info.last_update

        # Apply exponential decay: P(t) = P(0) * e^(-λt)
        decay_factor = math.exp(-self.config.get_decay_constant() * elapsed)
        info.penalty *= decay_factor

        # Remove from tracking if penalty below cutoff
        if info.penalty < self.config.cutoff_threshold and not info.is_suppressed:
            self.logger.debug(f"Route {info.prefix} penalty decayed below cutoff "
                            f"({info.penalty:.0f}) - clearing history")
            self.flap_info.pop(info.prefix, None)

    def _suppress_route(self, info: FlapInfo) -> None:
        """
        Suppress a route

        Args:
            info: Flap info object
        """
        if not info.is_suppressed:
            info.is_suppressed = True
            info.suppress_time = time.time()
            self.stats['suppressed_routes'] += 1

            self.logger.warning(f"SUPPRESSING route {info.prefix} - penalty {info.penalty:.0f} "
                              f"exceeds threshold {self.config.suppress_threshold} "
                              f"(flaps: {info.flap_count})")

    def _reuse_route(self, info: FlapInfo) -> None:
        """
        Reuse (unsuppress) a route

        Args:
            info: Flap info object
        """
        if info.is_suppressed:
            suppress_duration = time.time() - info.suppress_time if info.suppress_time else 0
            info.is_suppressed = False
            info.suppress_time = None
            self.stats['reused_routes'] += 1

            self.logger.info(f"REUSING route {info.prefix} - penalty decayed to {info.penalty:.0f} "
                           f"below threshold {self.config.reuse_threshold} "
                           f"(suppressed for {suppress_duration:.0f}s)")

    def get_flap_statistics(self, prefix: Optional[str] = None) -> Dict:
        """
        Get flap damping statistics

        Args:
            prefix: Specific prefix (or None for global stats)

        Returns:
            Dictionary with statistics
        """
        if prefix and prefix in self.flap_info:
            info = self.flap_info[prefix]
            self._decay_penalty(info)

            return {
                'prefix': prefix,
                'penalty': info.penalty,
                'flap_count': info.flap_count,
                'withdrawal_count': info.withdrawal_count,
                'attribute_change_count': info.attribute_change_count,
                'is_suppressed': info.is_suppressed,
                'suppress_time': info.suppress_time,
                'age': time.time() - info.first_flap
            }

        # Global statistics
        suppressed_count = sum(1 for info in self.flap_info.values() if info.is_suppressed)

        return {
            'total_flaps': self.stats['total_flaps'],
            'tracked_routes': len(self.flap_info),
            'suppressed_routes': suppressed_count,
            'reused_routes': self.stats['reused_routes'],
            'config': {
                'suppress_threshold': self.config.suppress_threshold,
                'reuse_threshold': self.config.reuse_threshold,
                'half_life_minutes': self.config.half_life / 60,
                'max_suppress_minutes': self.config.max_suppress_time / 60
            }
        }
