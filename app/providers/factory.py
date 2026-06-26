from functools import lru_cache

from app.core.config import get_settings
from app.providers.base import LLMProvider
from app.providers.deepseek_provider import DeepSeekLLMProvider
from app.providers.gemini_provider import GeminiLLMProvider
from app.providers.mock_provider import MockLLMProvider
from app.providers.openai_provider import OpenAILLMProvider


def create_llm_provider(
    provider_name: str,
    model: str,
    api_key: str | None = None,
) -> LLMProvider:
    if provider_name == "mock":
        return MockLLMProvider(model=model)
    if provider_name == "openai":
        return OpenAILLMProvider(model=model, api_key=api_key)
    if provider_name == "gemini":
        return GeminiLLMProvider(model=model, api_key=api_key)
    if provider_name == "deepseek":
        return DeepSeekLLMProvider(model=model, api_key=api_key)
    raise ValueError(
        "Unsupported LLM provider. Expected one of: "
        "mock, openai, gemini, deepseek."
    )


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    api_key: str | None = None
    if settings.llm_provider == "openai":
        api_key = settings.llm_api_key or settings.openai_api_key
    elif settings.llm_provider == "gemini":
        api_key = settings.llm_api_key or settings.gemini_api_key
    elif settings.llm_provider == "deepseek":
        api_key = settings.llm_api_key or settings.deepseek_api_key
    return create_llm_provider(
        provider_name=settings.llm_provider,
        model=settings.llm_model,
        api_key=api_key,
    )
