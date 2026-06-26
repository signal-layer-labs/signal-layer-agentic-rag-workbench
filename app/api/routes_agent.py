from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.services.agent_orchestrator import (
    AgentOrchestrator,
    get_agent_orchestrator,
)

router = APIRouter(prefix="/agent", tags=["agent"])
OrchestratorDependency = Annotated[
    AgentOrchestrator,
    Depends(get_agent_orchestrator),
]


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    request: AgentRunRequest,
    orchestrator: OrchestratorDependency,
) -> AgentRunResponse:
    return orchestrator.run(request)
