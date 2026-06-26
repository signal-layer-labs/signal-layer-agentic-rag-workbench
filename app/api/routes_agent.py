from typing import Annotated

from fastapi import APIRouter, Depends

from app.agents.agno_agent import AgnoAgentRunner, get_agno_agent_runner
from app.agents.schemas import AgnoAgentRunRequest, AgnoAgentRunResponse
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
AgnoRunnerDependency = Annotated[
    AgnoAgentRunner,
    Depends(get_agno_agent_runner),
]


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    request: AgentRunRequest,
    orchestrator: OrchestratorDependency,
) -> AgentRunResponse:
    return orchestrator.run(request)


@router.post("/agno/run", response_model=AgnoAgentRunResponse)
def run_agno_agent(
    request: AgnoAgentRunRequest,
    runner: AgnoRunnerDependency,
) -> AgnoAgentRunResponse:
    return runner.run(request)
