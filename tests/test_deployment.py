from app.core.config import Settings
from app.core.deployment import (
    parse_cors_allowed_origins,
    validate_deployment_settings,
)


def test_parse_cors_allowed_origins_supports_wildcard_and_csv() -> None:
    assert parse_cors_allowed_origins("*") == ["*"]
    assert parse_cors_allowed_origins("https://a.example, https://b.example") == [
        "https://a.example",
        "https://b.example",
    ]


def test_validate_deployment_settings_flags_hosted_demo_risks() -> None:
    settings = Settings(
        deployment_mode="hosted",
        cors_allowed_origins="*",
        enable_demo_endpoints=True,
    )

    issues = validate_deployment_settings(settings)

    assert {issue.code for issue in issues} >= {
        "cors_wildcard_hosted",
        "demo_endpoints_enabled_hosted",
    }
