"""Unit tests for the structure-aware chunker (FR-010 – FR-012).

Fully offline: word-count token stand-in, no models.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "rag-mcp"))

from ingestion.chunker import chunk_document  # noqa: E402
from ingestion.parsers import ParsedDocument, Section  # noqa: E402


def count_tokens(text: str) -> int:
    return len(text.split())


def _doc(sections):
    return ParsedDocument(title="Test Doc", sections=sections, page_count=None, content_hash="h")


def _prose(words: int, page=None):
    return ("text", " ".join(f"word{i}" for i in range(words)), page)


def test_heading_boundaries_never_mix_sections():
    doc = _doc(
        [
            Section(heading_path=["Chapter 1"], blocks=[_prose(50)]),
            Section(heading_path=["Chapter 2"], blocks=[_prose(50)]),
        ]
    )
    chunks = chunk_document(doc, count_tokens, target_min=400, target_max=800)
    assert len(chunks) == 2
    assert chunks[0].breadcrumb == "Test Doc > Chapter 1"
    assert chunks[1].breadcrumb == "Test Doc > Chapter 2"


def test_breadcrumb_prefix_on_chunk_text():
    doc = _doc([Section(heading_path=["Ch", "Sec"], blocks=[_prose(10)])])
    chunks = chunk_document(doc, count_tokens)
    assert chunks[0].text.startswith("Test Doc > Ch > Sec\n\n")
    assert chunks[0].section == "Sec"


def test_token_targets_and_packing():
    # 10 paragraphs x 100 words: should pack into chunks of 400-800 tokens
    doc = _doc([Section(heading_path=["Big"], blocks=[_prose(100) for _ in range(10)])])
    chunks = chunk_document(doc, count_tokens, target_min=400, target_max=800)
    assert len(chunks) >= 2
    for c in chunks[:-1]:  # all but the tail respect the min target
        body_tokens = count_tokens(c.text.split("\n\n", 1)[1])
        assert body_tokens <= 800 + 100  # never wildly over max


def test_overlap_carries_tail_between_chunks():
    paragraphs = [_prose(100) for _ in range(10)]
    doc = _doc([Section(heading_path=["Big"], blocks=paragraphs)])
    chunks = chunk_document(doc, count_tokens, target_min=400, target_max=800)
    assert len(chunks) >= 2
    first_body = chunks[0].text.split("\n\n", 1)[1]
    second_body = chunks[1].text.split("\n\n", 1)[1]
    first_paras = first_body.split("\n\n")
    # ~12% overlap of a 400-500 token chunk = the last paragraph carries over
    assert first_paras[-1] in second_body


def test_atomic_block_never_split_when_oversized():
    big_config = "\n".join(f"interface Gi0/0/{i}\n no shutdown" for i in range(400))
    doc = _doc(
        [
            Section(
                heading_path=["Config"],
                blocks=[_prose(50), ("atomic", big_config, None), _prose(50)],
            )
        ]
    )
    chunks = chunk_document(doc, count_tokens, target_min=400, target_max=800)
    atomic_chunks = [c for c in chunks if c.atomic]
    assert len(atomic_chunks) == 1
    assert "Gi0/0/399" in atomic_chunks[0].text and "Gi0/0/0" in atomic_chunks[0].text


def test_small_atomic_block_packs_with_neighbors():
    doc = _doc(
        [
            Section(
                heading_path=["Steps"],
                blocks=[_prose(30), ("atomic", "show version", None), _prose(30)],
            )
        ]
    )
    chunks = chunk_document(doc, count_tokens, target_min=400, target_max=800)
    assert len(chunks) == 1
    assert "show version" in chunks[0].text
    assert chunks[0].atomic is False  # packed prose chunk, not standalone atomic


def test_page_reference_propagates():
    doc = _doc([Section(heading_path=["S"], blocks=[_prose(20, page=31)])])
    chunks = chunk_document(doc, count_tokens)
    assert chunks[0].page == 31


def test_no_duplicate_overlap_only_chunk_at_section_end():
    # Exactly hits the min target so flush() fires, leaving only carried overlap
    doc = _doc([Section(heading_path=["S"], blocks=[_prose(200), _prose(200)])])
    chunks = chunk_document(doc, count_tokens, target_min=400, target_max=800)
    bodies = [c.text.split("\n\n", 1)[1] for c in chunks]
    assert len(bodies) == len(set(bodies))  # no chunk is a pure repeat
