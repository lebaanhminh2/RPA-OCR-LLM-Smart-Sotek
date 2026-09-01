from datetime import UTC, datetime
from uuid import uuid4

from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
)
from app.domain.ports.repository import Repository

_REQUIRED_DOCUMENT_TYPES = frozenset(
    {
        DocumentType.CCCD_FRONT,
        DocumentType.CCCD_BACK,
        DocumentType.LOAN_APPLICATION,
        DocumentType.LABOR_CONTRACT,
    }
)


class CaseNotFoundError(Exception):
    def __init__(self, case_id: str) -> None:
        super().__init__(f"Case not found: {case_id}")


class DuplicateDocumentTypeError(Exception):
    def __init__(self, case_id: str, document_type: DocumentType) -> None:
        super().__init__(
            f"Document type {document_type.value} already exists "
            f"for case {case_id}"
        )


class CaseService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def create_case(self) -> Case:
        created_at = datetime.now(UTC)
        case = Case(
            id=str(uuid4()),
            status=CaseStatus.UPLOADING,
            created_at=created_at,
            updated_at=created_at,
        )
        return self._repository.create_case(case)

    def get_case(self, case_id: str) -> Case:
        case = self._repository.get_case(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)
        return case

    def add_document(
        self,
        case_id: str,
        document_type: DocumentType,
        file_path: str,
        page_count: int,
    ) -> Document:
        case = self._repository.get_case(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)

        if self._repository.document_type_exists(case_id, document_type):
            raise DuplicateDocumentTypeError(case_id, document_type)

        document = Document(
            id=str(uuid4()),
            case_id=case_id,
            document_type=document_type,
            file_path=file_path,
            page_count=page_count,
            ocr_status=DocumentOcrStatus.PENDING,
            uploaded_at=datetime.now(UTC),
        )
        created_document = self._repository.create_document(document)

        documents = self._repository.list_documents_by_case_id(case_id)
        document_types = frozenset(
            existing_document.document_type
            for existing_document in documents
        )
        if (
            case.status is CaseStatus.UPLOADING
            and document_types == _REQUIRED_DOCUMENT_TYPES
        ):
            self._repository.update_case_status(
                case_id,
                CaseStatus.PROCESSING,
                datetime.now(UTC),
            )

        return created_document
