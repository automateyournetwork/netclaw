"""Where documents land. Spec 082, FR-016..FR-020.

Follows feature 046's convention (workspace/skills/threejs-network-viz/output.py) —
persistent, timestamped, uniquely named, gitignored — with one deliberate tightening.

046 relies on timestamp uniqueness alone. Two documents generated in the same second
collide, and `write_text` would silently replace the first. FR-018 says a file MUST
NEVER be overwritten, because a regenerated report must not replace the one already
attached to a ticket. So this opens with O_EXCL and suffixes on collision. The
difference between "unlikely to overwrite" and "cannot" is the whole requirement.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Resolved from __file__ so it works regardless of the caller's cwd — the same reason
# feature 046 does it this way. mcp-servers/document-mcp/output.py → repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DIR = _REPO_ROOT / "workspace" / "output" / "document-mcp"

EXTENSIONS = {"docx": "docx", "xlsx": "xlsx", "pptx": "pptx", "pdfform": "pdf"}


class OutputUnwritable(OSError):
    """The output directory is missing or not writable. Reported as a failure — there
    is deliberately NO fallback to a temp directory the operator will never find."""


def output_dir() -> Path:
    override = os.environ.get("DOCUMENT_OUTPUT_DIR")
    return Path(override).expanduser() if override else _DEFAULT_DIR


def safe_id(output_id: str) -> str:
    """`output_id` is the caller's identifier; this is its sanitised form. Same
    sanitiser as feature 046."""
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in (output_id or "document"))
    return cleaned[:80] or "document"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@dataclass
class OutputArtifact:
    path: str
    bytes: int
    created_at: str
    collision_suffix: int | None = None

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "bytes": self.bytes,
            "created_at": self.created_at,
            "collision_suffix": self.collision_suffix,
        }


def _ensure_dir() -> Path:
    d = output_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputUnwritable(f"output directory {d} could not be created: {exc}") from exc
    if not os.access(d, os.W_OK):
        raise OutputUnwritable(f"output directory {d} is not writable")
    return d


def reserve(kind: str, output_id: str) -> tuple[Path, int | None]:
    """Exclusively create the destination file and return its path.

    Returns the path of a file that now exists and was empty a moment ago. Nothing
    that already existed is ever opened for writing.
    """
    directory = _ensure_dir()
    ext = EXTENSIONS.get(kind, kind)
    base = f"{kind}-{_timestamp()}-{safe_id(output_id)}"

    suffix: int | None = None
    attempt = 0
    while True:
        name = f"{base}.{ext}" if attempt == 0 else f"{base}-{attempt + 1}.{ext}"
        path = directory / name
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            attempt += 1
            suffix = attempt + 1
            if attempt > 999:
                raise OutputUnwritable(
                    f"could not find a free filename under {directory} after 1000 attempts"
                )
            continue
        except OSError as exc:
            raise OutputUnwritable(f"could not create {path}: {exc}") from exc
        os.close(fd)
        return path, suffix


def finalize(path: Path, suffix: int | None) -> OutputArtifact:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise OutputUnwritable(f"wrote {path} but could not stat it: {exc}") from exc
    try:
        rel = str(path.relative_to(_REPO_ROOT))
    except ValueError:
        rel = str(path)
    return OutputArtifact(
        path=rel,
        bytes=size,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        collision_suffix=suffix,
    )


def list_outputs(kind: str | None = None, limit: int = 50) -> list[dict]:
    """What has been generated, newest first, so an operator can find a file."""
    d = output_dir()
    if not d.is_dir():
        return []
    entries = []
    for p in d.iterdir():
        if not p.is_file():
            continue
        if kind and not p.name.startswith(f"{kind}-"):
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        entries.append(
            {
                "name": p.name,
                "kind": p.name.split("-", 1)[0],
                "bytes": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            }
        )
    entries.sort(key=lambda e: e["modified"], reverse=True)
    return entries[: max(1, min(limit, 500))]
