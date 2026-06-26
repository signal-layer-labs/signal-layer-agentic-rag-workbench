from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.business_repositories import (
    CustomerFilters,
    SalesFilters,
    SqlAlchemyBusinessRepository,
)
from app.db.repositories import (
    SqlAlchemyAgentRunRepository,
    SqlAlchemyRetrievalEventRepository,
    SqlAlchemyToolCallRepository,
)
from app.db.session import get_db_session
from app.rag.retrieval import RetrievalService, get_retrieval_service
from app.schemas.agent import (
    AgentRunRequest,
    AgentRunResponse,
    AgentTraceSummary,
    ExecutionPlanStep,
    PlanStepStatus,
)
from app.schemas.business import CustomerSummary, SalesSummary
from app.services.business_service import BusinessService
from app.services.business_tool_executor import BusinessToolExecutor
from app.services.run_service import RunService
from app.tools.business_tools import query_customers_tool, summarize_sales_tool

TRACE_SUMMARY = (
    "Deterministic orchestration completed. This run retrieved document "
    "context, queried structured business data, and recorded trace events."
)


class AgentOrchestrator:
    def __init__(
        self,
        run_service: RunService,
        retrieval_service: RetrievalService,
        business_executor: BusinessToolExecutor,
    ) -> None:
        self.run_service = run_service
        self.retrieval_service = retrieval_service
        self.business_executor = business_executor

    def run(self, request: AgentRunRequest) -> AgentRunResponse:
        plan = self._build_plan()
        run = self.run_service.create_run(request.business_question)
        self._mark_completed(plan, "create_run")

        try:
            self.run_service.update_status(run.id, "running")

            retrieval_event_id: UUID | None = None
            documents_retrieved = 0
            if request.retrieval_query is not None:
                results = self.retrieval_service.search(
                    request.retrieval_query,
                    limit=5,
                )
                retrieval_event_id = self.run_service.log_retrieval(
                    run.id,
                    request.retrieval_query,
                    results,
                )
                documents_retrieved = len(results)
                self._mark_completed(plan, "retrieve_documents")
            else:
                self._mark_skipped(
                    plan,
                    "retrieve_documents",
                    "No retrieval_query provided.",
                )

            tool_call_ids: list[UUID] = []
            customers_returned = 0
            if request.customer_segment is not None:
                customers, customer_tool_call_id = self.business_executor.execute(
                    tool_name="query_customers",
                    run_id=run.id,
                    tool_input={"segment": request.customer_segment, "limit": 20},
                    operation=lambda: query_customers_tool(
                        self.business_executor.service,
                        CustomerFilters(
                            segment=request.customer_segment,
                            limit=20,
                        ),
                    ),
                    serialize=lambda customer_rows: {
                        "results": [
                            CustomerSummary.model_validate(customer).model_dump(
                                mode="json"
                            )
                            for customer in customer_rows
                        ]
                    },
                )
                customers_returned = len(customers)
                if customer_tool_call_id is not None:
                    tool_call_ids.append(customer_tool_call_id)
                self._mark_completed(plan, "query_customers")
            else:
                self._mark_skipped(
                    plan,
                    "query_customers",
                    "No customer filters provided.",
                )

            sales_summary, sales_tool_call_id = self.business_executor.execute(
                tool_name="summarize_sales",
                run_id=run.id,
                tool_input={
                    "region": request.sales_region,
                    "channel": request.sales_channel,
                },
                operation=lambda: summarize_sales_tool(
                    self.business_executor.service,
                    SalesFilters(
                        region=request.sales_region,
                        channel=request.sales_channel,
                        limit=None,
                    ),
                ),
                serialize=lambda value: {
                    "summary": value.model_dump(mode="json"),
                },
            )
            if sales_tool_call_id is not None:
                tool_call_ids.append(sales_tool_call_id)
            self._mark_completed(plan, "summarize_sales")

            self.run_service.update_summary(run.id, TRACE_SUMMARY)
            completed_run = self.run_service.update_status(run.id, "completed")
            self._mark_completed(plan, "assemble_trace_summary")

            return AgentRunResponse(
                run_id=run.id,
                status=(
                    completed_run.status
                    if completed_run is not None
                    else "completed"
                ),
                business_question=request.business_question,
                execution_plan=plan,
                trace=AgentTraceSummary(
                    retrieval_event_id=retrieval_event_id,
                    tool_call_ids=tool_call_ids,
                    documents_retrieved=documents_retrieved,
                    customers_returned=customers_returned,
                    sales_summary=SalesSummary.model_validate(sales_summary),
                ),
                summary=TRACE_SUMMARY,
            )
        except Exception:
            self.run_service.update_status(run.id, "failed")
            self._mark_failed(plan)
            raise

    def _build_plan(self) -> list[ExecutionPlanStep]:
        return [
            ExecutionPlanStep(step=1, name="create_run", status="pending"),
            ExecutionPlanStep(step=2, name="retrieve_documents", status="pending"),
            ExecutionPlanStep(step=3, name="query_customers", status="pending"),
            ExecutionPlanStep(step=4, name="summarize_sales", status="pending"),
            ExecutionPlanStep(
                step=5,
                name="assemble_trace_summary",
                status="pending",
            ),
        ]

    def _mark_completed(
        self,
        plan: list[ExecutionPlanStep],
        name: str,
    ) -> None:
        self._update_step(plan, name, status="completed")

    def _mark_skipped(
        self,
        plan: list[ExecutionPlanStep],
        name: str,
        details: str,
    ) -> None:
        self._update_step(plan, name, status="skipped", details=details)

    def _update_step(
        self,
        plan: list[ExecutionPlanStep],
        name: str,
        status: PlanStepStatus,
        details: str | None = None,
    ) -> None:
        for step in plan:
            if step.name == name:
                step.status = status
                step.details = details
                return

    def _mark_failed(self, plan: list[ExecutionPlanStep]) -> None:
        for step in plan:
            if step.status == "pending":
                step.status = "failed"
                return


def get_agent_orchestrator(
    session: Annotated[Session, Depends(get_db_session)],
    retrieval_service: Annotated[
        RetrievalService,
        Depends(get_retrieval_service),
    ],
) -> AgentOrchestrator:
    run_service = RunService(
        repository=SqlAlchemyAgentRunRepository(session),
        retrieval_event_repository=SqlAlchemyRetrievalEventRepository(session),
    )
    business_executor = BusinessToolExecutor(
        service=BusinessService(SqlAlchemyBusinessRepository(session)),
        run_repository=SqlAlchemyAgentRunRepository(session),
        tool_call_repository=SqlAlchemyToolCallRepository(session),
    )
    return AgentOrchestrator(
        run_service=run_service,
        retrieval_service=retrieval_service,
        business_executor=business_executor,
    )
