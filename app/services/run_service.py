from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.models import AgentRun
from app.db.repositories import AgentRunRepository, SqlAlchemyAgentRunRepository
from app.db.session import get_db_session

MOCK_RUN_SUMMARY = (
    "Mock run created. Agent execution will be added in a later phase."
)


class RunService:
    def __init__(self, repository: AgentRunRepository) -> None:
        self.repository = repository

    def create_run(self, business_question: str) -> AgentRun:
        return self.repository.create(
            business_question=business_question,
            summary=MOCK_RUN_SUMMARY,
        )

    def get_run(self, run_id: UUID) -> AgentRun | None:
        return self.repository.get_by_id(run_id)

    def list_recent_runs(self, limit: int = 20) -> list[AgentRun]:
        return list(self.repository.list_recent(limit))


def get_run_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> RunService:
    return RunService(SqlAlchemyAgentRunRepository(session))
