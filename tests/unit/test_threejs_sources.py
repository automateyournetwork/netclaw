"""
Unit tests for sources.py's multi-source composition (spec.md FR-010-FR-013)
and source-selection disambiguation (FR-012).
"""

import sys
from pathlib import Path

import pytest

skill_path = Path(__file__).parent.parent.parent / "workspace" / "skills" / "threejs-network-viz"
sys.path.insert(0, str(skill_path))

from sources import (  # noqa: E402
    AmbiguousSourceError,
    SourceUnreachableError,
    _SOURCE_KIND_ADAPTERS,
    resolve_source,
)

_ALL_SOURCES = list(_SOURCE_KIND_ADAPTERS.keys())


def test_all_eight_sources_have_a_registered_adapter():
    expected = {
        "cml",
        "gns3",
        "containerlab",
        "eve_ng",
        "nautobot",
        "netbox_infrahub",
        "ip_fabric",
        "forward_networks",
    }
    assert set(_SOURCE_KIND_ADAPTERS.keys()) == expected


def test_every_adapter_produces_an_equivalent_snapshot_shape():
    raw = {
        "source": "adapter-parity-test",
        "devices": [{"hostname": "d1", "device_type": "router"}],
        "links": [],
    }
    for source_kind, adapter in _SOURCE_KIND_ADAPTERS.items():
        snapshot = adapter(raw)
        assert snapshot.source_kind.value == source_kind
        assert len(snapshot.devices) == 1
        assert snapshot.devices[0].role.value == "router"


def test_resolve_source_returns_the_only_available_source_with_no_hint():
    assert resolve_source("show me the network", ["cml"]) == "cml"


def test_resolve_source_matches_named_source_in_request_text():
    assert resolve_source("visualize my GNS3 project", _ALL_SOURCES) == "gns3"
    assert resolve_source("replicate the CML lab topology", _ALL_SOURCES) == "cml"


def test_resolve_source_raises_when_ambiguous():
    with pytest.raises(AmbiguousSourceError):
        resolve_source("show me the network", ["cml", "gns3"])


def test_resolve_source_raises_when_no_source_available():
    with pytest.raises(SourceUnreachableError):
        resolve_source("show me the network", [])
