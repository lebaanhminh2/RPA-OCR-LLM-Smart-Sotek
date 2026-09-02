from dataclasses import dataclass
from typing import Protocol

from app.domain.models import DocumentType, OCRBlock


@dataclass(frozen=True)
class LLMDocumentInput:
    document_id: str
    document_type: DocumentType
    blocks: list[OCRBlock]


@dataclass(frozen=True)
class LLMExtractedField:
    field_code: str
    value: str | None
    source_ids: list[str]


class LLMProvider(Protocol):
    def extract(
        self,
        documents: list[LLMDocumentInput],
    ) -> list[LLMExtractedField]: ...
