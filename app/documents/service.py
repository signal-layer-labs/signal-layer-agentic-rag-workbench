import json
from collections.abc import Mapping

from app.documents.parser import get_document_parsers
from app.documents.types import DocumentParser, ParsedDocument, ParsedMetadata
from app.schemas.documents import DocumentMetadata


class DocumentParsingService:
    def __init__(
        self,
        parsers: list[DocumentParser] | None = None,
        max_upload_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self.parsers = parsers or get_document_parsers()
        self.max_upload_bytes = max_upload_bytes

    def parse(
        self,
        filename: str,
        content: bytes,
        *,
        content_type: str | None = None,
        title_override: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ParsedDocument:
        if not filename:
            raise ValueError("Uploaded filename is required.")
        if len(content) > self.max_upload_bytes:
            raise ValueError("Uploaded file exceeds the maximum allowed size.")

        parser = next(
            (
                parser
                for parser in self.parsers
                if parser.supports(filename, content_type)
            ),
            None,
        )
        if parser is None:
            raise ValueError("Unsupported document type for parsing.")

        parsed = parser.parse(filename, content, content_type)
        if not parsed.content.strip():
            raise ValueError("Parsed document content cannot be blank.")

        merged_metadata: ParsedMetadata = {
            **parsed.metadata,
            "original_filename": filename,
            "parser": parsed.parser,
        }
        if content_type:
            merged_metadata["content_type"] = content_type
        if metadata:
            merged_metadata.update(dict(metadata))
        if title_override is not None:
            stripped_title = title_override.strip()
            if not stripped_title:
                raise ValueError("Title override cannot be blank.")
            merged_metadata["title_override"] = stripped_title
            parsed.title = stripped_title
        parsed.metadata = merged_metadata
        return parsed


def parse_metadata_json(value: str | None) -> DocumentMetadata:
    if value is None or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("Malformed metadata JSON.") from error
    if not isinstance(parsed, dict):
        raise ValueError("Metadata must be a JSON object.")
    if not all(isinstance(key, str) for key in parsed):
        raise ValueError("Metadata keys must be strings.")
    validated: DocumentMetadata = {}
    for key, item in parsed.items():
        if not isinstance(item, (str, int, float, bool)):
            raise ValueError("Metadata values must be string, number, or boolean.")
        validated[key] = item
    return validated
