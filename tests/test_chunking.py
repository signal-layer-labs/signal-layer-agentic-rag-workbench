import pytest

from app.rag.chunking import TextChunker


def test_chunking_is_stable_and_preserves_overlap() -> None:
    chunker = TextChunker(chunk_size=10, chunk_overlap=3)

    chunks = chunker.split("abcdefghijklmnopqrstuvwxyz")

    assert [(chunk.index, chunk.text) for chunk in chunks] == [
        (0, "abcdefghij"),
        (1, "hijklmnopq"),
        (2, "opqrstuvwx"),
        (3, "vwxyz"),
    ]


def test_chunking_ignores_empty_chunks() -> None:
    chunker = TextChunker(chunk_size=10, chunk_overlap=2)

    assert chunker.split("   ") == []


def test_chunking_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        TextChunker(chunk_size=10, chunk_overlap=10)
