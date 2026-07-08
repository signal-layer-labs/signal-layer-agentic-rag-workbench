"""Deterministic smoke checks for a deployed demo instance."""

from __future__ import annotations

import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def build_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def fetch_status(url: str) -> int:
    request = Request(url, headers=build_headers())
    try:
        with urlopen(request, timeout=10) as response:
            _ = response.read()
            return response.status
    except HTTPError as error:
        _ = error.read()
        return error.code
    except URLError as error:
        print(f"FAIL request error for {url}: {error}")
        return 0


def build_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    demo_api_key = os.environ.get("DEMO_API_KEY", "")
    if demo_api_key:
        headers[os.environ.get("DEMO_API_KEY_HEADER", "X-Demo-API-Key")] = (
            demo_api_key
        )
    return headers


def main() -> int:
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    docs_enabled = os.environ.get("DOCS_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
    }

    checks: list[tuple[str, int]] = []
    checks.append(("/health", fetch_status(build_url(base_url, "/health"))))

    if docs_enabled:
        checks.append(("/docs", fetch_status(build_url(base_url, "/docs"))))

    failed = False
    for path, status in checks:
        if path == "/health" and status != 200:
            failed = True
            print(f"FAIL {path}: expected 200, got {status}")
            continue
        if path == "/docs" and status not in {200, 307, 308}:
            failed = True
            print(f"FAIL {path}: expected 200/307/308, got {status}")
            continue
        print(f"PASS {path}: {status}")

    if failed:
        return 1

    print("Deployment smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
