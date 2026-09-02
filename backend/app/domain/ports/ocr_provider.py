from typing import Protocol

from app.domain.models import DocumentType, OCRBlock


class OCRProvider(Protocol):
    def extract(
        self,
        document_id: str,
        document_type: DocumentType,
        file_path: str,
    ) -> list[OCRBlock]: ...
