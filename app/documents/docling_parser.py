from app.documents.types import DocumentParser, ParsedDocument

try:
    import docling  # type: ignore[import-not-found,unused-ignore]
except ImportError:
    docling = None


class DoclingPdfParser(DocumentParser):
    def supports(self, filename: str, content_type: str | None) -> bool:
        return filename.lower().endswith(".pdf")

    def parse(
        self,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> ParsedDocument:
        if docling is None:
            raise ValueError(
                "PDF parsing through Docling is not wired in this environment yet."
            )
        raise ValueError(
            "PDF parsing through Docling is not wired in this environment yet."
        )
