from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateAgentRunRequest(BaseModel):
    business_question: str = Field(min_length=1, max_length=10_000)


class AgentRunResponse(BaseModel):
    run_id: UUID = Field(validation_alias="id")
    status: str
    business_question: str
    summary: str | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
