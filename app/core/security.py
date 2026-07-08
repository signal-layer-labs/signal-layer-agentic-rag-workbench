from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Final

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import Settings

INFRA_PATHS: Final[set[str]] = {
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


rate_limiter = InMemoryRateLimiter()


def is_infra_path(path: str) -> bool:
    return path in INFRA_PATHS


def is_demo_path(path: str) -> bool:
    return not is_infra_path(path)


def make_error_response(
    *,
    code: str,
    message: str,
    status_code: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "retryable": False,
                "details": {},
            }
        },
    )


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client is None:
        return "unknown"
    return request.client.host


def enforce_security(
    request: Request,
    settings: Settings,
) -> JSONResponse | None:
    path = request.url.path
    if not is_demo_path(path):
        return None

    if not settings.enable_demo_endpoints:
        return make_error_response(
            code="not_found",
            message="The requested resource was not found.",
            status_code=404,
        )

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > settings.max_request_body_bytes:
                return make_error_response(
                    code="payload_too_large",
                    message="Request body exceeds the configured limit.",
                    status_code=413,
                )
        except ValueError:
            return make_error_response(
                code="validation_error",
                message="Invalid Content-Length header.",
                status_code=422,
            )

    if settings.require_demo_api_key and path not in INFRA_PATHS:
        header_name = settings.demo_api_key_header
        provided = request.headers.get(header_name, "")
        if not provided or not secrets.compare_digest(
            provided,
            settings.demo_api_key,
        ):
            return make_error_response(
                code="unauthorized",
                message="Invalid or missing demo API key.",
                status_code=401,
            )

    if settings.rate_limit_enabled and path not in {"/health", "/ready"}:
        limit_key = get_client_ip(request)
        if not rate_limiter.allow(
            limit_key,
            settings.rate_limit_requests,
            settings.rate_limit_window_seconds,
        ):
            return make_error_response(
                code="rate_limit_exceeded",
                message="Too many requests.",
                status_code=429,
            )

    return None
