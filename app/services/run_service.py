from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.models import AgentRun
from app.db.repositories import (
    AgentRunRepository,
    RetrievalEventRepository,
    SqlAlchemyAgentRunRepository,
    SqlAlchemyRetrievalEventRepository,
)
from app.db.session import get_db_session
from app.rag.vector_store import SearchResult

MOCK_RUN_SUMMARY = (
    "Mock run created. Agent execution will be added in a later phase."
)


class RunService:
    def __init__(
        self,
        repository: AgentRunRepository,
        retrieval_event_repository: RetrievalEventRepository | None = None,
    ) -> None:
        self.repository = repository
        self.retrieval_event_repository = retrieval_event_repository

    def create_run(self, business_question: str) -> AgentRun:
        return self.repository.create(
            business_question=business_question,
            summary=MOCK_RUN_SUMMARY,
        )

    def get_run(self, run_id: UUID) -> AgentRun | None:
        return self.repository.get_by_id(run_id)

    def list_recent_runs(self, limit: int = 20) -> list[AgentRun]:
        return list(self.repository.list_recent(limit))

    def log_retrieval(
        self,
        run_id: UUID,
        query: str,
        results: list[SearchResult],
    ) -> UUID:
        if self.retrieval_event_repository is None:
            raise RuntimeError("Retrieval event persistence is not configured.")
        items: list[dict[str, object]] = [
            {
                "chunk_id": result.chunk_id,
                "document": result.document,
                "metadata": result.metadata,
                "distance": result.distance,
            }
            for result in results
        ]
        event = self.retrieval_event_repository.create(
            run_id=run_id,
            query=query,
            source="chroma",
            retrieved_items=items,
        )
        return event.id


def get_run_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> RunService:
    return RunService(
        repository=SqlAlchemyAgentRunRepository(session),
        retrieval_event_repository=SqlAlchemyRetrievalEventRepository(session),
    )
