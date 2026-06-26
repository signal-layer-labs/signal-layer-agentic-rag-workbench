import pytest

from app.core.config import get_settings
from app.core.errors import AppError
from app.providers.base import LLMGenerationRequest
from app.providers.deepseek_provider import DeepSeekLLMProvider
from app.providers.factory import create_llm_provider, get_llm_provider
from app.providers.gemini_provider import GeminiLLMProvider
from app.providers.mock_provider import MockLLMProvider
from app.providers.openai_provider import OpenAILLMProvider
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


def clear_provider_caches() -> None:
    get_settings.cache_clear()
    get_llm_provider.cache_clear()


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
    with pytest.raises(AppError, match="Unsupported LLM provider"):
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

    with pytest.raises(AppError, match=expected_error):
        provider.generate(build_request())


@pytest.mark.parametrize(
    "provider_name",
    ["openai", "gemini", "deepseek"],
)
def test_real_provider_skeletons_raise_not_implemented_when_configured(
    provider_name: str,
) -> None:
    provider = create_llm_provider(provider_name, "test-model", api_key="configured")

    with pytest.raises(AppError, match="not implemented yet"):
        provider.generate(build_request())


def test_openai_uses_openai_api_key_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "test-openai-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    clear_provider_caches()

    provider = get_llm_provider()

    assert isinstance(provider, OpenAILLMProvider)
    assert provider.api_key == "openai-key"


def test_gemini_uses_gemini_api_key_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "test-gemini-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    clear_provider_caches()

    provider = get_llm_provider()

    assert isinstance(provider, GeminiLLMProvider)
    assert provider.api_key == "gemini-key"


def test_deepseek_uses_deepseek_api_key_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_MODEL", "test-deepseek-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    clear_provider_caches()

    provider = get_llm_provider()

    assert isinstance(provider, DeepSeekLLMProvider)
    assert provider.api_key == "deepseek-key"


def test_gemini_does_not_use_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "test-gemini-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    clear_provider_caches()

    provider = get_llm_provider()

    assert isinstance(provider, GeminiLLMProvider)
    assert provider.api_key is None


def test_deepseek_does_not_use_other_provider_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_MODEL", "test-deepseek-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    clear_provider_caches()

    provider = get_llm_provider()

    assert isinstance(provider, DeepSeekLLMProvider)
    assert provider.api_key is None
