from app.core.errors import budget_exceeded


def ensure_limit_within_budget(
    *,
    limit: int,
    max_limit: int,
    resource_name: str,
) -> None:
    if limit > max_limit:
        raise budget_exceeded(
            f"{resource_name} limit exceeds the configured maximum.",
            details={
                "resource": resource_name,
                "limit": limit,
                "max_limit": max_limit,
            },
        )
