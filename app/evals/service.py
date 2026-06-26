from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.business_repositories import SqlAlchemyBusinessRepository
from app.db.repositories import (
    SqlAlchemyAgentRunRepository,
    SqlAlchemyRetrievalEventRepository,
    SqlAlchemyToolCallRepository,
)
from app.db.session import get_db_session
from app.evals.cases import get_builtin_eval_cases
from app.evals.runner import EvalRunner
from app.rag.retrieval import RetrievalService, get_retrieval_service
from app.schemas.evals import EvalRunReport
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.business_service import BusinessService
from app.services.business_tool_executor import BusinessToolExecutor
from app.services.response_generator import ResponseGenerator, get_response_generator
from app.services.run_service import RunService


class EvalService:
    def __init__(self, runner: EvalRunner) -> None:
        self.runner = runner

    def run_builtin_cases(self) -> EvalRunReport:
        return self.runner.run_cases(get_builtin_eval_cases())


def build_eval_service(
    session: Session,
    retrieval_service: RetrievalService,
    response_generator: ResponseGenerator,
) -> EvalService:
    orchestrator = AgentOrchestrator(
        run_service=RunService(
            repository=SqlAlchemyAgentRunRepository(session),
            retrieval_event_repository=SqlAlchemyRetrievalEventRepository(session),
        ),
        retrieval_service=retrieval_service,
        business_executor=BusinessToolExecutor(
            service=BusinessService(SqlAlchemyBusinessRepository(session)),
            run_repository=SqlAlchemyAgentRunRepository(session),
            tool_call_repository=SqlAlchemyToolCallRepository(session),
        ),
        response_generator=response_generator,
    )
    return EvalService(EvalRunner(retrieval_service, orchestrator))


def get_eval_service(
    session: Annotated[Session, Depends(get_db_session)],
    retrieval_service: Annotated[
        RetrievalService,
        Depends(get_retrieval_service),
    ],
    response_generator: Annotated[
        ResponseGenerator,
        Depends(get_response_generator),
    ],
) -> EvalService:
    return build_eval_service(
        session=session,
        retrieval_service=retrieval_service,
        response_generator=response_generator,
    )
