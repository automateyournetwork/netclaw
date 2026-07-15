"""
Unit tests for materials.py's state-color mapping and neutral-default
fallback (spec.md FR-016, FR-017, User Story 4).
"""

import sys
from pathlib import Path

skill_path = Path(__file__).parent.parent.parent / "workspace" / "skills" / "threejs-network-viz"
sys.path.insert(0, str(skill_path))

from materials import DEVICE_ROLE_COLORS, STATE_COLORS, get_state_color  # noqa: E402
from topology_model import OperationalState  # noqa: E402


def test_no_state_color_collides_with_any_role_color():
    """Regression guard: a state overlay must be visually distinguishable
    from EVERY role's base color, not just some of them — a prior palette
    had HEALTHY==SWITCH-green and DOWN==FIREWALL-red, which silently made a
    healthy switch or a down firewall indistinguishable from their own
    always-on role color (found via the scene_builder color-override test)."""
    role_colors = set(DEVICE_ROLE_COLORS.values())
    state_colors = set(STATE_COLORS.values())
    assert role_colors.isdisjoint(state_colors)


def test_healthy_degraded_down_each_have_a_distinct_color():
    colors = {
        get_state_color(OperationalState.HEALTHY),
        get_state_color(OperationalState.DEGRADED),
        get_state_color(OperationalState.DOWN),
    }
    assert len(colors) == 3


def test_absent_state_returns_none_so_caller_falls_back_to_role_color():
    assert get_state_color(None) is None


def test_explicit_unknown_state_still_renders_neutral_not_role_color():
    unknown_color = get_state_color(OperationalState.UNKNOWN)
    assert unknown_color is not None
    assert unknown_color not in (
        get_state_color(OperationalState.HEALTHY),
        get_state_color(OperationalState.DEGRADED),
        get_state_color(OperationalState.DOWN),
    )
