from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class DeploymentValidationIssue:
    code: str
    message: str


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_cors_allowed_origins(value: str) -> list[str]:
    if value == "*":
        return ["*"]
    return _split_csv(value)


def validate_deployment_settings(settings: Settings) -> list[DeploymentValidationIssue]:
    issues: list[DeploymentValidationIssue] = []

    if not settings.database_url.strip():
        issues.append(
            DeploymentValidationIssue(
                code="database_url_missing",
                message="DATABASE_URL must not be blank.",
            )
        )

    if not settings.chroma_host.strip():
        issues.append(
            DeploymentValidationIssue(
                code="chroma_host_missing",
                message="CHROMA_HOST must not be blank.",
            )
        )

    if settings.chroma_port <= 0:
        issues.append(
            DeploymentValidationIssue(
                code="chroma_port_invalid",
                message="CHROMA_PORT must be a positive integer.",
            )
        )

    if not settings.chroma_collection.strip():
        issues.append(
            DeploymentValidationIssue(
                code="chroma_collection_missing",
                message="CHROMA_COLLECTION must not be blank.",
            )
        )

    cors_origins = parse_cors_allowed_origins(settings.cors_allowed_origins)
    if not cors_origins:
        issues.append(
            DeploymentValidationIssue(
                code="cors_origins_missing",
                message="CORS_ALLOWED_ORIGINS must not be blank.",
            )
        )

    if settings.deployment_mode == "hosted":
        if settings.cors_allowed_origins.strip() == "*":
            issues.append(
                DeploymentValidationIssue(
                    code="cors_wildcard_hosted",
                    message=(
                        "Hosted demo deployments should set explicit "
                        "CORS_ALLOWED_ORIGINS values."
                    ),
                )
            )
        if not settings.require_demo_api_key:
            issues.append(
                DeploymentValidationIssue(
                    code="demo_api_key_disabled_hosted",
                    message=(
                        "Hosted demo deployments should enable "
                        "REQUIRE_DEMO_API_KEY."
                    ),
                )
            )
        if settings.require_demo_api_key and not settings.demo_api_key.strip():
            issues.append(
                DeploymentValidationIssue(
                    code="demo_api_key_missing_hosted",
                    message=(
                        "Hosted demo deployments with "
                        "REQUIRE_DEMO_API_KEY=true must set DEMO_API_KEY."
                    ),
                )
            )
        if not settings.rate_limit_enabled:
            issues.append(
                DeploymentValidationIssue(
                    code="rate_limit_disabled_hosted",
                    message=(
                        "Hosted demo deployments should enable "
                        "RATE_LIMIT_ENABLED."
                    ),
                )
            )
        if settings.enable_demo_endpoints:
            issues.append(
                DeploymentValidationIssue(
                    code="demo_endpoints_enabled_hosted",
                    message=(
                        "Hosted demo deployments should disable "
                        "ENABLE_DEMO_ENDPOINTS unless the demo surface is intended."
                    ),
                )
            )
        if settings.rate_limit_requests <= 0:
            issues.append(
                DeploymentValidationIssue(
                    code="rate_limit_requests_invalid",
                    message="RATE_LIMIT_REQUESTS must be a positive integer.",
                )
            )
        if settings.rate_limit_window_seconds <= 0:
            issues.append(
                DeploymentValidationIssue(
                    code="rate_limit_window_invalid",
                    message=(
                        "RATE_LIMIT_WINDOW_SECONDS must be a positive integer."
                    ),
                )
            )
        if settings.max_request_body_bytes <= 0:
            issues.append(
                DeploymentValidationIssue(
                    code="max_request_body_bytes_invalid",
                    message="MAX_REQUEST_BODY_BYTES must be a positive integer.",
                )
            )

    return issues
