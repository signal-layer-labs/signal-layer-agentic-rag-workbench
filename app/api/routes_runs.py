from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.runs import AgentRunResponse, CreateAgentRunRequest
from app.services.run_service import RunService, get_run_service

router = APIRouter(prefix="/runs", tags=["runs"])
RunServiceDependency = Annotated[RunService, Depends(get_run_service)]


@router.post("", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    request: CreateAgentRunRequest,
    service: RunServiceDependency,
) -> AgentRunResponse:
    return AgentRunResponse.model_validate(
        service.create_run(request.business_question)
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
