from collections.abc import Mapping
from typing import Protocol

ParsedMetadata = dict[str, object]


class ParsedDocument:
    def __init__(
        self,
        title: str,
        source: str,
        content: str,
        content_type: str,
        parser: str,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        self.title = title
        self.source = source
        self.content = content
        self.content_type = content_type
        self.parser = parser
        self.metadata = dict(metadata or {})


class DocumentParser(Protocol):
    def supports(self, filename: str, content_type: str | None) -> bool: ...

    def parse(
        self,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> ParsedDocument: ...
