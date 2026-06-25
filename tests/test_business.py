from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes_business import (
    BusinessToolExecutor,
    get_business_tool_executor,
)
from app.db.business_repositories import CustomerFilters, SalesFilters
from app.db.models import AgentRun, Customer, Product, Sale, ToolCall
from app.main import app
from app.services.business_service import BusinessService
from scripts.seed_business_data import build_business_seed_data


class InMemoryBusinessRepository:
    def __init__(
        self,
        customers: list[Customer],
        products: list[Product],
        sales: list[Sale],
    ) -> None:
        self.customers = customers
        self.products = products
        self.sales = sales

    def list_customers(self, limit: int = 20) -> Sequence[Customer]:
        return sorted(self.customers, key=lambda customer: customer.name)[:limit]

    def get_customer_by_id(self, customer_id: UUID) -> Customer | None:
        return next(
            (
                customer
                for customer in self.customers
                if customer.id == customer_id
            ),
            None,
        )

    def search_customers(
        self,
        filters: CustomerFilters,
    ) -> Sequence[Customer]:
        customers = [
            customer
            for customer in self.customers
            if (
                filters.segment is None
                or customer.segment == filters.segment
            )
            and (filters.region is None or customer.region == filters.region)
            and (filters.status is None or customer.status == filters.status)
        ]
        return sorted(customers, key=lambda customer: customer.name)[
            : filters.limit
        ]

    def list_products(self) -> Sequence[Product]:
        return sorted(self.products, key=lambda product: product.name)

    def query_sales(self, filters: SalesFilters) -> Sequence[Sale]:
        sales = [
            sale
            for sale in self.sales
            if (
                filters.customer_id is None
                or sale.customer_id == filters.customer_id
            )
            and (filters.region is None or sale.region == filters.region)
            and (filters.channel is None or sale.channel == filters.channel)
            and (
                filters.start_date is None
                or sale.sold_at >= filters.start_date
            )
            and (filters.end_date is None or sale.sold_at <= filters.end_date)
        ]
        sales.sort(key=lambda sale: (sale.sold_at, sale.id), reverse=True)
        if filters.limit is None:
            return sales
        return sales[: filters.limit]


class InMemoryRunRepository:
    def __init__(self, run: AgentRun) -> None:
        self.run = run

    def create(self, business_question: str, summary: str) -> AgentRun:
        return self.run

    def get_by_id(self, run_id: UUID) -> AgentRun | None:
        return self.run if run_id == self.run.id else None

    def list_recent(self, limit: int = 20) -> Sequence[AgentRun]:
        return [self.run][:limit]


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


@pytest.fixture
def business_context() -> tuple[
    TestClient,
    AgentRun,
    InMemoryToolCallRepository,
]:
    data = build_business_seed_data()
    run = AgentRun(
        id=uuid4(),
        business_question="Review business performance.",
        status="created",
        summary="Mock run.",
    )
    tool_call_repository = InMemoryToolCallRepository()
    executor = BusinessToolExecutor(
        service=BusinessService(
            InMemoryBusinessRepository(
                data.customers,
                data.products,
                data.sales,
            )
        ),
        run_repository=InMemoryRunRepository(run),
        tool_call_repository=tool_call_repository,
    )
    app.dependency_overrides[get_business_tool_executor] = lambda: executor
    yield TestClient(app), run, tool_call_repository
    app.dependency_overrides.clear()


def test_business_seed_data_has_expected_fake_records() -> None:
    data = build_business_seed_data()

    assert len(data.customers) == 6
    assert len(data.products) == 5
    assert len(data.sales) == 24
    assert len({customer.id for customer in data.customers}) == 6
    assert len({sale.id for sale in data.sales}) == 24


def test_customer_query_filters_work(
    business_context: tuple[
        TestClient,
        AgentRun,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, tool_calls = business_context

    response = client.post(
        "/business/customers/query",
        json={"segment": "enterprise", "region": "east"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool_name"] == "query_customers"
    assert "tool_call_id" not in payload
    assert [result["name"] for result in payload["results"]] == [
        "Orchard Trading"
    ]
    assert tool_calls.tool_calls == []


def test_sales_query_filters_work(
    business_context: tuple[
        TestClient,
        AgentRun,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _ = business_context

    response = client.post(
        "/business/sales/query",
        json={
            "region": "north",
            "channel": "direct",
            "start_date": "2026-01-01T00:00:00Z",
            "end_date": "2026-12-31T23:59:59Z",
            "limit": 100,
        },
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results
    assert all(result["region"] == "north" for result in results)
    assert all(result["channel"] == "direct" for result in results)


def test_sales_summary_returns_correct_totals(
    business_context: tuple[
        TestClient,
        AgentRun,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, _ = business_context

    response = client.post(
        "/business/sales/summary",
        json={"region": "east"},
    )

    assert response.status_code == 200
    summary = response.json()["summary"]
    data = build_business_seed_data()
    east_sales = [sale for sale in data.sales if sale.region == "east"]
    assert Decimal(summary["total_revenue"]) == sum(
        (sale.amount for sale in east_sales),
        start=Decimal("0.00"),
    )
    assert summary["total_quantity"] == sum(
        sale.quantity for sale in east_sales
    )
    assert summary["number_of_sales"] == len(east_sales)
    assert summary["unique_customers"] == len(
        {sale.customer_id for sale in east_sales}
    )
    assert summary["top_region"] == "east"


def test_tool_call_is_logged_when_run_id_is_provided(
    business_context: tuple[
        TestClient,
        AgentRun,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, run, repository = business_context

    response = client.post(
        "/business/sales/summary",
        json={"run_id": str(run.id), "channel": "online"},
    )

    assert response.status_code == 200
    assert len(repository.tool_calls) == 1
    tool_call = repository.tool_calls[0]
    assert response.json()["tool_call_id"] == str(tool_call.id)
    assert tool_call.run_id == run.id
    assert tool_call.tool_name == "summarize_sales"
    assert tool_call.status == "completed"
    assert tool_call.latency_ms is not None
    assert tool_call.tool_input == {
        "region": None,
        "channel": "online",
        "start_date": None,
        "end_date": None,
    }
    assert tool_call.tool_output is not None
    assert "summary" in tool_call.tool_output


def test_invalid_date_range_returns_validation_error(
    business_context: tuple[
        TestClient,
        AgentRun,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, repository = business_context

    response = client.post(
        "/business/sales/query",
        json={
            "start_date": datetime.now(UTC).isoformat(),
            "end_date": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 422
    assert repository.tool_calls == []


def test_unknown_run_id_returns_404(
    business_context: tuple[
        TestClient,
        AgentRun,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, repository = business_context

    response = client.post(
        "/business/customers/query",
        json={"run_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert repository.tool_calls == []


def test_whitespace_filter_and_invalid_limit_are_rejected(
    business_context: tuple[
        TestClient,
        AgentRun,
        InMemoryToolCallRepository,
    ],
) -> None:
    client, _, repository = business_context

    blank_filter = client.post(
        "/business/customers/query",
        json={"segment": "   "},
    )
    invalid_limit = client.post(
        "/business/sales/query",
        json={"limit": 101},
    )

    assert blank_filter.status_code == 422
    assert invalid_limit.status_code == 422
    assert repository.tool_calls == []
