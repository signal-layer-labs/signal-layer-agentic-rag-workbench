from app.documents.docling_parser import DoclingPdfParser
from app.documents.markdown_parser import MarkdownParser
from app.documents.text_parser import PlainTextParser
from app.documents.types import DocumentParser


def get_document_parsers() -> list[DocumentParser]:
    return [
        PlainTextParser(),
        MarkdownParser(),
        DoclingPdfParser(),
    ]
