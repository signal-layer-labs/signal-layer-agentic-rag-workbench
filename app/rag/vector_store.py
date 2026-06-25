from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

import chromadb
from chromadb.api.models.Collection import Collection

MetadataValue = str | int | float | bool
ChunkMetadata = dict[str, MetadataValue]


@dataclass(frozen=True)
class StoredChunk:
    chunk_id: str
    document: str
    metadata: ChunkMetadata


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document: str
    metadata: ChunkMetadata
    distance: float | None


class VectorStore(Protocol):
    def add_chunks(
        self,
        chunks: list[StoredChunk],
        embeddings: list[list[float]],
    ) -> None: ...

    def search(
        self,
        embedding: list[float],
        limit: int,
        where: ChunkMetadata | None = None,
    ) -> list[SearchResult]: ...


class ChromaVectorStore:
    def __init__(self, host: str, port: int, collection_name: str) -> None:
        client = chromadb.HttpClient(host=host, port=port)
        self.collection: Collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        chunks: list[StoredChunk],
        embeddings: list[list[float]],
    ) -> None:
        self.collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.document for chunk in chunks],
            embeddings=cast(Any, embeddings),
            metadatas=[chunk.metadata for chunk in chunks],
        )

    def search(
        self,
        embedding: list[float],
        limit: int,
        where: ChunkMetadata | None = None,
    ) -> list[SearchResult]:
        arguments: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": limit,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            arguments["where"] = where
        response = self.collection.query(**arguments)

        ids = response["ids"][0]
        documents = (response["documents"] or [[]])[0]
        metadatas = (response["metadatas"] or [[]])[0]
        distances = (response["distances"] or [[]])[0]
        return [
            SearchResult(
                chunk_id=chunk_id,
                document=document or "",
                metadata=_normalize_metadata(metadata or {}),
                distance=distance,
            )
            for chunk_id, document, metadata, distance in zip(
                ids,
                documents,
                metadatas,
                distances,
                strict=True,
            )
        ]


def _normalize_metadata(metadata: Mapping[str, object]) -> ChunkMetadata:
    normalized: ChunkMetadata = {}
    for key, value in metadata.items():
        if isinstance(value, str | int | float | bool):
            normalized[key] = value
    return normalized
