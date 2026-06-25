from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import AgentRun, RetrievalEvent
from app.main import app
from app.rag.chunking import TextChunker
from app.rag.embeddings import MockEmbeddingProvider
from app.rag.retrieval import RetrievalService, get_retrieval_service
from app.rag.vector_store import ChunkMetadata, SearchResult, StoredChunk
from app.services.run_service import RunService, get_run_service


class InMemoryVectorStore:
    def __init__(self) -> None:
        self.records: list[tuple[StoredChunk, list[float]]] = []

    def add_chunks(
        self,
        chunks: list[StoredChunk],
        embeddings: list[list[float]],
    ) -> None:
        self.records.extend(zip(chunks, embeddings, strict=True))

    def search(
        self,
        embedding: list[float],
        limit: int,
        where: ChunkMetadata | None = None,
    ) -> list[SearchResult]:
        matches = [
            (chunk, vector)
            for chunk, vector in self.records
            if not where
            or all(chunk.metadata.get(key) == value for key, value in where.items())
        ]
        ranked = sorted(
            matches,
            key=lambda item: -sum(
                left * right
                for left, right in zip(item[1], embedding, strict=True)
            ),
        )
        return [
            SearchResult(
                chunk_id=chunk.chunk_id,
                document=chunk.document,
                metadata=chunk.metadata,
                distance=1
                - sum(
                    left * right
                    for left, right in zip(vector, embedding, strict=True)
                ),
            )
            for chunk, vector in ranked[:limit]
        ]


class InMemoryAgentRunRepository:
    def __init__(self, run: AgentRun) -> None:
        self.run = run

    def create(self, business_question: str, summary: str) -> AgentRun:
        return self.run

    def get_by_id(self, run_id: UUID) -> AgentRun | None:
        return self.run if run_id == self.run.id else None

    def list_recent(self, limit: int = 20) -> Sequence[AgentRun]:
        return [self.run][:limit]


class InMemoryRetrievalEventRepository:
    def __init__(self) -> None:
        self.events: list[RetrievalEvent] = []

    def create(
        self,
        run_id: UUID,
        query: str,
        source: str,
        retrieved_items: list[dict[str, object]],
    ) -> RetrievalEvent:
        event = RetrievalEvent(
            id=uuid4(),
            run_id=run_id,
            query=query,
            source=source,
            retrieved_items=retrieved_items,
        )
        self.events.append(event)
        return event


@pytest.fixture
def retrieval_context() -> tuple[
    TestClient,
    UUID,
    InMemoryVectorStore,
    InMemoryRetrievalEventRepository,
]:
    vector_store = InMemoryVectorStore()
    retrieval_service = RetrievalService(
        chunker=TextChunker(chunk_size=30, chunk_overlap=5),
        embedding_provider=MockEmbeddingProvider(),
        vector_store=vector_store,
    )
    run = AgentRun(
        id=uuid4(),
        business_question="What commercial rules apply?",
        status="created",
        summary="Mock run.",
    )
    event_repository = InMemoryRetrievalEventRepository()
    run_service = RunService(
        repository=InMemoryAgentRunRepository(run),
        retrieval_event_repository=event_repository,
    )
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval_service
    app.dependency_overrides[get_run_service] = lambda: run_service
    yield TestClient(app), run.id, vector_store, event_repository
    app.dependency_overrides.clear()


def test_ingest_and_search_documents(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, _, vector_store, _ = retrieval_context
    response = client.post(
        "/documents/ingest",
        json={
            "title": "Commercial Policy",
            "source": "commercial_policy.md",
            "content": (
                "Discount approval rules require manager review for large "
                "commercial concessions."
            ),
            "metadata": {
                "department": "growth",
                "document_type": "policy",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "indexed"
    assert payload["chunks_created"] == len(vector_store.records)
    assert payload["chunks_created"] > 1
    assert len(payload["chunk_ids"]) == payload["chunks_created"]
    assert vector_store.records[0][0].metadata["department"] == "growth"
    assert vector_store.records[0][0].metadata["chunk_index"] == 0

    search_response = client.post(
        "/documents/search",
        json={
            "query": "discount approval rules",
            "limit": 2,
            "where": {"department": "growth"},
        },
    )

    assert search_response.status_code == 200
    assert search_response.json()["query"] == "discount approval rules"
    assert len(search_response.json()["results"]) == 2
    assert "distance" in search_response.json()["results"][0]
    assert "score" not in search_response.json()["results"][0]


def test_run_retrieval_creates_event(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, run_id, _, event_repository = retrieval_context
    client.post(
        "/documents/ingest",
        json={
            "title": "Commercial Policy",
            "source": "commercial_policy.md",
            "content": "Discount approval rules require manager review.",
            "metadata": {"department": "growth"},
        },
    )

    response = client.post(
        f"/runs/{run_id}/retrieve",
        json={"query": "What discount approval rules are relevant?", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == str(run_id)
    assert payload["results"]
    assert len(event_repository.events) == 1
    event = event_repository.events[0]
    assert payload["retrieval_event_id"] == str(event.id)
    assert event.source == "chroma"
    assert event.retrieved_items == payload["results"]


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        (
            {
                "title": "   ",
                "source": "policy.md",
                "content": "Valid content",
            },
            "title",
        ),
        (
            {
                "title": "Policy",
                "source": "   ",
                "content": "Valid content",
            },
            "source",
        ),
        (
            {
                "title": "Policy",
                "source": "policy.md",
                "content": "   ",
            },
            "content",
        ),
    ],
)
def test_ingest_rejects_whitespace_only_fields(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
    payload: dict[str, str],
    field: str,
) -> None:
    client, _, vector_store, _ = retrieval_context

    response = client.post("/documents/ingest", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == field
    assert vector_store.records == []


def test_search_and_run_retrieval_reject_whitespace_only_queries(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, run_id, _, event_repository = retrieval_context

    search_response = client.post(
        "/documents/search",
        json={"query": "   "},
    )
    retrieval_response = client.post(
        f"/runs/{run_id}/retrieve",
        json={"query": "   "},
    )

    assert search_response.status_code == 422
    assert retrieval_response.status_code == 422
    assert event_repository.events == []


def test_ingestion_rejects_content_that_produces_no_chunks(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    _, _, vector_store, _ = retrieval_context
    service = RetrievalService(
        chunker=TextChunker(chunk_size=30, chunk_overlap=5),
        embedding_provider=MockEmbeddingProvider(),
        vector_store=vector_store,
    )

    with pytest.raises(
        ValueError,
        match="Document content did not produce any indexable chunks.",
    ):
        service.ingest("Policy", "policy.md", "   ", {})

    assert vector_store.records == []
