from typing import Protocol

from app.domain.models import OCRBlock


class OCRProvider(Protocol):
    def extract(
        self,
        document_id: str,
        file_path: str,
    ) -> list[OCRBlock]: ...
