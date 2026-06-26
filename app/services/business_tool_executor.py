from collections.abc import Callable
from time import perf_counter
from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException, status

from app.db.repositories import AgentRunRepository, ToolCallRepository
from app.services.business_service import BusinessService

ResultT = TypeVar("ResultT")


class BusinessToolExecutor:
    def __init__(
        self,
        service: BusinessService,
        run_repository: AgentRunRepository,
        tool_call_repository: ToolCallRepository,
    ) -> None:
        self.service = service
        self.run_repository = run_repository
        self.tool_call_repository = tool_call_repository

    def execute(
        self,
        tool_name: str,
        run_id: UUID | None,
        tool_input: dict[str, object],
        operation: Callable[[], ResultT],
        serialize: Callable[[ResultT], dict[str, object]],
    ) -> tuple[ResultT, UUID | None]:
        if run_id is not None and self.run_repository.get_by_id(run_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent run not found.",
            )
        started_at = perf_counter()
        result = operation()
        latency_ms = max(0, round((perf_counter() - started_at) * 1000))
        if run_id is None:
            return result, None
        tool_call = self.tool_call_repository.create(
            run_id=run_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=serialize(result),
            status="completed",
            latency_ms=latency_ms,
        )
        return result, tool_call.id
