from typing import Literal

from pydantic import BaseModel

from app.schemas.agent import AgentRunRequest, AgentRunResponse, GeneratedResponse


class AgnoAgentRunRequest(AgentRunRequest):
    generate_response: bool = True
    use_agno_agent: bool = True


class AgnoToolDescriptor(BaseModel):
    name: str
    description: str


class AgnoAgentTrace(BaseModel):
    run_id: str
    status: str
    execution_plan_steps: int
    documents_retrieved: int
    tool_call_count: int


class AgnoAgentRunResponse(BaseModel):
    mode: Literal["agno"] = "agno"
    run_id: str
    status: str
    business_question: str
    agent_instructions: str
    allowed_tools: list[str]
    execution_plan: list[dict[str, object]]
    trace: dict[str, object]
    generated_response: GeneratedResponse | None = None
    agent_output: str

    @classmethod
    def from_agent_run(
        cls,
        response: AgentRunResponse,
        *,
        agent_instructions: str,
        allowed_tools: list[str],
        agent_output: str,
    ) -> "AgnoAgentRunResponse":
        return cls(
            run_id=str(response.run_id),
            status=response.status,
            business_question=response.business_question,
            agent_instructions=agent_instructions,
            allowed_tools=allowed_tools,
            execution_plan=[
                step.model_dump(mode="json") for step in response.execution_plan
            ],
            trace=response.trace.model_dump(mode="json"),
            generated_response=response.generated_response,
            agent_output=agent_output,
        )
