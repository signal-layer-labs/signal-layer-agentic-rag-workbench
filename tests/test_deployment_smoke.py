from scripts.deployment_smoke import build_headers, build_url


def test_build_url_joins_paths_without_double_slashes() -> None:
    assert build_url("http://localhost:8000/", "/health") == "http://localhost:8000/health"


def test_build_headers_includes_demo_api_key(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_KEY", "secret")
    monkeypatch.setenv("DEMO_API_KEY_HEADER", "X-Test-Key")

    assert build_headers() == {
        "Accept": "application/json",
        "X-Test-Key": "secret",
    }
