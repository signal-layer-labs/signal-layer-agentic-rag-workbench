from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.business_repositories import (
    CustomerFilters,
    SalesFilters,
    SqlAlchemyBusinessRepository,
)
from app.db.repositories import (
    SqlAlchemyAgentRunRepository,
    SqlAlchemyToolCallRepository,
)
from app.db.session import get_db_session
from app.schemas.business import (
    CustomerQueryRequest,
    CustomerSummary,
    SaleRecord,
    SalesQueryRequest,
    SalesSummaryRequest,
    ToolExecutionResponse,
)
from app.services.business_service import BusinessService
from app.services.business_tool_executor import BusinessToolExecutor
from app.tools.business_tools import (
    query_customers_tool,
    query_sales_tool,
    summarize_sales_tool,
)

router = APIRouter(prefix="/business", tags=["business"])

def get_business_tool_executor(
    session: Annotated[Session, Depends(get_db_session)],
) -> BusinessToolExecutor:
    return BusinessToolExecutor(
        service=BusinessService(SqlAlchemyBusinessRepository(session)),
        run_repository=SqlAlchemyAgentRunRepository(session),
        tool_call_repository=SqlAlchemyToolCallRepository(session),
    )


ExecutorDependency = Annotated[
    BusinessToolExecutor,
    Depends(get_business_tool_executor),
]


@router.post(
    "/customers/query",
    response_model=ToolExecutionResponse,
    response_model_exclude_none=True,
)
def query_customers(
    request: CustomerQueryRequest,
    executor: ExecutorDependency,
) -> ToolExecutionResponse:
    filters = CustomerFilters(
        segment=request.segment,
        region=request.region,
        status=request.status,
        limit=request.limit,
    )
    results, tool_call_id = executor.execute(
        tool_name="query_customers",
        run_id=request.run_id,
        tool_input=request.model_dump(mode="json", exclude={"run_id"}),
        operation=lambda: query_customers_tool(executor.service, filters),
        serialize=lambda customers: {
            "results": [
                CustomerSummary.model_validate(customer).model_dump(mode="json")
                for customer in customers
            ]
        },
    )
    return ToolExecutionResponse(
        tool_name="query_customers",
        tool_call_id=tool_call_id,
        results=[
            CustomerSummary.model_validate(customer) for customer in results
        ],
    )


@router.post(
    "/sales/query",
    response_model=ToolExecutionResponse,
    response_model_exclude_none=True,
)
def query_sales(
    request: SalesQueryRequest,
    executor: ExecutorDependency,
) -> ToolExecutionResponse:
    filters = _sales_filters(request, limit=request.limit)
    results, tool_call_id = executor.execute(
        tool_name="query_sales",
        run_id=request.run_id,
        tool_input=request.model_dump(mode="json", exclude={"run_id"}),
        operation=lambda: query_sales_tool(executor.service, filters),
        serialize=lambda sales: {
            "results": [
                SaleRecord.model_validate(sale).model_dump(mode="json")
                for sale in sales
            ]
        },
    )
    return ToolExecutionResponse(
        tool_name="query_sales",
        tool_call_id=tool_call_id,
        results=[SaleRecord.model_validate(sale) for sale in results],
    )


@router.post(
    "/sales/summary",
    response_model=ToolExecutionResponse,
    response_model_exclude_none=True,
)
def summarize_sales(
    request: SalesSummaryRequest,
    executor: ExecutorDependency,
) -> ToolExecutionResponse:
    filters = _sales_filters(request, limit=None)
    summary, tool_call_id = executor.execute(
        tool_name="summarize_sales",
        run_id=request.run_id,
        tool_input=request.model_dump(mode="json", exclude={"run_id"}),
        operation=lambda: summarize_sales_tool(executor.service, filters),
        serialize=lambda value: {
            "summary": value.model_dump(mode="json"),
        },
    )
    return ToolExecutionResponse(
        tool_name="summarize_sales",
        tool_call_id=tool_call_id,
        summary=summary,
    )


def _sales_filters(
    request: SalesQueryRequest | SalesSummaryRequest,
    limit: int | None,
) -> SalesFilters:
    return SalesFilters(
        customer_id=getattr(request, "customer_id", None),
        region=request.region,
        channel=request.channel,
        start_date=request.start_date,
        end_date=request.end_date,
        limit=limit,
    )
