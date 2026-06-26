from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app.agents.agno_tools import (
    query_customers_tool,
    retrieve_documents_tool,
    run_traceable_workflow_tool,
    summarize_sales_tool,
)
from app.agents.schemas import (
    AgnoAgentRunRequest,
    AgnoAgentRunResponse,
    AgnoToolDescriptor,
)
from app.core.config import get_settings
from app.core.errors import unsupported_provider, validation_error
from app.db.business_repositories import SqlAlchemyBusinessRepository
from app.db.repositories import (
    SqlAlchemyAgentRunRepository,
    SqlAlchemyRetrievalEventRepository,
    SqlAlchemyToolCallRepository,
)
from app.db.session import get_db_session
from app.rag.retrieval import RetrievalService, get_retrieval_service
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.business_service import BusinessService
from app.services.business_tool_executor import BusinessToolExecutor
from app.services.response_generator import ResponseGenerator, get_response_generator
from app.services.run_service import RunService

try:
    from agno.agent import Agent as AgnoAgent  # type: ignore[import-not-found]
except ImportError:
    AgnoAgent = None

AGNO_AGENT_INSTRUCTIONS = (
    "Use only the approved allowlisted tools, preserve trace-first behavior, "
    "and do not bypass the existing service layer."
)


class AgnoAgentRunner:
    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        retrieval_service: RetrievalService,
        business_service: BusinessService,
    ) -> None:
        self.orchestrator = orchestrator
        self.retrieval_service = retrieval_service
        self.business_service = business_service
        self._descriptor_registry = {
            "retrieve_documents": retrieve_documents_tool,
            "query_customers": query_customers_tool,
            "summarize_sales": summarize_sales_tool,
        }
        self._internal_registry = {
            "run_traceable_workflow": run_traceable_workflow_tool,
        }

    def get_tool_descriptors(self) -> list[AgnoToolDescriptor]:
        descriptors: list[AgnoToolDescriptor] = []
        for name, tool in self._descriptor_registry.items():
            description = (tool.__doc__ or "").strip()
            if not description:
                raise validation_error(f"Agno tool {name} is missing a docstring.")
            descriptors.append(
                AgnoToolDescriptor(
                    name=name,
                    description=description,
                )
            )
        return descriptors

    def invoke_tool(self, tool_name: str, **kwargs: Any) -> Any:
        if tool_name == "retrieve_documents":
            return retrieve_documents_tool(self.retrieval_service, **kwargs)
        if tool_name == "query_customers":
            return query_customers_tool(self.business_service, **kwargs)
        if tool_name == "summarize_sales":
            return summarize_sales_tool(self.business_service, **kwargs)
        if tool_name in self._internal_registry:
            return run_traceable_workflow_tool(self.orchestrator, **kwargs)
        raise validation_error(f"Unknown Agno tool: {tool_name}")

    def prepare_agent(self) -> Any | None:
        settings = get_settings()
        if not settings.agno_enabled:
            return None
        if AgnoAgent is None:
            return None
        if settings.agno_allow_real_provider:
            raise unsupported_provider(
                "Real Agno model execution is not enabled in this foundation."
            )
        return AgnoAgent(
            name="signal-layer-agno-adapter",
            instructions=AGNO_AGENT_INSTRUCTIONS,
        )

    def run(self, request: AgnoAgentRunRequest) -> AgnoAgentRunResponse:
        self.prepare_agent()
        response = self.orchestrator.run(request)
        allowed_tools = [descriptor.name for descriptor in self.get_tool_descriptors()]
        agent_output = (
            "Agno agent adapter executed through the trace-first workflow using "
            f"allowlisted tools: {', '.join(allowed_tools)}."
        )
        return AgnoAgentRunResponse.from_agent_run(
            response,
            agent_instructions=AGNO_AGENT_INSTRUCTIONS,
            allowed_tools=allowed_tools,
            agent_output=agent_output,
        )


def build_agno_agent_runner(
    session: Session,
    retrieval_service: RetrievalService,
    response_generator: ResponseGenerator,
) -> AgnoAgentRunner:
    business_service = BusinessService(SqlAlchemyBusinessRepository(session))
    orchestrator = AgentOrchestrator(
        run_service=RunService(
            repository=SqlAlchemyAgentRunRepository(session),
            retrieval_event_repository=SqlAlchemyRetrievalEventRepository(session),
        ),
        retrieval_service=retrieval_service,
        business_executor=BusinessToolExecutor(
            service=business_service,
            run_repository=SqlAlchemyAgentRunRepository(session),
            tool_call_repository=SqlAlchemyToolCallRepository(session),
        ),
        response_generator=response_generator,
    )
    return AgnoAgentRunner(
        orchestrator=orchestrator,
        retrieval_service=retrieval_service,
        business_service=business_service,
    )


def get_agno_agent_runner(
    session: Annotated[Session, Depends(get_db_session)],
    retrieval_service: Annotated[
        RetrievalService,
        Depends(get_retrieval_service),
    ],
    response_generator: Annotated[
        ResponseGenerator,
        Depends(get_response_generator),
    ],
) -> AgnoAgentRunner:
    return build_agno_agent_runner(session, retrieval_service, response_generator)
