"""Generated inventory tier — a CACHE rendered from a source of truth.

Spec 076 FR-017a, T019.

The loading and marker logic lives in `sources.py`, because it must share one
secret-rejection and attribution path with the other two tiers; splitting it
would create two ways to parse an inventory. This module is the named entry
point plan.md specifies, plus the render half that `sources.py` has no reason to
own.

A generated file is OVERWRITTEN on refresh. It carries `GENERATED_MARKER` so a
refresh can never destroy an operator-authored file — the distinction that stops
"the refresh wiped my edits" (FR-017b).
"""

from __future__ import annotations

from pathlib import Path

from inventory.sources import (
    GENERATED_MARKER,
    Device,
    InventoryError,
    is_generated,
    load_generated as load,
)

__all__ = ["load", "render", "is_generated", "GENERATED_MARKER", "InventoryError"]


def render(devices: list[Device], path: Path) -> Path:
    """Write a generated inventory cache, refusing to clobber an operator file."""
    path = Path(path)
    if path.exists() and not is_generated(path):
        raise InventoryError(
            f"{path} has no generated marker, so it looks operator-authored. "
            f"Refusing to overwrite it — point MULTIVENDOR_GENERATED_PATH elsewhere."
        )
    lines = [f"{GENERATED_MARKER}: true",
             "# Generated from a source of truth. A CACHE — overwritten on refresh.",
             "# Hand edits WILL be lost. For a file you maintain, use the operator tier.",
             "# Contains no credentials, only credential references (FR-017d)."]
    for d in devices:
        lines.append(f"{d.name}:")
        lines.append(f"  hostname: {d.hostname}")
        if d.platform:
            lines.append(f"  platform: {d.platform}")
        if d.groups:
            lines.append(f"  groups: [{', '.join(d.groups)}]")
        lines.append(f"  credential_ref: {d.credential_ref}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path
