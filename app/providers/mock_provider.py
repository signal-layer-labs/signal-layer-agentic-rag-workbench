from app.providers.base import LLMGenerationRequest, LLMGenerationResponse


class MockLLMProvider:
    def __init__(self, model: str = "mock-trace-generator") -> None:
        self.model = model

    def generate(
        self,
        request: LLMGenerationRequest,
    ) -> LLMGenerationResponse:
        trace = request.business_data_summary
        sales_summary = trace.sales_summary
        documents_retrieved = trace.documents_retrieved
        tool_call_count = len(trace.tool_call_ids)
        content = (
            "Deterministic mock response generated from the recorded trace.\n"
            f"Business question: {request.business_question}\n"
            f"Documents retrieved: {'yes' if documents_retrieved > 0 else 'no'} "
            f"({documents_retrieved})\n"
            f"Tool calls recorded: {tool_call_count}\n"
            "Sales summary highlights: "
            f"revenue={sales_summary.total_revenue}, "
            f"quantity={sales_summary.total_quantity}, "
            f"sales={sales_summary.number_of_sales}, "
            f"unique_customers={sales_summary.unique_customers}, "
            f"top_region={sales_summary.top_region}, "
            f"top_channel={sales_summary.top_channel}\n"
            "This output is deterministic and local."
        )
        return LLMGenerationResponse(
            content=content,
            provider="mock",
            model=self.model,
            latency_ms=0,
        )
