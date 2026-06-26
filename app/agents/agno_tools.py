from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.budgets import ensure_limit_within_budget
from app.core.config import get_settings
from app.core.errors import validation_error
from app.db.business_repositories import CustomerFilters, SalesFilters
from app.rag.retrieval import RetrievalService
from app.rag.vector_store import SearchResult
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.schemas.business import CustomerSummary, SalesSummary
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.business_service import BusinessService

AnnotatedQuery = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class RetrieveDocumentsInput(BaseModel):
    query: AnnotatedQuery
    limit: int = Field(default=5, ge=1, le=100)


class QueryCustomersInput(BaseModel):
    segment: str | None = None
    region: str | None = None
    status: str | None = None
    limit: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_sql_style_input(self) -> "QueryCustomersInput":
        for value in (self.segment, self.region, self.status):
            if value and _looks_like_sql(value):
                raise validation_error(
                    "Raw SQL-style customer filters are not allowed."
                )
        return self


class SummarizeSalesInput(BaseModel):
    region: str | None = None
    channel: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class RunTraceableWorkflowInput(BaseModel):
    business_question: AnnotatedQuery
    retrieval_query: str | None = None
    sales_region: str | None = None
    sales_channel: str | None = None
    customer_segment: str | None = None
    generate_response: bool = True


def _looks_like_sql(value: str) -> bool:
    lowered = value.lower()
    return "select " in lowered or " from " in lowered or ";" in lowered


def retrieve_documents_tool(
    retrieval_service: RetrievalService,
    *,
    query: str,
    limit: int = 5,
) -> list[SearchResult]:
    """Retrieve matching document chunks for a text query.

    Use this tool when document context is needed before answering. It accepts
    a text query and an optional limit, uses approved service-layer retrieval,
    does not accept raw SQL, and does not execute shell commands.
    """
    ensure_limit_within_budget(
        limit=limit,
        max_limit=get_settings().max_retrieval_results,
        resource_name="retrieval_results",
    )
    return retrieval_service.search(query, limit=limit)


def query_customers_tool(
    business_service: BusinessService,
    *,
    segment: str | None = None,
    region: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[CustomerSummary]:
    """Query allowlisted customer filters through the approved business service.

    Use this tool for structured customer lookups by segment, region, status,
    and limit. It uses approved service-layer behavior, does not accept raw
    SQL, and does not execute shell commands.
    """
    request = QueryCustomersInput(
        segment=segment,
        region=region,
        status=status,
        limit=limit,
    )
    customers = business_service.query_customers(
        CustomerFilters(
            segment=request.segment,
            region=request.region,
            status=request.status,
            limit=request.limit,
        )
    )
    return [CustomerSummary.model_validate(customer) for customer in customers]


def summarize_sales_tool(
    business_service: BusinessService,
    *,
    region: str | None = None,
    channel: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> SalesSummary:
    """Return a deterministic sales aggregate from approved service filters.

    Use this tool for structured sales summaries by region, channel, and
    optional date range. It uses approved service-layer behavior, does not
    accept raw SQL, and does not execute shell commands.
    """
    request = SummarizeSalesInput(
        region=region,
        channel=channel,
        start_date=start_date,
        end_date=end_date,
    )
    return business_service.summarize_sales(
        SalesFilters(
            region=request.region,
            channel=request.channel,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=None,
        )
    )


def run_traceable_workflow_tool(
    orchestrator: AgentOrchestrator,
    *,
    business_question: str,
    retrieval_query: str | None = None,
    sales_region: str | None = None,
    sales_channel: str | None = None,
    customer_segment: str | None = None,
    generate_response: bool = True,
) -> AgentRunResponse:
    """Run the trace-first workflow through the approved orchestrator.

    Use this tool when a full traceable workflow run is needed. It creates an
    agent run, records retrieval events and tool calls, uses approved
    service-layer behavior, does not accept raw SQL, and does not execute shell
    commands.
    """
    request = RunTraceableWorkflowInput(
        business_question=business_question,
        retrieval_query=retrieval_query,
        sales_region=sales_region,
        sales_channel=sales_channel,
        customer_segment=customer_segment,
        generate_response=generate_response,
    )
    return orchestrator.run(
        AgentRunRequest(
            business_question=request.business_question,
            retrieval_query=request.retrieval_query,
            sales_region=request.sales_region,
            sales_channel=request.sales_channel,
            customer_segment=request.customer_segment,
            generate_response=request.generate_response,
        )
    )
