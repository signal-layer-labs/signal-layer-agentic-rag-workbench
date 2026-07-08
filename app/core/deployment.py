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

    return issues
