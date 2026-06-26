from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import AppError, budget_exceeded, validation_error
from app.core.timing import measure_time
from app.evals.runner import EvalRunner
from app.main import app
from app.mcp.tools import execute_mcp_tool, normalize_mcp_error
from app.providers.factory import create_llm_provider, get_llm_provider
from app.rag.retrieval import RetrievalService, get_retrieval_service
from app.schemas.evals import EvalCase
from app.services.agent_orchestrator import get_agent_orchestrator
from app.services.run_service import get_run_service


class StubSearchService:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def search(
        self,
        query: str,
        limit: int,
        where: dict[str, object] | None = None,
    ) -> list[object]:
        raise self.error


class DummyEmbeddingProvider:
    def embed_text(self, query: str) -> list[float]:
        return [1.0]


class DummyVectorStore:
    def search(
        self,
        embedding: list[float],
        limit: int,
        where: dict[str, object] | None = None,
    ) -> list[object]:
        return []


class StubOrchestrator:
    def run(self, request: Any) -> Any:
        raise validation_error("stubbed app error")


class StubRunService:
    def create_run(self, business_question: str) -> Any:
        raise NotImplementedError

    def get_run(self, run_id: Any) -> None:
        return None


def clear_settings_caches() -> None:
    get_settings.cache_clear()
    get_llm_provider.cache_clear()


def test_app_error_serializes_to_expected_error_response_shape() -> None:
    error = budget_exceeded(
        "Too many retrieval results requested.",
        details={"limit": 20, "max_limit": 10},
    )

    assert error.to_response() == {
        "error": {
            "code": "budget_exceeded",
            "message": "Too many retrieval results requested.",
            "retryable": False,
            "details": {"limit": 20, "max_limit": 10},
        }
    }


def test_fastapi_app_error_handler_returns_structured_error() -> None:
    app.dependency_overrides[get_agent_orchestrator] = lambda: StubOrchestrator()
    client = TestClient(app)

    response = client.post(
        "/agent/run",
        json={"business_question": "Analyze sales."},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "stubbed app error",
            "retryable": False,
            "details": {},
        }
    }


def test_http_exception_404_is_normalized_to_structured_error() -> None:
    app.dependency_overrides[get_run_service] = lambda: StubRunService()
    client = TestClient(app)

    response = client.get("/runs/00000000-0000-0000-0000-000000000001")

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Agent run not found.",
            "retryable": False,
            "details": {},
        }
    }


def test_known_validation_value_error_returns_controlled_error_shape() -> None:
    app.dependency_overrides[get_retrieval_service] = lambda: StubSearchService(
        ValueError("Known validation issue.")
    )
    client = TestClient(app)

    response = client.post(
        "/documents/search",
        json={"query": "discount approval rules", "limit": 5},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Known validation issue.",
            "retryable": False,
            "details": {},
        }
    }


def test_http_exception_415_is_normalized_to_structured_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/documents/parse",
        files={"file": ("policy.csv", b"a,b,c\n1,2,3\n", "text/csv")},
    )

    assert response.status_code == 415
    assert response.json() == {
        "error": {
            "code": "unsupported_document_type",
            "message": "Unsupported document type for parsing.",
            "retryable": False,
            "details": {},
        }
    }


def test_unknown_provider_returns_unsupported_provider_error() -> None:
    with pytest.raises(AppError, match="Unsupported LLM provider"):
        create_llm_provider("unknown", "test-model")


def test_missing_provider_key_returns_provider_not_configured_error() -> None:
    provider = create_llm_provider("openai", "test-model")

    with pytest.raises(AppError, match="OPENAI_API_KEY is required"):
        provider.generate(object())  # type: ignore[arg-type]


def test_provider_skeleton_returns_provider_not_implemented_error() -> None:
    provider = create_llm_provider("openai", "test-model", api_key="configured")

    with pytest.raises(AppError, match="not implemented yet"):
        provider.generate(object())  # type: ignore[arg-type]


def test_timing_helper_returns_non_negative_latency() -> None:
    with measure_time() as timer:
        _ = sum(range(10))

    assert timer.elapsed_ms >= 0


def test_retrieval_limit_is_rejected_when_above_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_RETRIEVAL_RESULTS", "10")
    clear_settings_caches()
    service = RetrievalService(
        chunker=object(),  # type: ignore[arg-type]
        embedding_provider=DummyEmbeddingProvider(),  # type: ignore[arg-type]
        vector_store=DummyVectorStore(),  # type: ignore[arg-type]
    )

    with pytest.raises(AppError, match="configured maximum"):
        service.search("discount approval rules", limit=11)


def test_eval_case_budget_rejects_too_many_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_EVAL_CASES", "2")
    clear_settings_caches()
    runner = EvalRunner(
        retrieval_service=object(),  # type: ignore[arg-type]
        orchestrator=object(),  # type: ignore[arg-type]
    )
    cases = [
        EvalCase(
            id=f"case-{index}",
            name=f"Case {index}",
            business_question="Question",
            documents=[],
        )
        for index in range(3)
    ]

    with pytest.raises(AppError, match="configured maximum"):
        runner.run_cases(cases)


def test_mcp_error_normalization_does_not_expose_stack_traces() -> None:
    envelope = normalize_mcp_error(RuntimeError("boom")).model_dump(mode="json")

    assert envelope["error"]["code"] == "mcp_tool_error"
    assert "traceback" not in str(envelope).lower()
    assert "RuntimeError" not in str(envelope)


def test_execute_mcp_tool_returns_controlled_error_envelope() -> None:
    result = execute_mcp_tool(lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    assert result.model_dump(mode="json") == {
        "error": {
            "code": "mcp_tool_error",
            "message": "The MCP tool request failed.",
            "retryable": False,
            "details": {},
        }
    }
