from app.core.errors import provider_not_configured, provider_not_implemented
from app.providers.base import LLMGenerationRequest, LLMGenerationResponse


class GeminiLLMProvider:
    def __init__(self, model: str, api_key: str | None) -> None:
        self.model = model
        self.api_key = api_key

    def generate(
        self,
        request: LLMGenerationRequest,
    ) -> LLMGenerationResponse:
        if not self.api_key:
            raise provider_not_configured(
                "GEMINI_API_KEY is required when LLM_PROVIDER=gemini."
            )
        raise provider_not_implemented(
            "The Gemini provider skeleton is configured but not implemented yet."
        )
