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


def test_validate_deployment_settings_flags_hosted_security_risks() -> None:
    settings = Settings(
        deployment_mode="hosted",
        require_demo_api_key=False,
        rate_limit_enabled=False,
        rate_limit_requests=0,
        rate_limit_window_seconds=0,
        max_request_body_bytes=0,
    )

    issues = validate_deployment_settings(settings)

    assert {issue.code for issue in issues} >= {
        "demo_api_key_disabled_hosted",
        "rate_limit_disabled_hosted",
        "rate_limit_requests_invalid",
        "rate_limit_window_invalid",
        "max_request_body_bytes_invalid",
    }


def test_hosted_validation_warns_when_demo_key_enabled_but_blank() -> None:
    settings = Settings(
        deployment_mode="hosted",
        require_demo_api_key=True,
        demo_api_key="",
    )

    issues = validate_deployment_settings(settings)

    assert "demo_api_key_missing_hosted" in {issue.code for issue in issues}


def test_local_defaults_keep_demo_access_open() -> None:
    settings = Settings()

    assert settings.deployment_mode == "local"
    assert settings.require_demo_api_key is False
    assert settings.rate_limit_enabled is False
