from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.documents.service import DocumentParsingService, parse_metadata_json
from app.rag.retrieval import RetrievalService, get_retrieval_service
from app.schemas.documents import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentMetadata,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSearchResult,
    ParsedDocumentResponse,
    ParsedIngestResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])
UploadFileInput = Annotated[UploadFile, File(...)]
OptionalTitleInput = Annotated[str | None, Form()]
OptionalMetadataInput = Annotated[str | None, Form()]
RetrievalServiceDependency = Annotated[
    RetrievalService,
    Depends(get_retrieval_service),
]


def get_document_parsing_service() -> DocumentParsingService:
    settings = get_settings()
    return DocumentParsingService(
        max_upload_bytes=settings.max_document_upload_bytes,
    )


DocumentParsingServiceDependency = Annotated[
    DocumentParsingService,
    Depends(get_document_parsing_service),
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


@router.post("/parse", response_model=ParsedDocumentResponse)
async def parse_document(
    parsing_service: DocumentParsingServiceDependency,
    file: UploadFileInput,
    title: OptionalTitleInput = None,
    metadata: OptionalMetadataInput = None,
) -> ParsedDocumentResponse:
    try:
        metadata_value = parse_metadata_json(metadata)
        content = await file.read()
        parsed = parsing_service.parse(
            filename=file.filename or "",
            content=content,
            content_type=file.content_type,
            title_override=title,
            metadata=metadata_value,
        )
    except ValueError as error:
        detail = str(error)
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        if "Unsupported document type" in detail:
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        raise HTTPException(status_code=status_code, detail=detail) from error

    return ParsedDocumentResponse(
        title=parsed.title,
        source=parsed.source,
        content_preview=parsed.content[:200],
        content_length=len(parsed.content),
        content_type=parsed.content_type,
        parser=parsed.parser,
        metadata=parsed.metadata,
    )


@router.post("/parse-ingest", response_model=ParsedIngestResponse)
async def parse_and_ingest_document(
    parsing_service: DocumentParsingServiceDependency,
    retrieval_service: RetrievalServiceDependency,
    file: UploadFileInput,
    title: OptionalTitleInput = None,
    metadata: OptionalMetadataInput = None,
) -> ParsedIngestResponse:
    try:
        metadata_value = parse_metadata_json(metadata)
        content = await file.read()
        parsed = parsing_service.parse(
            filename=file.filename or "",
            content=content,
            content_type=file.content_type,
            title_override=title,
            metadata=metadata_value,
        )
        ingest_metadata: DocumentMetadata = {
            key: value
            for key, value in parsed.metadata.items()
            if isinstance(value, (str, int, float, bool))
        }
        document_id, chunk_ids = retrieval_service.ingest(
            title=parsed.title,
            source=parsed.source,
            content=parsed.content,
            metadata=ingest_metadata,
        )
    except ValueError as error:
        detail = str(error)
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        if "Unsupported document type" in detail:
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        raise HTTPException(status_code=status_code, detail=detail) from error

    return ParsedIngestResponse(
        document_id=document_id,
        title=parsed.title,
        source=parsed.source,
        parser=parsed.parser,
        content_type=parsed.content_type,
        chunks_created=len(chunk_ids),
        chunk_ids=chunk_ids,
        status="indexed",
    )
