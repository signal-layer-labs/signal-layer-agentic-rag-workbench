from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import AgentRun, Customer, RetrievalEvent, Sale, ToolCall
from app.main import app
from app.providers.mock_provider import MockLLMProvider
from app.rag.retrieval import get_retrieval_service
from app.rag.vector_store import SearchResult
from app.schemas.business import SalesSummary
from app.services.agent_orchestrator import (
    AgentOrchestrator,
    get_agent_orchestrator,
)
from app.services.business_service import BusinessService
from app.services.business_tool_executor import BusinessToolExecutor
from app.services.response_generator import ResponseGenerator
from app.services.run_service import RunService


class InMemoryAgentRunRepository:
    def __init__(self) -> None:
        self.runs: dict[UUID, AgentRun] = {}
        self.status_history: dict[UUID, list[str]] = {}

    def create(self, business_question: str, summary: str) -> AgentRun:
        run = AgentRun(
            id=uuid4(),
            business_question=business_question,
            status="created",
            summary=summary,
        )
        self.runs[run.id] = run
        self.status_history[run.id] = ["created"]
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
        self.status_history.setdefault(run_id, []).append(status)
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


class StubRetrievalService:
    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self.results = results or []

    def search(self, query: str, limit: int) -> list[SearchResult]:
        return self.results[:limit]


class StubBusinessRepository:
    def __init__(self) -> None:
        self.customers = [
            Customer(
                id=uuid4(),
                name="Acme Growth",
                segment="enterprise",
                region="east",
                status="active",
            ),
            Customer(
                id=uuid4(),
                name="Summit Retail",
                segment="mid-market",
                region="west",
                status="active",
            ),
        ]
        self.sales = [
            Sale(
                id=uuid4(),
                customer_id=self.customers[0].id,
                product_id=uuid4(),
                amount=Decimal("100.00"),
                quantity=2,
                sold_at=datetime(2025, 1, 15, tzinfo=UTC),
                channel="online",
                region="east",
            ),
            Sale(
                id=uuid4(),
                customer_id=self.customers[0].id,
                product_id=uuid4(),
                amount=Decimal("250.00"),
                quantity=3,
                sold_at=datetime(2025, 1, 18, tzinfo=UTC),
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


class FailingBusinessService(BusinessService):
    def summarize_sales(self, filters) -> SalesSummary:
        raise RuntimeError("sales service unavailable")


@pytest.fixture
def agent_context() -> tuple[
    TestClient,
    InMemoryAgentRunRepository,
    InMemoryRetrievalEventRepository,
    InMemoryToolCallRepository,
]:
    run_repository = InMemoryAgentRunRepository()
    event_repository = InMemoryRetrievalEventRepository()
    tool_call_repository = InMemoryToolCallRepository()
    retrieval_service = StubRetrievalService(
        [
            SearchResult(
                chunk_id="doc-1:0",
                document="Discount approval rules require manager review.",
                metadata={"title": "Commercial Policy"},
                distance=0.12,
            )
        ]
    )
    business_service = BusinessService(StubBusinessRepository())

    orchestrator = AgentOrchestrator(
        run_service=RunService(
            repository=run_repository,
            retrieval_event_repository=event_repository,
        ),
        retrieval_service=retrieval_service,
        business_executor=BusinessToolExecutor(
            service=business_service,
            run_repository=run_repository,
            tool_call_repository=tool_call_repository,
        ),
        response_generator=ResponseGenerator(MockLLMProvider()),
    )

    app.dependency_overrides[get_agent_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval_service
    yield TestClient(app), run_repository, event_repository, tool_call_repository
    app.dependency_overrides.clear()


def test_agent_run_returns_completed_status(
    agent_context: tuple[
        TestClient,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, _ = agent_context

    response = client.post(
        "/agent/run",
        json={"business_question": "Analyze online sales performance."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["execution_plan"][0]["name"] == "create_run"
    assert payload["execution_plan"][0]["status"] == "completed"
    assert payload["trace"]["sales_summary"]["total_revenue"] == "350.00"


def test_agent_run_with_retrieval_creates_event(
    agent_context: tuple[
        TestClient,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, event_repository, _ = agent_context

    response = client.post(
        "/agent/run",
        json={
            "business_question": "Find policy context for sales performance.",
            "retrieval_query": "discount approval rules",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(event_repository.events) == 1
    assert payload["trace"]["retrieval_event_id"] == str(event_repository.events[0].id)
    assert payload["trace"]["documents_retrieved"] == 1
    assert payload["execution_plan"][1]["status"] == "completed"


def test_agent_run_with_business_filters_logs_tool_calls(
    agent_context: tuple[
        TestClient,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, tool_call_repository = agent_context

    response = client.post(
        "/agent/run",
        json={
            "business_question": "Review enterprise online sales.",
            "customer_segment": "enterprise",
            "sales_region": "east",
            "sales_channel": "online",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [call.tool_name for call in tool_call_repository.tool_calls] == [
        "query_customers",
        "summarize_sales",
    ]
    assert len(payload["trace"]["tool_call_ids"]) == 2
    assert payload["trace"]["customers_returned"] == 1
    assert payload["execution_plan"][2]["status"] == "completed"


def test_agent_run_without_retrieval_skips_that_step(
    agent_context: tuple[
        TestClient,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, event_repository, _ = agent_context

    response = client.post(
        "/agent/run",
        json={"business_question": "Summarize current sales."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert event_repository.events == []
    assert payload["trace"]["retrieval_event_id"] is None
    assert payload["execution_plan"][1]["status"] == "skipped"


def test_agent_run_sets_completed_status_after_success(
    agent_context: tuple[
        TestClient,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, run_repository, _, _ = agent_context

    response = client.post(
        "/agent/run",
        json={"business_question": "Track run lifecycle."},
    )

    assert response.status_code == 200
    run_id = UUID(response.json()["run_id"])
    assert run_repository.status_history[run_id] == [
        "created",
        "running",
        "completed",
    ]
    assert run_repository.get_by_id(run_id).summary is not None


def test_agent_run_failure_sets_failed_status() -> None:
    run_repository = InMemoryAgentRunRepository()
    event_repository = InMemoryRetrievalEventRepository()
    tool_call_repository = InMemoryToolCallRepository()
    retrieval_service = StubRetrievalService()
    orchestrator = AgentOrchestrator(
        run_service=RunService(
            repository=run_repository,
            retrieval_event_repository=event_repository,
        ),
        retrieval_service=retrieval_service,
        business_executor=BusinessToolExecutor(
            service=FailingBusinessService(StubBusinessRepository()),
            run_repository=run_repository,
            tool_call_repository=tool_call_repository,
        ),
        response_generator=ResponseGenerator(MockLLMProvider()),
    )

    app.dependency_overrides[get_agent_orchestrator] = lambda: orchestrator
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/agent/run",
        json={"business_question": "Force a deterministic failure."},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 500
    run = next(iter(run_repository.runs.values()))
    assert run_repository.status_history[run.id] == [
        "created",
        "running",
        "failed",
    ]


def test_agent_run_response_is_deterministic_and_local(
    agent_context: tuple[
        TestClient,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, _ = agent_context

    response = client.post(
        "/agent/run",
        json={
            "business_question": (
                "Analyze online sales performance and find relevant "
                "commercial policy context."
            ),
            "retrieval_query": "discount approval rules",
            "sales_region": "east",
            "sales_channel": "online",
            "customer_segment": "enterprise",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == (
        "Deterministic orchestration completed. This run retrieved "
        "document context, queried structured business data, and "
        "recorded trace events."
    )
    assert payload["trace"]["sales_summary"] == {
        "total_revenue": "350.00",
        "total_quantity": 5,
        "number_of_sales": 2,
        "unique_customers": 1,
        "top_region": "east",
        "top_channel": "online",
    }


def test_agent_run_does_not_generate_response_by_default(
    agent_context: tuple[
        TestClient,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, _ = agent_context

    response = client.post(
        "/agent/run",
        json={"business_question": "Summarize current sales."},
    )

    assert response.status_code == 200
    assert response.json()["generated_response"] is None


def test_agent_run_can_generate_response_from_trace(
    agent_context: tuple[
        TestClient,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, tool_call_repository = agent_context

    response = client.post(
        "/agent/run",
        json={
            "business_question": "Analyze online sales performance.",
            "retrieval_query": "discount approval rules",
            "sales_region": "east",
            "sales_channel": "online",
            "customer_segment": "enterprise",
            "generate_response": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generated_response"]["provider"] == "mock"
    assert payload["generated_response"]["model"] == "mock-trace-generator"
    assert payload["generated_response"]["latency_ms"] == 0
    assert "Documents retrieved: yes (1)" in payload["generated_response"]["content"]
    assert "Tool calls recorded: 2" in payload["generated_response"]["content"]
    assert len(tool_call_repository.tool_calls) == 2


def test_generated_response_uses_trace_values(
    agent_context: tuple[
        TestClient,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, _ = agent_context

    response = client.post(
        "/agent/run",
        json={
            "business_question": "Analyze online sales performance.",
            "sales_region": "east",
            "sales_channel": "online",
            "generate_response": True,
        },
    )

    assert response.status_code == 200
    content = response.json()["generated_response"]["content"]
    assert "Business question: Analyze online sales performance." in content
    assert "Documents retrieved: no (0)" in content
    assert "revenue=350.00" in content
