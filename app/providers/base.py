from typing import Protocol

from pydantic import BaseModel

from app.schemas.agent import AgentTraceSummary, ExecutionPlanStep


class LLMGenerationRequest(BaseModel):
    business_question: str
    trace_summary: str
    execution_plan: list[ExecutionPlanStep]
    retrieval_context: dict[str, object]
    business_data_summary: AgentTraceSummary
    system_instruction: str


class LLMGenerationResponse(BaseModel):
    content: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None


class LLMProvider(Protocol):
    def generate(
        self,
        request: LLMGenerationRequest,
    ) -> LLMGenerationResponse: ...
