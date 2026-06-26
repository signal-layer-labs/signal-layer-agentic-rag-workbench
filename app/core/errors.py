from dataclasses import dataclass, field


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int
    retryable: bool = False
    details: dict[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message

    def to_response(self) -> dict[str, object]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
            }
        }


def validation_error(
    message: str,
    *,
    details: dict[str, object] | None = None,
    status_code: int = 422,
) -> AppError:
    return AppError(
        code="validation_error",
        message=message,
        status_code=status_code,
        details=details or {},
    )


def unsupported_document_type(
    message: str,
    *,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="unsupported_document_type",
        message=message,
        status_code=415,
        details=details or {},
    )


def not_found(
    message: str,
    *,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="not_found",
        message=message,
        status_code=404,
        details=details or {},
    )


def provider_not_configured(
    message: str,
    *,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="provider_not_configured",
        message=message,
        status_code=422,
        details=details or {},
    )


def provider_not_implemented(
    message: str,
    *,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="provider_not_implemented",
        message=message,
        status_code=501,
        details=details or {},
    )


def unsupported_provider(
    message: str,
    *,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="unsupported_provider",
        message=message,
        status_code=422,
        details=details or {},
    )


def budget_exceeded(
    message: str,
    *,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="budget_exceeded",
        message=message,
        status_code=422,
        details=details or {},
    )


def tool_execution_failed(
    message: str,
    *,
    retryable: bool = False,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="tool_execution_failed",
        message=message,
        status_code=500,
        retryable=retryable,
        details=details or {},
    )


def retrieval_failed(
    message: str,
    *,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="retrieval_failed",
        message=message,
        status_code=500,
        details=details or {},
    )


def orchestration_failed(
    message: str,
    *,
    retryable: bool = False,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="orchestration_failed",
        message=message,
        status_code=500,
        retryable=retryable,
        details=details or {},
    )


def mcp_tool_error(
    message: str,
    *,
    retryable: bool = False,
    details: dict[str, object] | None = None,
) -> AppError:
    return AppError(
        code="mcp_tool_error",
        message=message,
        status_code=500,
        retryable=retryable,
        details=details or {},
    )


def internal_error() -> AppError:
    return AppError(
        code="internal_error",
        message="An internal error occurred.",
        status_code=500,
    )
