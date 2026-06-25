from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

OptionalFilter = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class CustomerSummary(BaseModel):
    id: UUID
    name: str
    segment: str
    region: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class ProductSummary(BaseModel):
    id: UUID
    name: str
    category: str
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class SalesSummary(BaseModel):
    total_revenue: Decimal
    total_quantity: int
    number_of_sales: int
    unique_customers: int
    top_region: str | None
    top_channel: str | None


class DateRangeRequest(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRangeRequest":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date cannot be earlier than start_date")
        return self


class CustomerQueryRequest(BaseModel):
    run_id: UUID | None = None
    segment: OptionalFilter = None
    region: OptionalFilter = None
    status: OptionalFilter = None
    limit: int = Field(default=20, ge=1, le=100)


class SalesQueryRequest(DateRangeRequest):
    run_id: UUID | None = None
    customer_id: UUID | None = None
    region: OptionalFilter = None
    channel: OptionalFilter = None
    limit: int = Field(default=20, ge=1, le=100)


class SalesSummaryRequest(DateRangeRequest):
    run_id: UUID | None = None
    region: OptionalFilter = None
    channel: OptionalFilter = None


class SaleRecord(BaseModel):
    id: UUID
    customer_id: UUID
    product_id: UUID
    amount: Decimal
    quantity: int
    sold_at: datetime
    channel: str
    region: str

    model_config = ConfigDict(from_attributes=True)


class ToolExecutionResponse(BaseModel):
    tool_name: str
    tool_call_id: UUID | None = None
    results: list[CustomerSummary] | list[SaleRecord] | None = None
    summary: SalesSummary | None = None


ToolStatus = Literal["completed", "failed"]
JsonObject = dict[str, Any]
