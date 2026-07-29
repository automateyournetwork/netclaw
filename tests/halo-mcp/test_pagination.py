"""Tests for utils.pagination.extract_list (wrapper-key + record_count extraction)."""

from utils.pagination import extract_list


def test_extract_list_bare_list():
    """A bare list payload is returned unchanged with record_count None."""
    items, rc = extract_list([{"id": 1}, {"id": 2}])
    assert items == [{"id": 1}, {"id": 2}]
    assert rc is None


def test_extract_list_wrapped_tickets():
    """The ``tickets`` array and record_count are extracted from a wrapped dict."""
    payload = {"record_count": 2, "tickets": [{"id": 1}, {"id": 2}]}
    items, rc = extract_list(payload)
    assert items == [{"id": 1}, {"id": 2}]
    assert rc == 2


def test_extract_list_wrapped_clients_key():
    """The wrapper key is entity-specific — ``clients`` works the same as tickets."""
    payload = {"record_count": 1, "clients": [{"id": 501}]}
    items, rc = extract_list(payload)
    assert items == [{"id": 501}]
    assert rc == 1


def test_extract_list_ignores_meta_keys_before_item_array():
    """Meta keys (page_no/page_size/guid) are skipped in favour of the item array."""
    payload = {
        "page_no": 1,
        "page_size": 50,
        "guid": ["not-the-items"],
        "record_count": 3,
        "assets": [{"id": 701}],
    }
    items, rc = extract_list(payload)
    assert items == [{"id": 701}]
    assert rc == 3


def test_extract_list_dict_without_item_array():
    """A dict with only meta keys yields no items but preserves record_count."""
    items, rc = extract_list({"record_count": 0, "page_no": 1})
    assert items == []
    assert rc == 0


def test_extract_list_non_dict_non_list():
    """A scalar / None payload yields empty items and record_count None."""
    assert extract_list(None) == ([], None)
    assert extract_list(42) == ([], None)
    assert extract_list("nope") == ([], None)
