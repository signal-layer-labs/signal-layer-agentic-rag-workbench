from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

MetadataValue = str | int | float | bool
DocumentMetadata = dict[str, MetadataValue]
NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class DocumentIngestRequest(BaseModel):
    title: NonBlankText
    source: NonBlankText
    content: NonBlankText
    metadata: DocumentMetadata = Field(default_factory=dict)


class DocumentIngestResponse(BaseModel):
    document_id: UUID
    title: str
    source: str
    chunks_created: int
    chunk_ids: list[str]
    status: str


class DocumentSearchRequest(BaseModel):
    query: NonBlankText
    limit: int = Field(default=5, ge=1, le=100)
    where: DocumentMetadata | None = None


class DocumentSearchResult(BaseModel):
    chunk_id: str
    document: str
    metadata: DocumentMetadata
    distance: float | None


class DocumentSearchResponse(BaseModel):
    query: str
    results: list[DocumentSearchResult]


class RunRetrievalRequest(BaseModel):
    query: NonBlankText
    limit: int = Field(default=5, ge=1, le=100)


class RunRetrievalResponse(BaseModel):
    run_id: UUID
    retrieval_event_id: UUID
    query: str
    results: list[DocumentSearchResult]
