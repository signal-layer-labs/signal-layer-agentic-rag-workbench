from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentRun


class AgentRunRepository(Protocol):
    def create(self, business_question: str, summary: str) -> AgentRun: ...

    def get_by_id(self, run_id: UUID) -> AgentRun | None: ...

    def list_recent(self, limit: int = 20) -> Sequence[AgentRun]: ...


class SqlAlchemyAgentRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, business_question: str, summary: str) -> AgentRun:
        run = AgentRun(
            business_question=business_question,
            status="created",
            summary=summary,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get_by_id(self, run_id: UUID) -> AgentRun | None:
        return self.session.get(AgentRun, run_id)

    def list_recent(self, limit: int = 20) -> Sequence[AgentRun]:
        statement = (
            select(AgentRun)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        return self.session.scalars(statement).all()
