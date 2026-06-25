from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str


class TextChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        start = 0
        while start < len(text):
            chunk_text = text[start : start + self.chunk_size].strip()
            if chunk_text:
                chunks.append(TextChunk(index=len(chunks), text=chunk_text))
            if start + self.chunk_size >= len(text):
                break
            start += self.chunk_size - self.chunk_overlap
        return chunks
