"""Operator-authored inventory tier — the server NEVER writes to it.

Spec 076 FR-017b, T020.

For operators with no source of truth. The parsing lives in `sources.py` so all
three tiers share one secret-rejection and attribution path; this module is the
named entry point plan.md specifies, and exists to make the read-only contract
explicit at the import site.

There is deliberately no `render`/`write` function here. Its absence is the
guarantee: no code path in this server can overwrite a file an operator maintains.
"""

from __future__ import annotations

from inventory.sources import InventoryError, load_operator as load

__all__ = ["load", "InventoryError"]
