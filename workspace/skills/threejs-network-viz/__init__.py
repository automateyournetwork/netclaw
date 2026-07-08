"""
Three.js browser network topology visualization skill (spec 046).

Top-level orchestration entry point: sources.py -> layout.py (via
scene_builder.py) -> materials.py (via scene_builder.py) -> assets.py
(real-stencil mode only) -> scene_builder.py -> html_template.py -> output.py.
See contracts/topology-scene-contract.md.
"""

from pathlib import Path

import sources
from html_template import render_html
from output import open_in_browser, write_scene
from scene_builder import build_scene_payload
from topology_model import TopologySnapshot

# Re-exported for the conversational orchestration layer (FR-012): call this
# BEFORE fetching raw_topology from any MCP, to determine which source a
# request refers to (or raise AmbiguousSourceError if it's unclear). This
# skill never calls a topology-source MCP itself — the same pattern already
# established by ue5-network-viz's renderer.py, which also only ever
# receives an already-fetched dict.
resolve_source = sources.resolve_source
AmbiguousSourceError = sources.AmbiguousSourceError
SourceUnreachableError = sources.SourceUnreachableError


def visualize_topology(
    source_kind: str,
    raw_topology: dict | None = None,
    freeform_description: str | None = None,
    real_stencil_mode: bool = False,
) -> Path:
    """
    Generate and open a self-contained Three.js visualization for one topology.

    Args:
        source_kind: one of sources._SOURCE_KIND_ADAPTERS' keys, or "freeform"
        raw_topology: the normalized {"devices": [...], "links": [...]} dict
            for a live source (ignored for freeform)
        freeform_description: plain-language topology description (freeform only)
        real_stencil_mode: whether to attempt real 3D model resolution (US5)

    Returns:
        The path to the written HTML file.
    """
    if source_kind == "freeform":
        snapshot: TopologySnapshot = sources.from_freeform(freeform_description or "")
    else:
        adapter = sources._SOURCE_KIND_ADAPTERS.get(source_kind)
        if adapter is None:
            raise sources.SourceUnreachableError(
                source_kind, f"no adapter registered for source_kind={source_kind!r}"
            )
        snapshot = adapter(raw_topology or {})

    snapshot.real_stencil_mode = real_stencil_mode
    if real_stencil_mode:
        import assets

        for device in snapshot.devices:
            device.device_asset, fallback = assets.resolve_device_asset(
                device.hostname, device.role.value, real_stencil_mode=True
            )
            if fallback is not None:
                snapshot.fallback_report.append(fallback)

    payload = build_scene_payload(snapshot)
    html = render_html(payload)
    path = write_scene(html, snapshot.snapshot_id)
    open_in_browser(path)
    return path
