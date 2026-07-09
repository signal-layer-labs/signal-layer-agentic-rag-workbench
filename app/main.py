import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from app.api.routes_agent import router as agent_router
from app.api.routes_business import router as business_router
from app.api.routes_documents import router as documents_router
from app.api.routes_evals import router as evals_router
from app.api.routes_health import router as health_router
from app.api.routes_runs import router as runs_router
from app.core.config import get_settings
from app.core.deployment import (
    parse_cors_allowed_origins,
    validate_deployment_settings,
)
from app.core.errors import (
    AppError,
    internal_error,
    not_found,
    unsupported_document_type,
    validation_error,
)
from app.core.security import enforce_security
from app.db.session import create_database_tables
from app.observability.tracing import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    for issue in validate_deployment_settings(settings):
        logger.warning("%s: %s", issue.code, issue.message)
    create_database_tables()
    yield


settings = get_settings()
app = FastAPI(
    title="Signal Layer Agentic RAG Workbench",
    description="Backend foundation for traceable agent runs.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_allowed_origins(settings.cors_allowed_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method == "OPTIONS":
        return await call_next(request)
    blocked_response = enforce_security(request, settings)
    if blocked_response is not None:
        return blocked_response
    return await call_next(request)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content=error.to_response(),
    )


@app.exception_handler(ValueError)
async def handle_value_error(_: Request, error: ValueError) -> JSONResponse:
    app_error = (
        unsupported_document_type(str(error))
        if "Unsupported document type" in str(error)
        else validation_error(str(error))
    )
    return JSONResponse(
        status_code=app_error.status_code,
        content=app_error.to_response(),
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(_: Request, error: HTTPException) -> JSONResponse:
    message = (
        error.detail if isinstance(error.detail, str) else "The request failed."
    )
    if error.status_code == 404:
        app_error = not_found(message)
    elif error.status_code == 415:
        app_error = unsupported_document_type(message)
    elif error.status_code == 422:
        app_error = validation_error(message)
    else:
        app_error = AppError(
            code="http_error",
            message=message,
            status_code=error.status_code,
        )
    return JSONResponse(
        status_code=app_error.status_code,
        content=app_error.to_response(),
    )


@app.exception_handler(Exception)
async def handle_uncaught_error(_: Request, error: Exception) -> JSONResponse:
    app_error = internal_error()
    return JSONResponse(
        status_code=app_error.status_code,
        content=app_error.to_response(),
    )


app.include_router(health_router)
app.include_router(runs_router)
app.include_router(documents_router)
app.include_router(business_router)
app.include_router(agent_router)
app.include_router(evals_router)


@app.get("/", include_in_schema=False)
async def index() -> RedirectResponse:
    return RedirectResponse(url="/app/")


FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount(
    "/app",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend",
)
