from functools import lru_cache
from uuid import UUID, uuid4

from app.core.budgets import ensure_limit_within_budget
from app.core.config import get_settings
from app.core.errors import AppError, retrieval_failed
from app.rag.chunking import TextChunker
from app.rag.embeddings import EmbeddingProvider, MockEmbeddingProvider
from app.rag.vector_store import (
    ChromaVectorStore,
    ChunkMetadata,
    SearchResult,
    StoredChunk,
    VectorStore,
)


class RetrievalService:
    def __init__(
        self,
        chunker: TextChunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def ingest(
        self,
        title: str,
        source: str,
        content: str,
        metadata: ChunkMetadata,
    ) -> tuple[UUID, list[str]]:
        document_id = uuid4()
        text_chunks = self.chunker.split(content)
        if not text_chunks:
            raise ValueError("Document content did not produce any indexable chunks.")
        total_chunks = len(text_chunks)
        stored_chunks = [
            StoredChunk(
                chunk_id=f"{document_id}:{chunk.index}",
                document=chunk.text,
                metadata={
                    **metadata,
                    "document_id": str(document_id),
                    "title": title,
                    "source": source,
                    "chunk_index": chunk.index,
                    "total_chunks": total_chunks,
                },
            )
            for chunk in text_chunks
        ]
        embeddings = self.embedding_provider.embed_batch(
            [chunk.document for chunk in stored_chunks]
        )
        self.vector_store.add_chunks(stored_chunks, embeddings)
        return document_id, [chunk.chunk_id for chunk in stored_chunks]

    def search(
        self,
        query: str,
        limit: int,
        where: ChunkMetadata | None = None,
    ) -> list[SearchResult]:
        settings = get_settings()
        ensure_limit_within_budget(
            limit=limit,
            max_limit=settings.max_retrieval_results,
            resource_name="retrieval_results",
        )
        try:
            embedding = self.embedding_provider.embed_text(query)
            return self.vector_store.search(embedding, limit, where)
        except AppError:
            raise
        except Exception as error:
            raise retrieval_failed(
                "Document retrieval failed.",
                details={"limit": limit},
            ) from error


@lru_cache
def get_retrieval_service() -> RetrievalService:
    settings = get_settings()
    if settings.embedding_provider != "mock":
        raise ValueError("Only the mock embedding provider is supported.")
    return RetrievalService(
        chunker=TextChunker(settings.chunk_size, settings.chunk_overlap),
        embedding_provider=MockEmbeddingProvider(),
        vector_store=ChromaVectorStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection_name=settings.chroma_collection,
        ),
    )
