import pytest

from app.providers.base import LLMGenerationRequest
from app.providers.factory import create_llm_provider
from app.providers.mock_provider import MockLLMProvider
from app.schemas.agent import AgentTraceSummary, ExecutionPlanStep
from app.schemas.business import SalesSummary


def build_request() -> LLMGenerationRequest:
    return LLMGenerationRequest(
        business_question="Analyze enterprise online sales.",
        trace_summary="Deterministic trace completed.",
        execution_plan=[
            ExecutionPlanStep(step=1, name="create_run", status="completed")
        ],
        retrieval_context={
            "retrieval_event_id": "trace-1",
            "documents_retrieved": 2,
        },
        business_data_summary=AgentTraceSummary(
            retrieval_event_id=None,
            tool_call_ids=[],
            documents_retrieved=2,
            customers_returned=1,
            sales_summary=SalesSummary(
                total_revenue="350.00",
                total_quantity=5,
                number_of_sales=2,
                unique_customers=1,
                top_region="east",
                top_channel="online",
            ),
        ),
        system_instruction="Trace only.",
    )


def test_mock_provider_is_deterministic() -> None:
    provider = MockLLMProvider()
    request = build_request()

    first = provider.generate(request)
    second = provider.generate(request)

    assert first == second
    assert "Business question: Analyze enterprise online sales." in first.content
    assert "Documents retrieved: yes (2)" in first.content
    assert "Tool calls recorded: 0" in first.content
    assert first.provider == "mock"


def test_provider_factory_returns_mock_by_default() -> None:
    provider = create_llm_provider("mock", "mock-trace-generator")

    assert isinstance(provider, MockLLMProvider)


def test_unknown_provider_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm_provider("unknown", "test-model")


@pytest.mark.parametrize(
    ("provider_name", "expected_error"),
    [
        ("openai", "OPENAI_API_KEY is required"),
        ("gemini", "GEMINI_API_KEY is required"),
        ("deepseek", "DEEPSEEK_API_KEY is required"),
    ],
)
def test_real_provider_skeletons_fail_without_api_key(
    provider_name: str,
    expected_error: str,
) -> None:
    provider = create_llm_provider(provider_name, "test-model")

    with pytest.raises(ValueError, match=expected_error):
        provider.generate(build_request())
