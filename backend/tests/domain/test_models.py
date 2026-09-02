from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime

import pytest

from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
    OCRBlock,
    OCRBlockKind,
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


def test_ocr_block_preserves_supplied_values_and_has_exact_fields() -> None:
    created_at = datetime(2026, 9, 2, 8, 0, tzinfo=UTC)

    ocr_block = OCRBlock(
        id="ocr-block-1",
        document_id="document-1",
        page_number=1,
        text="NGUYEN VAN A",
        bbox_x=0.12,
        bbox_y=0.34,
        bbox_width=0.30,
        bbox_height=0.04,
        confidence=0.97,
        created_at=created_at,
    )

    assert ocr_block.id == "ocr-block-1"
    assert ocr_block.document_id == "document-1"
    assert ocr_block.page_number == 1
    assert ocr_block.text == "NGUYEN VAN A"
    assert ocr_block.bbox_x == 0.12
    assert ocr_block.bbox_y == 0.34
    assert ocr_block.bbox_width == 0.30
    assert ocr_block.bbox_height == 0.04
    assert ocr_block.confidence == 0.97
    assert ocr_block.created_at is created_at
    assert ocr_block.block_kind is OCRBlockKind.TEXT
    assert isinstance(ocr_block.page_number, int)
    assert isinstance(ocr_block.bbox_x, float)
    assert isinstance(ocr_block.bbox_y, float)
    assert isinstance(ocr_block.bbox_width, float)
    assert isinstance(ocr_block.bbox_height, float)
    assert isinstance(ocr_block.confidence, float)
    assert not hasattr(ocr_block, "source_id")
    assert [field.name for field in fields(OCRBlock)] == [
        "id",
        "document_id",
        "page_number",
        "text",
        "bbox_x",
        "bbox_y",
        "bbox_width",
        "bbox_height",
        "confidence",
        "created_at",
        "block_kind",
    ]


def test_ocr_block_is_immutable() -> None:
    ocr_block = OCRBlock(
        id="ocr-block-1",
        document_id="document-1",
        page_number=1,
        text="NGUYEN VAN A",
        bbox_x=0.12,
        bbox_y=0.34,
        bbox_width=0.30,
        bbox_height=0.04,
        confidence=0.97,
        created_at=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
    )

    with pytest.raises(FrozenInstanceError):
        setattr(ocr_block, "bbox_x", 0.5)


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


def test_ocr_block_kind_has_exact_names_and_values() -> None:
    assert [(member.name, member.value) for member in OCRBlockKind] == [
        ("TEXT", "TEXT"),
        ("CHECKBOX_SELECTION", "CHECKBOX_SELECTION"),
    ]
