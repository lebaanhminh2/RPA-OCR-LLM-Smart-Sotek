from datetime import UTC, datetime

from app.domain.models import CaseStatus, Document, DocumentOcrStatus
from app.domain.ports.ocr_provider import OCRProvider
from app.domain.ports.repository import Repository


class ExtractionService:
    def __init__(
        self,
        repository: Repository,
        ocr_provider: OCRProvider,
    ) -> None:
        self._repository = repository
        self._ocr_provider = ocr_provider

    def is_case_ready_for_ocr(self, case_id: str) -> bool:
        case = self._repository.get_case(case_id)
        return case is not None and case.status is CaseStatus.PROCESSING

    def process_case_ocr(self, case_id: str) -> None:
        if not self.is_case_ready_for_ocr(case_id):
            return

        any_failed = False
        documents = self._repository.list_documents_by_case_id(case_id)
        for document in documents:
            if document.ocr_status is not DocumentOcrStatus.PENDING:
                continue
            if not self._process_document(document):
                any_failed = True

        if any_failed:
            self._repository.update_case_status(
                case_id,
                CaseStatus.FAILED,
                datetime.now(UTC),
            )

    def _process_document(self, document: Document) -> bool:
        try:
            blocks = self._ocr_provider.extract(
                document.id,
                document.file_path,
            )
            self._repository.create_ocr_blocks(blocks)
            updated_document = self._repository.update_document_ocr_status(
                document.id,
                DocumentOcrStatus.DONE,
            )
            if updated_document is None:
                raise RuntimeError(
                    f"Document disappeared during OCR: {document.id}"
                )
        except Exception:
            failed_document = self._repository.update_document_ocr_status(
                document.id,
                DocumentOcrStatus.FAILED,
            )
            if failed_document is None:
                raise RuntimeError(
                    f"Unable to mark missing document as failed: {document.id}"
                )
            return False
        return True
