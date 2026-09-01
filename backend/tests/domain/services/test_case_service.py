from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
)
from app.domain.services.case_service import (
    CaseNotFoundError,
    CaseService,
    DuplicateDocumentTypeError,
)

REQUIRED_DOCUMENT_TYPES = {
    DocumentType.CCCD_FRONT,
    DocumentType.CCCD_BACK,
    DocumentType.LOAN_APPLICATION,
    DocumentType.LABOR_CONTRACT,
}


class FakeRepository:
    def __init__(self) -> None:
        self.cases: dict[str, Case] = {}
        self.documents: list[Document] = []
        self.update_calls: list[tuple[str, CaseStatus, datetime]] = []

    def create_case(self, case: Case) -> Case:
        self.cases[case.id] = case
        return case

    def get_case(self, case_id: str) -> Case | None:
        return self.cases.get(case_id)

    def update_case_status(
        self,
        case_id: str,
        status: CaseStatus,
        updated_at: datetime,
    ) -> Case | None:
        case = self.cases.get(case_id)
        if case is None:
            return None

        updated_case = Case(
            id=case.id,
            status=status,
            created_at=case.created_at,
            updated_at=updated_at,
        )
        self.cases[case_id] = updated_case
        self.update_calls.append((case_id, status, updated_at))
        return updated_case

    def create_document(self, document: Document) -> Document:
        self.documents.append(document)
        return document

    def list_documents_by_case_id(self, case_id: str) -> list[Document]:
        return [
            document
            for document in self.documents
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
            for document in self.documents
        )


def test_create_case_sets_uuid_uploading_status_and_timestamps() -> None:
    repository = FakeRepository()
    service = CaseService(repository)
    before_creation = datetime.now(UTC)

    case = service.create_case()

    after_creation = datetime.now(UTC)
    parsed_id = UUID(case.id)
    assert parsed_id.version == 4
    assert str(parsed_id) == case.id
    assert case.status is CaseStatus.UPLOADING
    assert case.created_at == case.updated_at
    assert before_creation <= case.created_at <= after_creation
    assert repository.cases[case.id] == case


def test_get_case_returns_existing_case_without_mutation() -> None:
    repository = FakeRepository()
    service = CaseService(repository)
    case = service.create_case()
    original_state = (
        case.id,
        case.status,
        case.created_at,
        case.updated_at,
    )

    retrieved = service.get_case(case.id)

    assert retrieved == case
    assert retrieved.status is CaseStatus.UPLOADING
    assert (
        case.id,
        case.status,
        case.created_at,
        case.updated_at,
    ) == original_state


def test_get_case_raises_when_case_does_not_exist() -> None:
    repository = FakeRepository()
    service = CaseService(repository)

    with pytest.raises(CaseNotFoundError, match="Case not found: missing-case"):
        service.get_case("missing-case")


def test_add_first_document_sets_domain_data_and_keeps_case_uploading() -> None:
    repository = FakeRepository()
    service = CaseService(repository)
    case = service.create_case()
    before_upload = datetime.now(UTC)

    document = service.add_document(
        case.id,
        DocumentType.CCCD_FRONT,
        "uploads/case/cccd-front.pdf",
        1,
    )

    after_upload = datetime.now(UTC)
    parsed_id = UUID(document.id)
    assert parsed_id.version == 4
    assert str(parsed_id) == document.id
    assert document.case_id == case.id
    assert document.document_type is DocumentType.CCCD_FRONT
    assert document.file_path == "uploads/case/cccd-front.pdf"
    assert document.page_count == 1
    assert document.ocr_status is DocumentOcrStatus.PENDING
    assert before_upload <= document.uploaded_at <= after_upload
    assert repository.documents == [document]
    assert repository.cases[case.id].status is CaseStatus.UPLOADING
    assert repository.update_calls == []


def test_one_to_three_required_types_do_not_update_case_status() -> None:
    repository = FakeRepository()
    service = CaseService(repository)
    case = service.create_case()

    for index, document_type in enumerate(
        (
            DocumentType.CCCD_FRONT,
            DocumentType.CCCD_BACK,
            DocumentType.LOAN_APPLICATION,
        ),
        start=1,
    ):
        service.add_document(
            case.id,
            document_type,
            f"uploads/case/document-{index}.pdf",
            index,
        )

        assert repository.cases[case.id].status is CaseStatus.UPLOADING
        assert repository.update_calls == []


def test_all_four_required_types_transition_case_to_processing() -> None:
    repository = FakeRepository()
    service = CaseService(repository)
    case = service.create_case()
    before_additions = datetime.now(UTC)

    for index, document_type in enumerate(REQUIRED_DOCUMENT_TYPES, start=1):
        service.add_document(
            case.id,
            document_type,
            f"uploads/case/document-{index}.pdf",
            1,
        )

    after_additions = datetime.now(UTC)
    assert {
        document.document_type for document in repository.documents
    } == REQUIRED_DOCUMENT_TYPES
    assert repository.cases[case.id].status is CaseStatus.PROCESSING
    assert len(repository.update_calls) == 1
    updated_case_id, status, updated_at = repository.update_calls[0]
    assert updated_case_id == case.id
    assert status is CaseStatus.PROCESSING
    assert before_additions <= updated_at <= after_additions


def test_duplicate_document_type_is_rejected_before_persist_or_update() -> None:
    repository = FakeRepository()
    service = CaseService(repository)
    case = service.create_case()
    service.add_document(
        case.id,
        DocumentType.CCCD_FRONT,
        "uploads/case/cccd-front.pdf",
        1,
    )

    with pytest.raises(DuplicateDocumentTypeError):
        service.add_document(
            case.id,
            DocumentType.CCCD_FRONT,
            "uploads/case/duplicate-cccd-front.pdf",
            1,
        )

    assert len(repository.documents) == 1
    assert repository.cases[case.id].status is CaseStatus.UPLOADING
    assert repository.update_calls == []


def test_missing_case_is_rejected_before_document_creation_or_update() -> None:
    repository = FakeRepository()
    service = CaseService(repository)

    with pytest.raises(CaseNotFoundError):
        service.add_document(
            "missing-case",
            DocumentType.CCCD_FRONT,
            "uploads/missing/cccd-front.pdf",
            1,
        )

    assert repository.documents == []
    assert repository.update_calls == []


def test_four_records_without_all_required_types_do_not_transition() -> None:
    repository = FakeRepository()
    service = CaseService(repository)
    case = service.create_case()
    uploaded_at = datetime.now(UTC)
    repository.documents.extend(
        Document(
            id=f"inconsistent-{index}",
            case_id=case.id,
            document_type=DocumentType.CCCD_FRONT,
            file_path=f"uploads/case/inconsistent-{index}.pdf",
            page_count=1,
            ocr_status=DocumentOcrStatus.PENDING,
            uploaded_at=uploaded_at,
        )
        for index in range(3)
    )

    service.add_document(
        case.id,
        DocumentType.CCCD_BACK,
        "uploads/case/cccd-back.pdf",
        1,
    )

    assert len(repository.documents) == 4
    assert {
        document.document_type for document in repository.documents
    } == {
        DocumentType.CCCD_FRONT,
        DocumentType.CCCD_BACK,
    }
    assert repository.cases[case.id].status is CaseStatus.UPLOADING
    assert repository.update_calls == []
