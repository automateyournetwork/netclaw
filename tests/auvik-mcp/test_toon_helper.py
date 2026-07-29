"""Tests for utils/toon_helper.py (TOON serialization shim)."""

from utils.toon_helper import gcf_dumps


def test_gcf_dumps_json_fallback():
    out = gcf_dumps({"a": 1, "b": None})
    assert "a" in out and isinstance(out, str)


def test_gcf_dumps_returns_string_for_list():
    out = gcf_dumps([{"id": "1"}, {"id": "2"}])
    assert isinstance(out, str)
    assert "id" in out


def test_gcf_dumps_handles_non_serializable():
    from datetime import datetime

    out = gcf_dumps({"ts": datetime(2026, 1, 1)})
    assert isinstance(out, str)
    assert "2026" in out
