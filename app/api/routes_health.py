from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class ReadyResponse(BaseModel):
    status: Literal["ok"]
    service: str


def check_ready_database() -> None:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="signal-layer-agentic-rag-workbench",
    )


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    try:
        check_ready_database()
    except Exception as exc:  # pragma: no cover - exercised through failure modes
        raise HTTPException(status_code=503, detail="Readiness check failed.") from exc
    return ReadyResponse(
        status="ok",
        service="signal-layer-agentic-rag-workbench",
    )
