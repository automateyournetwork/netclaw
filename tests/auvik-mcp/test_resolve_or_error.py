"""Tests for resolve_or_error in utils/resolver.py."""

import pytest

from utils.resolver import Resolution, resolve_or_error


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_resolve_or_error_success():
    id_, err = resolve_or_error(Resolution(id="9"))
    assert id_ == "9"
    assert err is None


def test_resolve_or_error_success_long_id():
    id_, err = resolve_or_error(Resolution(id="242216279026467843"))
    assert id_ == "242216279026467843"
    assert err is None


# ---------------------------------------------------------------------------
# Ambiguous path
# ---------------------------------------------------------------------------


def test_resolve_or_error_ambiguous_returns_none_id():
    res = Resolution(
        ambiguous=True,
        candidates=[
            {"id": "1", "name": "sw-01", "ipAddress": "10.0.0.1", "entityType": "device", "tenant": None},
            {"id": "2", "name": "sw-02", "ipAddress": "10.0.0.2", "entityType": "device", "tenant": None},
        ],
    )
    id_, err = resolve_or_error(res)
    assert id_ is None


def test_resolve_or_error_ambiguous_error_code():
    res = Resolution(
        ambiguous=True,
        candidates=[{"id": "1", "name": "x", "ipAddress": None, "entityType": "device", "tenant": None}],
    )
    _, err = resolve_or_error(res)
    assert err is not None
    assert err["error"]["code"] == "Ambiguous"


def test_resolve_or_error_ambiguous_includes_candidates():
    candidates = [
        {"id": "1", "name": "sw-01", "ipAddress": None, "entityType": "device", "tenant": None},
        {"id": "2", "name": "sw-02", "ipAddress": None, "entityType": "device", "tenant": None},
    ]
    res = Resolution(ambiguous=True, candidates=candidates)
    _, err = resolve_or_error(res)
    assert err["error"]["details"]["candidates"] == candidates


def test_resolve_or_error_ambiguous_has_message():
    res = Resolution(ambiguous=True, candidates=[{"id": "1", "name": "x", "ipAddress": None, "entityType": "device", "tenant": None}])
    _, err = resolve_or_error(res)
    assert "message" in err["error"]
    assert len(err["error"]["message"]) > 0


def test_resolve_or_error_ambiguous_custom_label():
    res = Resolution(ambiguous=True, candidates=[{"id": "1", "name": "net-01", "ipAddress": None, "entityType": "network", "tenant": None}])
    _, err = resolve_or_error(res, label="network")
    assert "network" in err["error"]["message"]


# ---------------------------------------------------------------------------
# Not-found path
# ---------------------------------------------------------------------------


def test_resolve_or_error_not_found_returns_none_id():
    id_, err = resolve_or_error(Resolution())
    assert id_ is None


def test_resolve_or_error_not_found_error_code():
    _, err = resolve_or_error(Resolution())
    assert err is not None
    assert err["error"]["code"] == "NotFound"


def test_resolve_or_error_not_found_has_message():
    _, err = resolve_or_error(Resolution())
    assert "message" in err["error"]
    assert len(err["error"]["message"]) > 0


def test_resolve_or_error_not_found_custom_label():
    _, err = resolve_or_error(Resolution(), label="tenant")
    assert "tenant" in err["error"]["message"]
