from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.rag.retrieval import RetrievalService, get_retrieval_service
from app.schemas.documents import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSearchResult,
)

router = APIRouter(prefix="/documents", tags=["documents"])
RetrievalServiceDependency = Annotated[
    RetrievalService,
    Depends(get_retrieval_service),
]


@router.post("/ingest", response_model=DocumentIngestResponse)
def ingest_document(
    request: DocumentIngestRequest,
    service: RetrievalServiceDependency,
) -> DocumentIngestResponse:
    try:
        document_id, chunk_ids = service.ingest(
            title=request.title,
            source=request.source,
            content=request.content,
            metadata=request.metadata,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return DocumentIngestResponse(
        document_id=document_id,
        title=request.title,
        source=request.source,
        chunks_created=len(chunk_ids),
        chunk_ids=chunk_ids,
        status="indexed",
    )


@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(
    request: DocumentSearchRequest,
    service: RetrievalServiceDependency,
) -> DocumentSearchResponse:
    results = service.search(request.query, request.limit, request.where)
    return DocumentSearchResponse(
        query=request.query,
        results=[
            DocumentSearchResult(
                chunk_id=result.chunk_id,
                document=result.document,
                metadata=result.metadata,
                distance=result.distance,
            )
            for result in results
        ],
    )
