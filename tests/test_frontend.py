import pytest
from fastapi.testclient import TestClient

from app import main as app_main
from app.main import app

client = TestClient(app)


def test_root_redirects_to_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_main, "create_database_tables", lambda: None)
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/app/"


def test_app_shell_serves_html(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_main, "create_database_tables", lambda: None)
    response = client.get("/app/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Signal Layer" in response.text


def test_app_shell_loads_without_demo_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main, "create_database_tables", lambda: None)
    monkeypatch.setattr(app_main.settings, "require_demo_api_key", True)
    monkeypatch.setattr(app_main.settings, "demo_api_key", "secret-key")

    response = client.get("/app/")

    assert response.status_code == 200
    assert "Signal Layer" in response.text
