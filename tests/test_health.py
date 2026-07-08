import pytest
from fastapi.testclient import TestClient

from app import main as app_main
from app.api import routes_health
from app.main import app

client = TestClient(app)


def test_health(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_main, "create_database_tables", lambda: None)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "signal-layer-agentic-rag-workbench",
    }


def test_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check_ready_database() -> None:
        return None

    monkeypatch.setattr(app_main, "create_database_tables", lambda: None)
    monkeypatch.setattr(
        routes_health,
        "check_ready_database",
        fake_check_ready_database,
    )
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "signal-layer-agentic-rag-workbench",
    }


def test_ready_returns_503_when_database_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_check_ready_database() -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(app_main, "create_database_tables", lambda: None)
    monkeypatch.setattr(
        routes_health,
        "check_ready_database",
        fake_check_ready_database,
    )
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Readiness check failed.",
            "retryable": False,
            "details": {},
        }
    }
