from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.business_repositories import (
    CustomerFilters,
    SalesFilters,
    SqlAlchemyBusinessRepository,
)
from app.db.repositories import (
    SqlAlchemyAgentRunRepository,
    SqlAlchemyRetrievalEventRepository,
    SqlAlchemyToolCallRepository,
)
from app.db.session import SessionLocal
from app.mcp.schemas import (
    QueryCustomersToolInput,
    RunTraceableWorkflowInput,
    SummarizeSalesToolInput,
)
from app.rag.embeddings import MockEmbeddingProvider
from app.rag.retrieval import RetrievalService
from app.rag.vector_store import ChromaVectorStore
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.schemas.business import CustomerSummary, SalesSummary
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.business_service import BusinessService
from app.services.business_tool_executor import BusinessToolExecutor
from app.services.response_generator import ResponseGenerator
from app.services.run_service import RunService


@contextmanager
def managed_session(session: Session | None = None) -> Generator[Session, None, None]:
    if session is not None:
        yield session
        return
    with SessionLocal() as owned_session:
        yield owned_session


def build_business_service(session: Session) -> BusinessService:
    return BusinessService(SqlAlchemyBusinessRepository(session))


def build_agent_orchestrator(session: Session) -> AgentOrchestrator:
    settings = get_settings()
    retrieval_service = RetrievalService(
        chunker=__import__(
            "app.rag.chunking",
            fromlist=["TextChunker"],
        ).TextChunker(settings.chunk_size, settings.chunk_overlap),
        embedding_provider=MockEmbeddingProvider(),
        vector_store=ChromaVectorStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection_name=settings.chroma_collection,
        ),
    )
    run_service = RunService(
        repository=SqlAlchemyAgentRunRepository(session),
        retrieval_event_repository=SqlAlchemyRetrievalEventRepository(session),
    )
    business_executor = BusinessToolExecutor(
        service=build_business_service(session),
        run_repository=SqlAlchemyAgentRunRepository(session),
        tool_call_repository=SqlAlchemyToolCallRepository(session),
    )
    response_generator = ResponseGenerator(
        __import__(
            "app.providers.factory",
            fromlist=["get_llm_provider"],
        ).get_llm_provider()
    )
    return AgentOrchestrator(
        run_service=run_service,
        retrieval_service=retrieval_service,
        business_executor=business_executor,
        response_generator=response_generator,
    )


def query_customers(
    payload: QueryCustomersToolInput | dict[str, object],
    *,
    service: BusinessService | None = None,
    session: Session | None = None,
) -> list[CustomerSummary]:
    request = (
        payload
        if isinstance(payload, QueryCustomersToolInput)
        else QueryCustomersToolInput.model_validate(payload)
    )
    if service is not None:
        customers = service.query_customers(
            CustomerFilters(
                segment=request.segment,
                region=request.region,
                status=request.status,
                limit=request.limit,
            )
        )
        return [CustomerSummary.model_validate(customer) for customer in customers]
    with managed_session(session) as active_session:
        business_service = build_business_service(active_session)
        customers = business_service.query_customers(
            CustomerFilters(
                segment=request.segment,
                region=request.region,
                status=request.status,
                limit=request.limit,
            )
        )
        return [CustomerSummary.model_validate(customer) for customer in customers]


def summarize_sales(
    payload: SummarizeSalesToolInput | dict[str, object],
    *,
    service: BusinessService | None = None,
    session: Session | None = None,
) -> SalesSummary:
    request = (
        payload
        if isinstance(payload, SummarizeSalesToolInput)
        else SummarizeSalesToolInput.model_validate(payload)
    )
    if service is not None:
        return service.summarize_sales(
            SalesFilters(
                region=request.region,
                channel=request.channel,
                start_date=request.start_date,
                end_date=request.end_date,
                limit=None,
            )
        )
    with managed_session(session) as active_session:
        business_service = build_business_service(active_session)
        return business_service.summarize_sales(
            SalesFilters(
                region=request.region,
                channel=request.channel,
                start_date=request.start_date,
                end_date=request.end_date,
                limit=None,
            )
        )


def run_traceable_workflow(
    payload: RunTraceableWorkflowInput | dict[str, object],
    *,
    orchestrator: AgentOrchestrator | None = None,
    session: Session | None = None,
) -> AgentRunResponse:
    request = (
        payload
        if isinstance(payload, RunTraceableWorkflowInput)
        else RunTraceableWorkflowInput.model_validate(payload)
    )
    agent_request = AgentRunRequest(
        business_question=request.business_question,
        retrieval_query=request.retrieval_query,
        sales_region=request.sales_region,
        sales_channel=request.sales_channel,
        customer_segment=request.customer_segment,
        generate_response=request.generate_response,
    )
    if orchestrator is not None:
        return orchestrator.run(agent_request)
    with managed_session(session) as active_session:
        return build_agent_orchestrator(active_session).run(agent_request)
