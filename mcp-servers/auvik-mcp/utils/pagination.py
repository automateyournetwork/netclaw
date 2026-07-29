"""Pagination helpers for Auvik JSON:API cursor-based pagination.

Auvik uses cursor-based pagination via ``links.next``. The deprecated
``meta.totalPages`` field is intentionally ignored — all page walking is
driven by the presence of ``links.next``.

Functions:
    next_cursor_url: Extract the next-page URL from a JSON:API response payload.
    merge_page:      Append a page's ``data`` items to an accumulator list.
"""

from typing import Optional


def next_cursor_url(payload: dict) -> Optional[str]:
    """Return the ``links.next`` URL from a JSON:API payload, or None.

    Args:
        payload: Parsed JSON response body containing an optional ``links`` key.

    Returns:
        The next-page URL string, or None if ``links.next`` is absent, None,
        or an empty string.
    """
    links = payload.get("links", {})
    next_url = links.get("next")
    if not next_url:
        return None
    return next_url


def merge_page(acc: list, payload: dict) -> list:
    """Extend *acc* in-place with the ``data`` items from *payload*.

    Args:
        acc:     Accumulator list of already-collected items.
        payload: Parsed JSON response body containing an optional ``data`` key.

    Returns:
        The same *acc* list, extended with items from ``payload["data"]``.
    """
    acc.extend(payload.get("data", []))
    return acc
