from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.db.models import AgentRun, Customer, RetrievalEvent, Sale, ToolCall
from app.mcp.tools import query_customers, run_traceable_workflow, summarize_sales
from app.providers.mock_provider import MockLLMProvider
from app.rag.vector_store import SearchResult
from app.services.agent_orchestrator import AgentOrchestrator
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
            if filters.start_date is None or sale.sold_at >= filters.start_date
            if filters.end_date is None or sale.sold_at <= filters.end_date
        ]


@pytest.fixture
def business_service() -> BusinessService:
    return BusinessService(StubBusinessRepository())


@pytest.fixture
def orchestrator() -> AgentOrchestrator:
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
    return AgentOrchestrator(
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


def test_mcp_query_customers_wrapper_returns_expected_customers(
    business_service: BusinessService,
) -> None:
    results = query_customers(
        {"segment": "enterprise", "region": "east", "limit": 20},
        service=business_service,
    )

    assert len(results) == 1
    assert results[0].name == "Acme Growth"


def test_mcp_summarize_sales_wrapper_returns_correct_aggregate_values(
    business_service: BusinessService,
) -> None:
    summary = summarize_sales(
        {"region": "east", "channel": "online"},
        service=business_service,
    )

    assert summary.total_revenue == Decimal("350.00")
    assert summary.total_quantity == 5
    assert summary.number_of_sales == 2
    assert summary.unique_customers == 1


def test_mcp_run_traceable_workflow_creates_completed_run(
    orchestrator: AgentOrchestrator,
) -> None:
    response = run_traceable_workflow(
        {
            "business_question": "Analyze enterprise online sales.",
            "retrieval_query": "discount approval rules",
            "sales_region": "east",
            "sales_channel": "online",
            "customer_segment": "enterprise",
        },
        orchestrator=orchestrator,
    )

    assert response.status == "completed"
    assert response.trace.documents_retrieved == 1


def test_mcp_run_traceable_workflow_can_generate_response(
    orchestrator: AgentOrchestrator,
) -> None:
    response = run_traceable_workflow(
        {
            "business_question": "Analyze enterprise online sales.",
            "generate_response": True,
            "sales_region": "east",
            "sales_channel": "online",
        },
        orchestrator=orchestrator,
    )

    assert response.generated_response is not None
    assert response.generated_response.provider == "mock"


def test_mcp_invalid_limit_is_rejected() -> None:
    with pytest.raises(ValidationError):
        query_customers(
            {"limit": 101},
            service=BusinessService(StubBusinessRepository()),
        )


def test_mcp_blank_business_question_is_rejected(
    orchestrator: AgentOrchestrator,
) -> None:
    with pytest.raises(ValidationError, match="business_question cannot be blank"):
        run_traceable_workflow(
            {"business_question": "   "},
            orchestrator=orchestrator,
        )


def test_mcp_invalid_date_range_is_rejected(
    business_service: BusinessService,
) -> None:
    with pytest.raises(ValidationError, match="end_date cannot be earlier"):
        summarize_sales(
            {
                "start_date": "2025-01-31T00:00:00Z",
                "end_date": "2025-01-01T00:00:00Z",
            },
            service=business_service,
        )


def test_mcp_wrappers_do_not_accept_raw_sql(
    business_service: BusinessService,
) -> None:
    with pytest.raises(ValidationError):
        query_customers(
            {"sql": "select * from customers"},
            service=business_service,
        )
