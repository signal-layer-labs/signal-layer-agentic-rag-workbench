from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _normalize_optional_text(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


class QueryCustomersToolInput(BaseModel):
    segment: str | None = None
    region: str | None = None
    status: str | None = None
    limit: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def normalize_optional_values(
        cls,
        data: Any,
    ) -> Any:
        if not isinstance(data, dict):
            return data
        return {
            key: _normalize_optional_text(value)
            for key, value in data.items()
        }


class SummarizeSalesToolInput(BaseModel):
    region: str | None = None
    channel: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def normalize_optional_values(
        cls,
        data: Any,
    ) -> Any:
        if not isinstance(data, dict):
            return data
        return {
            key: _normalize_optional_text(value)
            for key, value in data.items()
        }

    @model_validator(mode="after")
    def validate_date_range(self) -> "SummarizeSalesToolInput":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date cannot be earlier than start_date")
        return self


class RunTraceableWorkflowInput(BaseModel):
    business_question: str
    retrieval_query: str | None = None
    sales_region: str | None = None
    sales_channel: str | None = None
    customer_segment: str | None = None
    generate_response: bool = False

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def normalize_optional_values(
        cls,
        data: Any,
    ) -> Any:
        if not isinstance(data, dict):
            return data
        normalized: dict[str, Any] = {}
        for key, value in data.items():
            if key == "business_question" and isinstance(value, str):
                normalized[key] = value.strip()
            else:
                normalized[key] = _normalize_optional_text(value)
        business_question = normalized.get("business_question")
        if isinstance(business_question, str):
            normalized["business_question"] = business_question.strip()
        return normalized

    @model_validator(mode="after")
    def validate_business_question(self) -> "RunTraceableWorkflowInput":
        if not self.business_question.strip():
            raise ValueError("business_question cannot be blank")
        self.business_question = self.business_question.strip()
        return self
