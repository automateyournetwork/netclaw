"""Page-based pagination helpers for the Halo API.

Halo list endpoints paginate with ``pageinate=true`` + ``page_no`` + ``page_size``
(server cap 100) and wrap results as ``{record_count, <entity>: [...]}`` where the
wrapper key varies by endpoint (``tickets``, ``clients``, ``assets``, ...).

``extract_list()`` finds that item array and the total ``record_count`` regardless
of the wrapper key, so the client's ``get_all()`` can aggregate pages uniformly.
"""

from typing import Any, Optional, Tuple

# Keys that appear alongside the item array in a wrapped list payload and are
# therefore NOT the item array themselves.
_META_KEYS = {
    "record_count",
    "page_no",
    "page_size",
    "pageinate",
    "page_count",
    "count",
    "$type",
    "guid",
}


def extract_list(payload: Any) -> Tuple[list, Optional[int]]:
    """Return ``(items, record_count)`` from a Halo list response.

    Handles three shapes:
    - a bare list (some endpoints return the array directly) -> (payload, None)
    - a wrapped dict ``{record_count, <entity>: [...]}`` -> (that array, record_count)
    - anything else -> ([], None)
    """
    if isinstance(payload, list):
        return payload, None
    if not isinstance(payload, dict):
        return [], None

    record_count = payload.get("record_count")
    for key, value in payload.items():
        if key in _META_KEYS:
            continue
        if isinstance(value, list):
            return value, record_count
    return [], record_count
