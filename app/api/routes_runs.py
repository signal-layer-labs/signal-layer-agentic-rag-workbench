from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.rag.retrieval import RetrievalService, get_retrieval_service
from app.schemas.documents import (
    DocumentSearchResult,
    RunRetrievalRequest,
    RunRetrievalResponse,
)
from app.schemas.runs import AgentRunResponse, CreateAgentRunRequest
from app.services.run_service import RunService, get_run_service

router = APIRouter(prefix="/runs", tags=["runs"])
RunServiceDependency = Annotated[RunService, Depends(get_run_service)]
RetrievalServiceDependency = Annotated[
    RetrievalService,
    Depends(get_retrieval_service),
]


@router.post("", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    request: CreateAgentRunRequest,
    service: RunServiceDependency,
) -> AgentRunResponse:
    return AgentRunResponse.model_validate(
        service.create_run(request.business_question)
    )


@router.post("/{run_id}/retrieve", response_model=RunRetrievalResponse)
def retrieve_for_run(
    run_id: UUID,
    request: RunRetrievalRequest,
    run_service: RunServiceDependency,
    retrieval_service: RetrievalServiceDependency,
) -> RunRetrievalResponse:
    if run_service.get_run(run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )
    results = retrieval_service.search(request.query, request.limit)
    event_id = run_service.log_retrieval(run_id, request.query, results)
    return RunRetrievalResponse(
        run_id=run_id,
        retrieval_event_id=event_id,
        query=request.query,
        results=[
            DocumentSearchResult(
                chunk_id=result.chunk_id,
                document=result.document,
                metadata=result.metadata,
                score=result.score,
            )
            for result in results
        ],
    )


@router.get("/{run_id}", response_model=AgentRunResponse)
def get_run(run_id: UUID, service: RunServiceDependency) -> AgentRunResponse:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )
    return AgentRunResponse.model_validate(run)
