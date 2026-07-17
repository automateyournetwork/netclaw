"""Structure-aware chunking for rag-mcp (FR-010 – FR-012, FR-014).

Strategy: split on heading boundaries first (a Section never mixes with
another), then pack paragraph blocks into chunks targeting 400–800 tokens
with ~10–15% overlap. Atomic blocks (fenced code/CLI/config, tables) are
never split — an oversized atomic block becomes its own chunk.

Every chunk is prefixed with a heading breadcrumb
("Document Title > Chapter > Section") before embedding — the offline
approximation of contextual retrieval that anchors chunks to their document.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional

from ingestion.parsers import ParsedDocument, Section

TARGET_MIN_TOKENS = 400
TARGET_MAX_TOKENS = 800
OVERLAP_RATIO = 0.12  # ~10–15%


@dataclass
class Chunk:
    seq: int
    text: str  # breadcrumb-prefixed, ready to embed
    breadcrumb: str
    section: Optional[str]
    page: Optional[int]
    atomic: bool


def _breadcrumb(title: str, heading_path: List[str]) -> str:
    return " > ".join([title] + [h for h in heading_path if h])


def chunk_document(
    parsed: ParsedDocument,
    count_tokens: Callable[[str], int],
    target_min: int = TARGET_MIN_TOKENS,
    target_max: int = TARGET_MAX_TOKENS,
) -> List[Chunk]:
    chunks: List[Chunk] = []
    seq = 0

    def emit(body: str, section: Section, page: Optional[int], atomic: bool) -> None:
        nonlocal seq
        crumb = _breadcrumb(parsed.title, section.heading_path)
        section_name = section.heading_path[-1] if section.heading_path else None
        chunks.append(
            Chunk(
                seq=seq,
                text=f"{crumb}\n\n{body}",
                breadcrumb=crumb,
                section=section_name,
                page=page,
                atomic=atomic,
            )
        )
        seq += 1

    for section in parsed.sections:
        pending: List[tuple] = []  # (text, page) prose blocks awaiting packing
        pending_tokens = 0
        pending_has_new = False  # guards against emitting overlap-carry only

        def flush(section=section):
            nonlocal pending, pending_tokens, pending_has_new
            if not pending or not pending_has_new:
                return
            body = "\n\n".join(t for t, _ in pending)
            page = next((p for _, p in pending if p is not None), None)
            emit(body, section, page, atomic=False)
            # Overlap: carry the tail of this chunk into the next (FR-010)
            overlap_budget = int(pending_tokens * OVERLAP_RATIO)
            carried, carried_tokens = [], 0
            for text, pg in reversed(pending):
                t = count_tokens(text)
                if carried_tokens + t > overlap_budget:
                    break
                carried.insert(0, (text, pg))
                carried_tokens += t
            pending = carried
            pending_tokens = carried_tokens
            pending_has_new = False

        for kind, text, page in section.blocks:
            if kind == "atomic":
                # Atomic blocks are never split (FR-011). Pack with neighbors
                # when small; standalone chunk when oversized.
                t = count_tokens(text)
                if t >= target_max:
                    flush()
                    pending, pending_tokens, pending_has_new = [], 0, False
                    emit(text, section, page, atomic=True)
                    continue
                if pending_tokens + t > target_max:
                    flush()
                pending.append((text, page))
                pending_tokens += t
                pending_has_new = True
                if pending_tokens >= target_min:
                    flush()
                continue

            t = count_tokens(text)
            if pending_tokens + t > target_max and pending:
                flush()
            pending.append((text, page))
            pending_tokens += t
            pending_has_new = True
            if pending_tokens >= target_min:
                flush()

        # Section boundary: never mix sections in one chunk
        if pending and pending_has_new:
            body = "\n\n".join(t for t, _ in pending)
            page = next((p for _, p in pending if p is not None), None)
            emit(body, section, page, atomic=False)

    return chunks
