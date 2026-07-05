"""
File delivery for the Three.js network topology visualization skill.

Writes each generated scene to a persistent, timestamped, uniquely-named file
under the NetClaw workspace output directory (never overwritten, never
ephemeral — FR-023, Clarification session 2026-07-05) and opens it in the
engineer's default browser with no server process (FR-001).
See contracts/topology-scene-contract.md.
"""

import webbrowser
from datetime import datetime, timezone
from pathlib import Path

# Repo-relative persistent output directory (T004). Resolved relative to this
# file so it works regardless of the caller's current working directory.
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "threejs-network-viz"


def write_scene(html: str, snapshot_id: str) -> Path:
    """Write the generated HTML to a uniquely-named file and return its path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in snapshot_id)
    filename = f"topology-{timestamp}-{safe_id}.html"
    path = OUTPUT_DIR / filename
    path.write_text(html, encoding="utf-8")
    return path


def open_in_browser(path: Path) -> None:
    """Open the generated scene in the engineer's OS-default browser; no server involved."""
    webbrowser.open(path.resolve().as_uri())
