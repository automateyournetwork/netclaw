"""Tests for utils/pagination.py (cursor extraction and page merging)."""

from utils.pagination import next_cursor_url, merge_page

_NEXT_URL = "https://x/v1/inventory/device/info?page[after]=ABC&page[first]=300"


def test_next_cursor_url_with_next_link():
    payload = {"links": {"next": _NEXT_URL}}
    assert next_cursor_url(payload) == _NEXT_URL


def test_next_cursor_url_empty_links():
    assert next_cursor_url({"links": {}}) is None


def test_next_cursor_url_no_links_key():
    assert next_cursor_url({}) is None


def test_next_cursor_url_none_next():
    assert next_cursor_url({"links": {"next": None}}) is None


def test_next_cursor_url_empty_string_next():
    assert next_cursor_url({"links": {"next": ""}}) is None


def test_merge_page_into_empty_list():
    result = merge_page([], {"data": [{"id": "1"}]})
    assert result == [{"id": "1"}]


def test_merge_page_appends_to_existing():
    acc = [{"id": "0"}]
    result = merge_page(acc, {"data": [{"id": "1"}, {"id": "2"}]})
    assert result == [{"id": "0"}, {"id": "1"}, {"id": "2"}]


def test_merge_page_no_data_key():
    result = merge_page([], {})
    assert result == []


def test_merge_page_empty_data():
    result = merge_page([{"id": "x"}], {"data": []})
    assert result == [{"id": "x"}]


def test_merge_page_returns_same_list_object():
    """merge_page should mutate and return the accumulator."""
    acc = []
    result = merge_page(acc, {"data": [{"id": "1"}]})
    assert result is acc
