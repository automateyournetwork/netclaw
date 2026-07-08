"""
Unit tests for sources.py's freeform topology description parser (FR-014,
FR-015). Covers the "X is a role" / "a role called X" declaration forms,
"A connects to B" / "A - B" / "A -> B" connection forms (including the
whitespace-sensitive bare-hyphen connector, which must never split a
hyphenated hostname like "core-rtr"), and quantity-only phrases ("two
routers") that must NOT double-count a device already named explicitly
elsewhere in the same description.
"""

import sys
from pathlib import Path

skill_path = Path(__file__).parent.parent.parent / "workspace" / "skills" / "threejs-network-viz"
sys.path.insert(0, str(skill_path))

from sources import from_freeform  # noqa: E402


def test_named_role_declaration_and_connection():
    snap = from_freeform("r1 is a router, sw1 is a switch, r1 connects to sw1")
    hosts = {d.hostname: d.role.value for d in snap.devices}
    assert hosts == {"r1": "router", "sw1": "switch"}
    assert len(snap.links) == 1
    assert snap.links[0].endpoint_a.hostname == "r1"
    assert snap.links[0].endpoint_b.hostname == "sw1"


def test_role_called_name_declaration_form():
    snap = from_freeform("a router called r1 and a switch called sw1, r1 connects to sw1")
    hosts = {d.hostname: d.role.value for d in snap.devices}
    assert hosts == {"r1": "router", "sw1": "switch"}


def test_quantity_phrase_does_not_double_count_an_explicitly_named_device():
    """Regression guard: 'sw1 is a switch' must not ALSO be read as 'one more
    unnamed switch' by the quantity-phrase scanner (bug found and fixed
    during implementation of this test)."""
    snap = from_freeform("r1 is a router, sw1 is a switch, r1 connects to sw1")
    assert len(snap.devices) == 2


def test_quantity_only_phrase_generates_clearly_marked_default_names():
    snap = from_freeform("two routers and a switch")
    routers = [d for d in snap.devices if d.role.value == "router"]
    switches = [d for d in snap.devices if d.role.value == "switch"]
    assert len(routers) == 2
    assert len(switches) == 1
    for d in snap.devices:
        assert d.metadata.get("name_source") == "generated"


def test_bare_hyphen_connector_requires_surrounding_whitespace():
    """Regression guard: a bare '-' must only act as a connector when spaced
    out ('r1 - sw1'), and must never split a hyphenated hostname like
    'core-rtr' (bug found and fixed during implementation of this test)."""
    snap = from_freeform("r1 - sw1, sw1 - fw1")
    assert {d.hostname for d in snap.devices} == {"r1", "sw1", "fw1"}
    assert len(snap.links) == 2

    snap2 = from_freeform("core-rtr connects to dist-sw")
    assert {d.hostname for d in snap2.devices} == {"core-rtr", "dist-sw"}
    assert len(snap2.links) == 1


def test_unrecognized_role_falls_back_to_unclassified_not_omitted():
    snap = from_freeform("mystery-box connects to sw1, sw1 is a switch")
    mystery = next(d for d in snap.devices if d.hostname == "mystery-box")
    assert mystery.role.value == "unclassified"
