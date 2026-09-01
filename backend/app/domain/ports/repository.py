from datetime import datetime
from typing import Protocol

from app.domain.models import Case, CaseStatus, Document, DocumentType


class Repository(Protocol):
    def create_case(self, case: Case) -> Case: ...

    def get_case(self, case_id: str) -> Case | None: ...

    def update_case_status(
        self,
        case_id: str,
        status: CaseStatus,
        updated_at: datetime,
    ) -> Case | None: ...

    def create_document(self, document: Document) -> Document: ...

    def get_document(self, document_id: str) -> Document | None: ...

    def list_documents_by_case_id(self, case_id: str) -> list[Document]: ...

    def document_type_exists(
        self,
        case_id: str,
        document_type: DocumentType,
    ) -> bool: ...
