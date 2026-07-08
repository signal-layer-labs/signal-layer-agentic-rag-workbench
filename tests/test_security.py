from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from app.api import routes_agent, routes_health
from app.core import security as security_module
from app.core.config import get_settings


class StubOrchestrator:
    def run(self, request: object) -> object:
        del request
        return {
            "run_id": "00000000-0000-0000-0000-000000000000",
            "status": "created",
            "business_question": "Analyze sales.",
            "execution_plan": [],
            "trace": {
                "retrieval_event_id": None,
                "tool_call_ids": [],
                "documents_retrieved": 0,
                "customers_returned": 0,
                "sales_summary": {
                    "total_revenue": "0",
                    "total_quantity": 0,
                    "number_of_sales": 0,
                    "unique_customers": 0,
                    "top_region": None,
                    "top_channel": None,
                },
            },
            "summary": "ok",
            "generated_response": None,
        }


def load_app(
    monkeypatch: pytest.MonkeyPatch,
    **env: str,
) -> tuple[TestClient, object]:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    security_module.rate_limiter.reset()
    import app.main as app_main

    importlib.reload(app_main)
    return TestClient(app_main.app), app_main


def test_demo_endpoints_can_be_disabled_while_health_remains_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = load_app(monkeypatch, ENABLE_DEMO_ENDPOINTS="false")
    monkeypatch.setattr(routes_health, "check_ready_database", lambda: None)

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.post(
        "/agent/run",
        json={"business_question": "Analyze sales."},
    ).status_code == 404


def test_api_key_guard_rejects_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client, app_main = load_app(
        monkeypatch,
        REQUIRE_DEMO_API_KEY="true",
        DEMO_API_KEY="super-secret",
    )
    app_main.app.dependency_overrides[routes_agent.get_agent_orchestrator] = (
        lambda: StubOrchestrator()
    )

    response = client.post(
        "/agent/run",
        json={"business_question": "Analyze sales."},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Invalid or missing demo API key.",
            "retryable": False,
            "details": {},
        }
    }


def test_api_key_guard_allows_valid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client, app_main = load_app(
        monkeypatch,
        REQUIRE_DEMO_API_KEY="true",
        DEMO_API_KEY="super-secret",
    )
    app_main.app.dependency_overrides[routes_agent.get_agent_orchestrator] = (
        lambda: StubOrchestrator()
    )

    response = client.post(
        "/agent/run",
        json={"business_question": "Analyze sales."},
        headers={"X-Demo-API-Key": "super-secret"},
    )

    assert response.status_code == 200


def test_api_key_guard_rejects_wrong_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client, app_main = load_app(
        monkeypatch,
        REQUIRE_DEMO_API_KEY="true",
        DEMO_API_KEY="super-secret",
    )
    app_main.app.dependency_overrides[routes_agent.get_agent_orchestrator] = (
        lambda: StubOrchestrator()
    )

    response = client.post(
        "/agent/run",
        json={"business_question": "Analyze sales."},
        headers={"X-Demo-API-Key": "wrong-secret"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Invalid or missing demo API key.",
            "retryable": False,
            "details": {},
        }
    }


def test_rate_limiter_returns_429_after_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, app_main = load_app(
        monkeypatch,
        RATE_LIMIT_ENABLED="true",
        RATE_LIMIT_REQUESTS="1",
        RATE_LIMIT_WINDOW_SECONDS="60",
        REQUIRE_DEMO_API_KEY="false",
    )
    app_main.app.dependency_overrides[routes_agent.get_agent_orchestrator] = (
        lambda: StubOrchestrator()
    )

    first = client.post(
        "/agent/run",
        json={"business_question": "Analyze sales."},
    )
    second = client.post(
        "/agent/run",
        json={"business_question": "Analyze sales."},
    )

    assert first.status_code != 429
    assert second.status_code == 429


def test_request_size_guard_returns_413(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = load_app(
        monkeypatch,
        MAX_REQUEST_BODY_BYTES="10",
    )

    response = client.post(
        "/agent/run",
        json={"business_question": "Analyze sales."},
        headers={"Content-Length": "11"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "error": {
            "code": "payload_too_large",
            "message": "Request body exceeds the configured limit.",
            "retryable": False,
            "details": {},
        }
    }
