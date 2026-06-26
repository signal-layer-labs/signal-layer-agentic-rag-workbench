from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.agno_agent import AgnoAgentRunner, get_agno_agent_runner
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import AgentRun, Customer, RetrievalEvent, Sale, ToolCall
from app.main import app
from app.providers.mock_provider import MockLLMProvider
from app.rag.retrieval import get_retrieval_service
from app.rag.vector_store import SearchResult
from app.services.agent_orchestrator import AgentOrchestrator, get_agent_orchestrator
from app.services.business_service import BusinessService
from app.services.business_tool_executor import BusinessToolExecutor
from app.services.response_generator import ResponseGenerator
from app.services.run_service import RunService


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
        if run is not None:
            run.status = status
        return run

    def update_summary(self, run_id: UUID, summary: str) -> AgentRun | None:
        run = self.runs.get(run_id)
        if run is not None:
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

    def search(
        self,
        query: str,
        limit: int,
        where: dict[str, object] | None = None,
    ) -> list[SearchResult]:
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
            if (filters.segment is None or customer.segment == filters.segment)
            and (filters.region is None or customer.region == filters.region)
            and (filters.status is None or customer.status == filters.status)
        ][: filters.limit]

    def query_sales(self, filters) -> Sequence[Sale]:
        return [
            sale
            for sale in self.sales
            if filters.region is None or sale.region == filters.region
            if filters.channel is None or sale.channel == filters.channel
        ]


@pytest.fixture
def agno_context() -> tuple[
    TestClient,
    AgnoAgentRunner,
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
                metadata={"source": "commercial_policy.md", "title": "Policy"},
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
    runner = AgnoAgentRunner(
        orchestrator=orchestrator,
        retrieval_service=retrieval_service,  # type: ignore[arg-type]
        business_service=business_service,
    )
    app.dependency_overrides[get_agno_agent_runner] = lambda: runner
    app.dependency_overrides[get_agent_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval_service
    yield (
        TestClient(app),
        runner,
        run_repository,
        event_repository,
        tool_call_repository,
    )
    app.dependency_overrides.clear()


def test_post_agno_run_returns_mode_agno(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, _, _ = agno_context

    response = client.post(
        "/agent/agno/run",
        json={"business_question": "Analyze online sales performance."},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "agno"


def test_post_agno_run_returns_run_id_completed_status_and_trace(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, _, _ = agno_context

    response = client.post(
        "/agent/agno/run",
        json={
            "business_question": "Find policy context for sales performance.",
            "retrieval_query": "discount approval rules",
            "sales_region": "east",
            "sales_channel": "online",
            "customer_segment": "enterprise",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "completed"
    assert payload["run_id"]
    assert payload["trace"]["documents_retrieved"] == 1
    assert payload["allowed_tools"] == [
        "retrieve_documents",
        "query_customers",
        "summarize_sales",
    ]


def test_agno_runner_uses_allowlisted_tools_only(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    _, runner, _, _, _ = agno_context

    descriptors = runner.get_tool_descriptors()

    assert [descriptor.name for descriptor in descriptors] == [
        "retrieve_documents",
        "query_customers",
        "summarize_sales",
    ]


def test_unknown_agno_tool_is_rejected(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    _, runner, _, _, _ = agno_context

    with pytest.raises(AppError, match="Unknown Agno tool"):
        runner.invoke_tool("drop_database")


def test_agno_tool_docstrings_exist(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    _, runner, _, _, _ = agno_context

    descriptors = runner.get_tool_descriptors()

    assert all(descriptor.description for descriptor in descriptors)


def test_fastapi_app_starts_without_agno_dependency_or_real_provider_credentials(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, _, _ = agno_context

    response = client.get("/health")

    assert response.status_code == 200


def test_deterministic_agent_run_remains_unaffected_by_agno_adapter(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, _, _ = agno_context

    response = client.post(
        "/agent/run",
        json={"business_question": "Analyze online sales performance."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_retrieve_documents_tool_respects_max_retrieval_results(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, runner, _, _, _ = agno_context
    monkeypatch.setenv("MAX_RETRIEVAL_RESULTS", "10")
    get_settings.cache_clear()

    with pytest.raises(AppError, match="configured maximum"):
        runner.invoke_tool(
            "retrieve_documents",
            query="discount approval rules",
            limit=11,
        )


def test_query_customers_tool_rejects_raw_sql_style_input(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    _, runner, _, _, _ = agno_context

    with pytest.raises(AppError, match="Raw SQL-style customer filters"):
        runner.invoke_tool("query_customers", segment="select * from customers")


def test_run_traceable_workflow_tool_creates_run_and_tool_calls(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    _, runner, run_repository, event_repository, tool_call_repository = agno_context

    response = runner.invoke_tool(
        "run_traceable_workflow",
        business_question="Analyze enterprise online sales.",
        retrieval_query="discount approval rules",
        sales_region="east",
        sales_channel="online",
        customer_segment="enterprise",
        generate_response=True,
    )

    assert response.status == "completed"
    assert run_repository.runs
    assert len(event_repository.events) == 1
    assert len(tool_call_repository.tool_calls) == 2


def test_agno_run_does_not_require_real_external_provider_calls(
    agno_context: tuple[
        TestClient,
        AgnoAgentRunner,
        InMemoryAgentRunRepository,
        InMemoryRetrievalEventRepository,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _, _, _ = agno_context

    response = client.post(
        "/agent/agno/run",
        json={
            "business_question": "Generate a trace response.",
            "generate_response": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["generated_response"]["provider"] == "mock"
