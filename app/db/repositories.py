from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentRun, RetrievalEvent


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


class RetrievalEventRepository(Protocol):
    def create(
        self,
        run_id: UUID,
        query: str,
        source: str,
        retrieved_items: list[dict[str, object]],
    ) -> RetrievalEvent: ...


class SqlAlchemyRetrievalEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        run_id: UUID,
        query: str,
        source: str,
        retrieved_items: list[dict[str, object]],
    ) -> RetrievalEvent:
        event = RetrievalEvent(
            run_id=run_id,
            query=query,
            source=source,
            retrieved_items=retrieved_items,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
