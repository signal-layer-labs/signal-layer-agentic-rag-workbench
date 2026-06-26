from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.business import SalesSummary

NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
OptionalNonBlankText = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, min_length=1),
]
PlanStepStatus = Literal["pending", "completed", "failed", "skipped"]
RunStatus = Literal["created", "running", "completed", "failed"]


class AgentRunRequest(BaseModel):
    business_question: NonBlankText = Field(max_length=10_000)
    retrieval_query: OptionalNonBlankText = None
    sales_region: OptionalNonBlankText = None
    sales_channel: OptionalNonBlankText = None
    customer_segment: OptionalNonBlankText = None
    generate_response: bool = False


class ExecutionPlanStep(BaseModel):
    step: int
    name: str
    status: PlanStepStatus
    details: str | None = None


class AgentTraceSummary(BaseModel):
    retrieval_event_id: UUID | None = None
    tool_call_ids: list[UUID]
    documents_retrieved: int
    customers_returned: int
    sales_summary: SalesSummary


class GeneratedResponse(BaseModel):
    content: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None


class AgentRunResponse(BaseModel):
    run_id: UUID
    status: RunStatus
    business_question: str
    execution_plan: list[ExecutionPlanStep]
    trace: AgentTraceSummary
    summary: str
    generated_response: GeneratedResponse | None = None
