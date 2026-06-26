from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.db.models import AgentRun, Customer, RetrievalEvent, Sale, ToolCall
from app.evals.cases import get_builtin_eval_cases
from app.evals.metrics import evaluate_response, evaluate_retrieval, evaluate_trace
from app.evals.runner import EvalRunner
from app.evals.service import EvalService, get_eval_service
from app.main import app
from app.providers.mock_provider import MockLLMProvider
from app.rag.chunking import TextChunker
from app.rag.embeddings import MockEmbeddingProvider
from app.rag.retrieval import RetrievalService
from app.rag.vector_store import ChunkMetadata, SearchResult, StoredChunk
from app.schemas.agent import AgentRunResponse, AgentTraceSummary, GeneratedResponse
from app.schemas.business import SalesSummary
from app.schemas.evals import EvalCase
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.business_service import BusinessService
from app.services.business_tool_executor import BusinessToolExecutor
from app.services.response_generator import ResponseGenerator
from app.services.run_service import RunService
from scripts import run_evals


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
    def __init__(self) -> None:
        self.runs: dict[UUID, AgentRun] = {}

    def create(self, business_question: str, summary: str) -> AgentRun:
        run = AgentRun(
            id=uuid4(),
            business_question=business_question,
            status="created",
            summary=summary,
        )
        self.runs[run.id] = run
        return run

    def get_by_id(self, run_id: UUID) -> AgentRun | None:
        return self.runs.get(run_id)

    def list_recent(self, limit: int = 20) -> Sequence[AgentRun]:
        return list(self.runs.values())[-limit:]

    def update_status(self, run_id: UUID, status: str) -> AgentRun | None:
        run = self.runs.get(run_id)
        if run is None:
            return None
        run.status = status
        return run

    def update_summary(self, run_id: UUID, summary: str) -> AgentRun | None:
        run = self.runs.get(run_id)
        if run is None:
            return None
        run.summary = summary
        return run


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


class InMemoryToolCallRepository:
    def __init__(self) -> None:
        self.tool_calls: list[ToolCall] = []

    def create(
        self,
        run_id: UUID,
        tool_name: str,
        tool_input: dict[str, object],
        tool_output: dict[str, object],
        status: str,
        latency_ms: int,
    ) -> ToolCall:
        tool_call = ToolCall(
            id=uuid4(),
            run_id=run_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            status=status,
            latency_ms=latency_ms,
        )
        self.tool_calls.append(tool_call)
        return tool_call


class StubBusinessRepository:
    def __init__(self) -> None:
        self.customers = [
            Customer(
                id=uuid4(),
                name="Orchard Trading",
                segment="enterprise",
                region="east",
                status="active",
            ),
            Customer(
                id=uuid4(),
                name="Northstar Retail",
                segment="mid-market",
                region="north",
                status="active",
            ),
        ]
        self.sales = [
            Sale(
                id=uuid4(),
                customer_id=self.customers[0].id,
                product_id=uuid4(),
                amount=Decimal("120.00"),
                quantity=1,
                sold_at=datetime(2026, 1, 5, tzinfo=UTC),
                channel="online",
                region="east",
            ),
            Sale(
                id=uuid4(),
                customer_id=self.customers[0].id,
                product_id=uuid4(),
                amount=Decimal("350.00"),
                quantity=2,
                sold_at=datetime(2026, 1, 9, tzinfo=UTC),
                channel="online",
                region="east",
            ),
        ]

    def search_customers(self, filters) -> Sequence[Customer]:
        return [
            customer
            for customer in self.customers
            if filters.segment is None or customer.segment == filters.segment
        ][: filters.limit]

    def query_sales(self, filters) -> Sequence[Sale]:
        return [
            sale
            for sale in self.sales
            if filters.region is None or sale.region == filters.region
            if filters.channel is None or sale.channel == filters.channel
        ]


@pytest.fixture
def eval_context() -> tuple[EvalRunner, EvalService]:
    retrieval_service = RetrievalService(
        chunker=TextChunker(chunk_size=40, chunk_overlap=5),
        embedding_provider=MockEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
    )
    run_repository = InMemoryAgentRunRepository()
    event_repository = InMemoryRetrievalEventRepository()
    tool_call_repository = InMemoryToolCallRepository()
    orchestrator = AgentOrchestrator(
        run_service=RunService(
            repository=run_repository,
            retrieval_event_repository=event_repository,
        ),
        retrieval_service=retrieval_service,
        business_executor=BusinessToolExecutor(
            service=BusinessService(StubBusinessRepository()),
            run_repository=run_repository,
            tool_call_repository=tool_call_repository,
        ),
        response_generator=ResponseGenerator(MockLLMProvider()),
    )
    runner = EvalRunner(retrieval_service, orchestrator)
    return runner, EvalService(runner)


def test_builtin_eval_cases_load() -> None:
    cases = get_builtin_eval_cases()

    assert len(cases) == 3
    assert [case.id for case in cases] == [
        "discount-approval-policy",
        "online-sales-summary",
        "structured-only-workflow",
    ]
    assert all(case.generate_response for case in cases)


def test_invalid_eval_case_rejected() -> None:
    with pytest.raises(ValidationError):
        EvalCase(
            id="bad-case",
            name="Bad case",
            business_question="Question",
            documents=[],
            retrieval_query="policy lookup",
            expected_keywords=[],
        )


def test_eval_case_with_retrieval_query_requires_expected_source() -> None:
    with pytest.raises(ValidationError):
        EvalCase(
            id="bad-source-case",
            name="Bad source case",
            business_question="Question",
            documents=[],
            retrieval_query="policy lookup",
            expected_keywords=["policy"],
            expected_source=None,
        )


def test_retrieval_metric_pass_and_fail() -> None:
    case = EvalCase(
        id="retrieval-check",
        name="Retrieval check",
        business_question="Find the policy.",
        documents=[],
        retrieval_query="discount approval rules",
        expected_keywords=["discount", "manager review"],
        expected_source="policy.md",
    )

    passing_result = evaluate_retrieval(
        case,
        [
            SearchResult(
                chunk_id="doc-1:0",
                document="Discount approval rules require manager review.",
                metadata={"source": "policy.md", "title": "Policy"},
                distance=0.1,
            )
        ],
    )
    failing_result = evaluate_retrieval(
        case,
        [
            SearchResult(
                chunk_id="doc-2:0",
                document="General onboarding guidance.",
                metadata={"source": "other.md", "title": "Other"},
                distance=0.4,
            )
        ],
    )

    assert passing_result.passed is True
    assert failing_result.passed is False
    assert "discount" in failing_result.missing_keywords


def test_response_metric_pass_and_unsupported_claim_flag() -> None:
    case = EvalCase(
        id="response-check",
        name="Response check",
        business_question="Summarize east region sales.",
        documents=[],
        generate_response=True,
    )
    trace = AgentTraceSummary(
        retrieval_event_id=None,
        tool_call_ids=[uuid4()],
        documents_retrieved=0,
        customers_returned=1,
        sales_summary=SalesSummary(
            total_revenue=Decimal("470.00"),
            total_quantity=3,
            number_of_sales=2,
            unique_customers=1,
            top_region="east",
            top_channel="online",
        ),
    )
    response = AgentRunResponse(
        run_id=uuid4(),
        status="completed",
        business_question=case.business_question,
        execution_plan=[],
        trace=trace,
        summary="done",
        generated_response=GeneratedResponse(
            content=(
                "Deterministic mock response generated from the recorded trace.\n"
                "Business question: Summarize east region sales.\n"
                "Documents retrieved: no (0)\n"
                "Tool calls recorded: 1\n"
                "Sales summary highlights: revenue=470.00, quantity=3, "
                "sales=2, unique_customers=1, top_region=east, "
                "top_channel=online\n"
                "This output is deterministic and local."
            ),
            provider="mock",
            model="mock-trace-generator",
        ),
    )
    mismatched_response = response.model_copy(
        update={
            "generated_response": GeneratedResponse(
                content=response.generated_response.content.replace(
                    "Tool calls recorded: 1",
                    "Tool calls recorded: 9",
                ),
                provider="mock",
                model="mock-trace-generator",
            )
        }
    )

    passing_result = evaluate_response(case, response)
    failing_result = evaluate_response(case, mismatched_response)

    assert passing_result.passed is True
    assert failing_result.passed is False
    assert "tool_call_count_mismatch" in failing_result.unsupported_claim_flags


def test_trace_metric_validates_run_retrieval_and_tool_calls() -> None:
    case = EvalCase(
        id="trace-check",
        name="Trace check",
        business_question="Find the policy.",
        documents=[],
        retrieval_query="discount approval rules",
        expected_keywords=["discount"],
        expected_source="policy.md",
    )
    response = AgentRunResponse(
        run_id=uuid4(),
        status="completed",
        business_question=case.business_question,
        execution_plan=[],
        trace=AgentTraceSummary(
            retrieval_event_id=uuid4(),
            tool_call_ids=[uuid4()],
            documents_retrieved=1,
            customers_returned=1,
            sales_summary=SalesSummary(
                total_revenue=Decimal("470.00"),
                total_quantity=3,
                number_of_sales=2,
                unique_customers=1,
                top_region="east",
                top_channel="online",
            ),
        ),
        summary="done",
        generated_response=None,
    )

    result = evaluate_trace(case, response)

    assert result.run_created is True
    assert result.retrieval_event_created is True
    assert result.tool_calls_created is True
    assert result.passed is True


def test_eval_runner_returns_total_passed_failed(
    eval_context: tuple[EvalRunner, EvalService],
) -> None:
    runner, _ = eval_context

    report = runner.run_cases(get_builtin_eval_cases())

    assert report.total == 3
    assert report.passed == 3
    assert report.failed == 0


def test_eval_runner_adds_eval_metadata_to_ingested_documents(
    eval_context: tuple[EvalRunner, EvalService],
) -> None:
    runner, _ = eval_context
    vector_store = runner.retrieval_service.vector_store
    case = EvalCase(
        id="metadata-check",
        name="Metadata check",
        business_question="Find the policy.",
        documents=[
            {
                "title": "Policy",
                "source": "policy.md",
                "content": "Discount approval rules require manager review.",
                "metadata": {"department": "growth"},
            }
        ],
        retrieval_query="discount approval rules",
        expected_keywords=["discount"],
        expected_source="policy.md",
    )

    runner.run_cases([case])

    first_metadata = vector_store.records[0][0].metadata
    assert first_metadata["department"] == "growth"
    assert first_metadata["eval_case_id"] == "metadata-check"
    assert first_metadata["eval_case_name"] == "Metadata check"
    assert first_metadata["eval_source"] == "built-in"


def test_evals_run_endpoint_returns_structured_report(
    eval_context: tuple[EvalRunner, EvalService],
) -> None:
    _, service = eval_context
    app.dependency_overrides[get_eval_service] = lambda: service
    client = TestClient(app)

    response = client.post("/evals/run")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["failed"] == 0
    assert len(payload["results"]) == 3
    assert {"retrieval", "response", "trace"} <= payload["results"][0].keys()


def test_run_evals_script_main_returns_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubSession:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class StubSessionFactory:
        def __call__(self) -> StubSession:
            return StubSession()

    class StubEvalService:
        def run_builtin_cases(self):
            from app.schemas.evals import EvalRunReport, OverallEvalResult

            return EvalRunReport(
                total=1,
                passed=1,
                failed=0,
                results=[
                    OverallEvalResult(
                        case_id="ok",
                        name="ok",
                        retrieval={
                            "retrieved_count": 1,
                            "expected_source_found": True,
                            "expected_keywords_found": True,
                            "missing_keywords": [],
                            "passed": True,
                        },
                        response={
                            "generated": True,
                            "contains_business_question": True,
                            "contains_sales_summary": True,
                            "unsupported_claim_flags": [],
                            "passed": True,
                        },
                        trace={
                            "run_created": True,
                            "retrieval_event_created": True,
                            "tool_calls_created": True,
                            "passed": True,
                        },
                        passed=True,
                    )
                ],
            )

    monkeypatch.setattr(run_evals, "create_database_tables", lambda: None)
    monkeypatch.setattr(run_evals, "SessionLocal", StubSessionFactory())
    monkeypatch.setattr(run_evals, "get_retrieval_service", lambda: object())
    monkeypatch.setattr(run_evals, "get_llm_provider", lambda: MockLLMProvider())
    monkeypatch.setattr(
        run_evals,
        "build_eval_service",
        lambda session, retrieval_service, response_generator: StubEvalService(),
    )

    assert run_evals.main() == 0
