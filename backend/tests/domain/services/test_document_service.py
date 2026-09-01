from datetime import datetime

import pytest

from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
)
from app.domain.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
)


class FakeRepository:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = {document.id: document for document in documents}

    def create_case(self, case: Case) -> Case:
        return case

    def get_case(self, case_id: str) -> Case | None:
        return None

    def update_case_status(
        self,
        case_id: str,
        status: CaseStatus,
        updated_at: datetime,
    ) -> Case | None:
        return None

    def create_document(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    def get_document(self, document_id: str) -> Document | None:
        return self.documents.get(document_id)

    def list_documents_by_case_id(self, case_id: str) -> list[Document]:
        return [
            document
            for document in self.documents.values()
            if document.case_id == case_id
        ]

    def document_type_exists(
        self,
        case_id: str,
        document_type: DocumentType,
    ) -> bool:
        return any(
            document.case_id == case_id
            and document.document_type is document_type
            for document in self.documents.values()
        )


def make_document() -> Document:
    return Document(
        id="document-001",
        case_id="case-001",
        document_type=DocumentType.CCCD_FRONT,
        file_path="uploads/document-001.png",
        page_count=1,
        ocr_status=DocumentOcrStatus.PENDING,
        uploaded_at=datetime(2026, 9, 1, 12, 0),
    )


def test_get_document_returns_existing_domain_document() -> None:
    document = make_document()
    service = DocumentService(FakeRepository([document]))

    assert service.get_document(document.id) == document


def test_get_document_raises_when_document_does_not_exist() -> None:
    service = DocumentService(FakeRepository([]))

    with pytest.raises(
        DocumentNotFoundError,
        match="Document not found: missing-document",
    ):
        service.get_document("missing-document")
