from dataclasses import fields
from datetime import UTC, datetime

from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
)


def test_case_preserves_supplied_values_and_has_exact_fields() -> None:
    created_at = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
    updated_at = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)

    case = Case(
        id="case-001",
        status=CaseStatus.PROCESSING,
        created_at=created_at,
        updated_at=updated_at,
    )

    assert case.id == "case-001"
    assert case.status is CaseStatus.PROCESSING
    assert case.created_at is created_at
    assert case.updated_at is updated_at
    assert [field.name for field in fields(Case)] == [
        "id",
        "status",
        "created_at",
        "updated_at",
    ]


def test_document_preserves_supplied_values_and_has_exact_fields() -> None:
    uploaded_at = datetime(2026, 9, 1, 8, 30, tzinfo=UTC)

    document = Document(
        id="document-001",
        case_id="case-001",
        document_type=DocumentType.CCCD_FRONT,
        file_path="uploads/case-001/cccd-front.pdf",
        page_count=1,
        ocr_status=DocumentOcrStatus.PENDING,
        uploaded_at=uploaded_at,
    )

    assert document.id == "document-001"
    assert document.case_id == "case-001"
    assert document.document_type is DocumentType.CCCD_FRONT
    assert document.file_path == "uploads/case-001/cccd-front.pdf"
    assert document.page_count == 1
    assert document.ocr_status is DocumentOcrStatus.PENDING
    assert document.uploaded_at is uploaded_at
    assert [field.name for field in fields(Document)] == [
        "id",
        "case_id",
        "document_type",
        "file_path",
        "page_count",
        "ocr_status",
        "uploaded_at",
    ]


def test_case_status_has_exact_names_and_values() -> None:
    assert [(member.name, member.value) for member in CaseStatus] == [
        ("UPLOADING", "UPLOADING"),
        ("PROCESSING", "PROCESSING"),
        ("READY_FOR_REVIEW", "READY_FOR_REVIEW"),
        ("COMPLETED", "COMPLETED"),
        ("FAILED", "FAILED"),
    ]


def test_document_type_has_exact_names_and_values() -> None:
    assert [(member.name, member.value) for member in DocumentType] == [
        ("CCCD_FRONT", "CCCD_FRONT"),
        ("CCCD_BACK", "CCCD_BACK"),
        ("LOAN_APPLICATION", "LOAN_APPLICATION"),
        ("LABOR_CONTRACT", "LABOR_CONTRACT"),
    ]


def test_document_ocr_status_has_exact_names_and_values() -> None:
    assert [(member.name, member.value) for member in DocumentOcrStatus] == [
        ("PENDING", "PENDING"),
        ("DONE", "DONE"),
        ("FAILED", "FAILED"),
    ]
