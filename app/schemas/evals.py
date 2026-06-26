from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.schemas.documents import DocumentMetadata

NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class EvalDocument(BaseModel):
    title: NonBlankText
    source: NonBlankText
    content: NonBlankText
    metadata: DocumentMetadata = Field(default_factory=dict)


class EvalCase(BaseModel):
    id: NonBlankText
    name: NonBlankText
    business_question: NonBlankText = Field(max_length=10_000)
    documents: list[EvalDocument] = Field(default_factory=list)
    retrieval_query: NonBlankText | None = None
    expected_keywords: list[NonBlankText] = Field(default_factory=list)
    expected_source: NonBlankText | None = None
    sales_region: NonBlankText | None = None
    sales_channel: NonBlankText | None = None
    customer_segment: NonBlankText | None = None
    generate_response: bool = True

    @model_validator(mode="after")
    def validate_case(self) -> "EvalCase":
        if self.retrieval_query is not None and not self.expected_keywords:
            raise ValueError(
                "expected_keywords must be provided when retrieval_query is set."
            )
        return self


class RetrievalEvalResult(BaseModel):
    retrieved_count: int
    expected_source_found: bool
    expected_keywords_found: bool
    missing_keywords: list[str]
    passed: bool


class ResponseEvalResult(BaseModel):
    generated: bool
    contains_business_question: bool
    contains_sales_summary: bool
    unsupported_claim_flags: list[str]
    passed: bool


class TraceEvalResult(BaseModel):
    run_created: bool
    retrieval_event_created: bool
    tool_calls_created: bool
    passed: bool


class OverallEvalResult(BaseModel):
    case_id: str
    name: str
    retrieval: RetrievalEvalResult
    response: ResponseEvalResult
    trace: TraceEvalResult
    passed: bool


class EvalRunReport(BaseModel):
    total: int
    passed: int
    failed: int
    results: list[OverallEvalResult]
