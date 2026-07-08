from scripts.deployment_smoke import build_url


def test_build_url_joins_paths_without_double_slashes() -> None:
    assert build_url("http://localhost:8000/", "/health") == "http://localhost:8000/health"
