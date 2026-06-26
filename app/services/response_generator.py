from typing import Annotated

from fastapi import Depends

from app.core.errors import AppError, orchestration_failed
from app.core.timing import measure_time
from app.providers.base import (
    LLMGenerationRequest,
    LLMGenerationResponse,
    LLMProvider,
)
from app.providers.factory import get_llm_provider
from app.schemas.agent import AgentTraceSummary, ExecutionPlanStep

SYSTEM_INSTRUCTION = (
    "Transform the provided deterministic trace into a compact human-readable "
    "response. Do not add claims that are not present in the trace."
)


class ResponseGenerator:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def generate(
        self,
        business_question: str,
        execution_plan: list[ExecutionPlanStep],
        trace: AgentTraceSummary,
        trace_summary: str,
    ) -> LLMGenerationResponse:
        request = LLMGenerationRequest(
            business_question=business_question,
            trace_summary=trace_summary,
            execution_plan=execution_plan,
            retrieval_context={
                "retrieval_event_id": (
                    str(trace.retrieval_event_id)
                    if trace.retrieval_event_id is not None
                    else None
                ),
                "documents_retrieved": trace.documents_retrieved,
            },
            business_data_summary=trace,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        try:
            with measure_time() as timer:
                response = self.provider.generate(request)
        except AppError:
            raise
        except Exception as error:
            raise orchestration_failed(
                "Response generation failed.",
                details={"provider": type(self.provider).__name__},
            ) from error
        if response.latency_ms is None:
            return response.model_copy(update={"latency_ms": timer.elapsed_ms})
        return response


def get_response_generator(
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> ResponseGenerator:
    return ResponseGenerator(provider)
