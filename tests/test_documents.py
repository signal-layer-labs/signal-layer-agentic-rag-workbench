from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import AgentRun, RetrievalEvent
from app.documents.markdown_parser import MarkdownParser
from app.documents.service import DocumentParsingService
from app.documents.text_parser import PlainTextParser
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


def test_text_parser_parses_utf8_text() -> None:
    parsed = PlainTextParser().parse(
        "commercial_policy.txt",
        b"Discount approval rules require manager review.",
        "text/plain",
    )

    assert parsed.title == "commercial_policy"
    assert parsed.source == "commercial_policy.txt"
    assert parsed.content == "Discount approval rules require manager review."
    assert parsed.parser == "text"


def test_text_parser_rejects_blank_content() -> None:
    with pytest.raises(ValueError, match="Parsed document content cannot be blank"):
        PlainTextParser().parse(
            "commercial_policy.txt",
            b"   ",
            "text/plain",
        )


def test_text_parser_rejects_invalid_utf8() -> None:
    with pytest.raises(
        ValueError,
        match="Document content must be valid UTF-8 text.",
    ):
        PlainTextParser().parse(
            "commercial_policy.txt",
            b"\xff\xfe\xfd",
            "text/plain",
        )


def test_markdown_parser_parses_markdown_text() -> None:
    parsed = MarkdownParser().parse(
        "commercial_policy.md",
        b"# Commercial Policy\n\nDiscount approval rules apply.",
        "text/markdown",
    )

    assert parsed.title == "commercial_policy"
    assert parsed.parser == "markdown"
    assert "# Commercial Policy" in parsed.content


def test_markdown_parser_rejects_invalid_utf8() -> None:
    with pytest.raises(
        ValueError,
        match="Document content must be valid UTF-8 text.",
    ):
        MarkdownParser().parse(
            "commercial_policy.md",
            b"\xff\xfe\xfd",
            "text/markdown",
        )


def test_parser_service_selects_parser_by_extension() -> None:
    service = DocumentParsingService()

    parsed = service.parse(
        filename="commercial_policy.md",
        content=b"# Commercial Policy\n\nDiscount approval rules apply.",
        content_type="text/markdown",
    )

    assert parsed.parser == "markdown"
    assert parsed.metadata["original_filename"] == "commercial_policy.md"


def test_parser_service_rejects_unsupported_file_type() -> None:
    service = DocumentParsingService()

    with pytest.raises(ValueError, match="Unsupported document type for parsing"):
        service.parse(
            filename="commercial_policy.csv",
            content=b"header,value",
            content_type="text/csv",
        )


def test_parser_service_rejects_blank_parsed_content() -> None:
    service = DocumentParsingService()

    with pytest.raises(ValueError, match="Parsed document content cannot be blank"):
        service.parse(
            filename="commercial_policy.md",
            content=b"   ",
            content_type="text/markdown",
        )


def test_parse_document_returns_preview_and_metadata(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, _, _, _ = retrieval_context

    response = client.post(
        "/documents/parse",
        files={
            "file": (
                "commercial_policy.md",
                b"# Commercial Policy\n\nDiscount approval rules apply.",
                "text/markdown",
            )
        },
        data={"metadata": '{"department":"growth"}'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "commercial_policy"
    assert payload["source"] == "commercial_policy.md"
    assert payload["parser"] == "markdown"
    assert payload["content_type"] == "text/markdown"
    assert payload["metadata"]["department"] == "growth"
    assert payload["metadata"]["original_filename"] == "commercial_policy.md"


def test_parse_ingest_reuses_ingestion_and_creates_chunks(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, _, vector_store, _ = retrieval_context

    response = client.post(
        "/documents/parse-ingest",
        files={
            "file": (
                "commercial_policy.md",
                (
                    b"# Commercial Policy\n\nDiscount approval rules require "
                    b"manager review for large concessions."
                ),
                "text/markdown",
            )
        },
        data={"metadata": '{"department":"growth"}'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "indexed"
    assert payload["parser"] == "markdown"
    assert payload["chunks_created"] == len(vector_store.records)
    assert payload["chunks_created"] > 0


def test_parser_metadata_is_preserved_in_indexed_chunks(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, _, vector_store, _ = retrieval_context

    response = client.post(
        "/documents/parse-ingest",
        files={
            "file": (
                "commercial_policy.md",
                b"# Commercial Policy\n\nDiscount approval rules apply.",
                "text/markdown",
            )
        },
        data={"metadata": '{"department":"growth"}'},
    )

    assert response.status_code == 200
    assert vector_store.records[0][0].metadata["parser"] == "markdown"
    assert (
        vector_store.records[0][0].metadata["original_filename"]
        == "commercial_policy.md"
    )
    assert vector_store.records[0][0].metadata["department"] == "growth"


def test_malformed_metadata_is_rejected(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, _, _, _ = retrieval_context

    response = client.post(
        "/documents/parse",
        files={
            "file": (
                "commercial_policy.md",
                b"# Commercial Policy\n\nDiscount approval rules apply.",
                "text/markdown",
            )
        },
        data={"metadata": '{"department":"growth"'},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Malformed metadata JSON."


def test_blank_title_override_is_rejected(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, _, _, _ = retrieval_context

    response = client.post(
        "/documents/parse",
        files={
            "file": (
                "commercial_policy.md",
                b"# Commercial Policy\n\nDiscount approval rules apply.",
                "text/markdown",
            )
        },
        data={"title": "   "},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Title override cannot be blank."


def test_upload_over_size_limit_is_rejected() -> None:
    service = DocumentParsingService(max_upload_bytes=10)

    with pytest.raises(ValueError, match="Uploaded file exceeds the maximum"):
        service.parse(
            filename="commercial_policy.md",
            content=b"01234567890",
            content_type="text/markdown",
        )


def test_pdf_parser_behavior_is_clear_when_docling_is_unavailable() -> None:
    service = DocumentParsingService()

    with pytest.raises(
        ValueError,
        match="PDF parsing through Docling is not wired in this environment yet.",
    ):
        service.parse(
            filename="commercial_policy.pdf",
            content=b"%PDF-1.4",
            content_type="application/pdf",
        )


def test_parse_rejects_invalid_utf8_text_upload(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, _, _, _ = retrieval_context

    response = client.post(
        "/documents/parse",
        files={
            "file": (
                "commercial_policy.txt",
                b"\xff\xfe\xfd",
                "text/plain",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Document content must be valid UTF-8 text."


def test_parse_rejects_invalid_utf8_markdown_upload(
    retrieval_context: tuple[
        TestClient,
        UUID,
        InMemoryVectorStore,
        InMemoryRetrievalEventRepository,
    ],
) -> None:
    client, _, _, _ = retrieval_context

    response = client.post(
        "/documents/parse",
        files={
            "file": (
                "commercial_policy.md",
                b"\xff\xfe\xfd",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Document content must be valid UTF-8 text."
