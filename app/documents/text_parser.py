from pathlib import Path

from app.documents.types import DocumentParser, ParsedDocument


class PlainTextParser(DocumentParser):
    def supports(self, filename: str, content_type: str | None) -> bool:
        return Path(filename).suffix.lower() == ".txt"

    def parse(
        self,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> ParsedDocument:
        text = content.decode("utf-8").strip()
        if not text:
            raise ValueError("Parsed document content cannot be blank.")
        path = Path(filename)
        return ParsedDocument(
            title=path.stem or filename,
            source=filename,
            content=text,
            content_type=content_type or "text/plain",
            parser="text",
            metadata={"original_filename": filename},
        )
