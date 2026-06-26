from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_agent import router as agent_router
from app.api.routes_business import router as business_router
from app.api.routes_documents import router as documents_router
from app.api.routes_health import router as health_router
from app.api.routes_runs import router as runs_router
from app.core.config import get_settings
from app.db.session import create_database_tables
from app.observability.tracing import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    create_database_tables()
    yield


app = FastAPI(
    title="Signal Layer Agentic RAG Workbench",
    description="Backend foundation for traceable agent runs.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(runs_router)
app.include_router(documents_router)
app.include_router(business_router)
app.include_router(agent_router)
