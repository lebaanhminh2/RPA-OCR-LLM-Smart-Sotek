from datetime import UTC, datetime

import pytest

from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
    ExtractedField,
    FieldSource,
    OCRBlock,
)
from app.domain.ports.repository import (
    ExtractedFieldWithSources,
    FieldSourceEvidence,
)
from app.domain.services.case_service import CaseNotFoundError
from app.domain.services.review_service import (
    CaseNotReadyForReviewError,
    ReviewService,
)


class FakeRepository:
    def __init__(
        self,
        case: Case | None,
        fields: list[ExtractedFieldWithSources],
    ) -> None:
        self.case = case
        self.fields = fields
        self.review_reads = 0

    def create_case(self, case: Case) -> Case:
        raise AssertionError("Not used by ReviewService")

    def get_case(self, case_id: str) -> Case | None:
        if self.case is not None and self.case.id == case_id:
            return self.case
        return None

    def update_case_status(
        self,
        case_id: str,
        status: CaseStatus,
        updated_at: datetime,
    ) -> Case | None:
        raise AssertionError("Not used by ReviewService")

    def create_document(self, document: Document) -> Document:
        raise AssertionError("Not used by ReviewService")

    def get_document(self, document_id: str) -> Document | None:
        raise AssertionError("Not used by ReviewService")

    def update_document_ocr_status(
        self,
        document_id: str,
        status: DocumentOcrStatus,
    ) -> Document | None:
        raise AssertionError("Not used by ReviewService")

    def list_documents_by_case_id(self, case_id: str) -> list[Document]:
        raise AssertionError("Not used by ReviewService")

    def document_type_exists(
        self,
        case_id: str,
        document_type: DocumentType,
    ) -> bool:
        raise AssertionError("Not used by ReviewService")

    def create_ocr_blocks(self, blocks: list[OCRBlock]) -> list[OCRBlock]:
        raise AssertionError("Not used by ReviewService")

    def list_ocr_blocks_by_document_id(
        self,
        document_id: str,
    ) -> list[OCRBlock]:
        raise AssertionError("Not used by ReviewService")

    def create_extracted_fields(
        self,
        fields: list[ExtractedField],
        sources: list[FieldSource],
    ) -> tuple[list[ExtractedField], list[FieldSource]]:
        raise AssertionError("Not used by ReviewService")

    def list_extracted_fields_with_sources_by_case_id(
        self,
        case_id: str,
    ) -> list[ExtractedFieldWithSources]:
        self.review_reads += 1
        return list(self.fields)


def make_case(status: CaseStatus) -> Case:
    timestamp = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
    return Case(
        id="case-001",
        status=status,
        created_at=timestamp,
        updated_at=timestamp,
    )


def make_review_field(
    field_code: str,
    value: str | None,
    *,
    with_source: bool = False,
) -> ExtractedFieldWithSources:
    timestamp = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
    field = ExtractedField(
        id=f"field-{field_code}",
        case_id="case-001",
        field_code=field_code,
        original_value=value,
        current_value=value,
        created_at=timestamp,
        updated_at=timestamp,
    )
    if not with_source:
        return ExtractedFieldWithSources(field=field, sources=())

    block = OCRBlock(
        id="ocr-ho-ten",
        document_id="document-front",
        page_number=1,
        text="Họ và tên: NGUYỄN VĂN AN",
        bbox_x=0.1,
        bbox_y=0.2,
        bbox_width=0.4,
        bbox_height=0.05,
        confidence=0.98,
        created_at=timestamp,
    )
    source = FieldSource(
        id="source-ho-ten",
        extracted_field_id=field.id,
        ocr_block_id=block.id,
    )
    return ExtractedFieldWithSources(
        field=field,
        sources=(FieldSourceEvidence(source, block),),
    )


@pytest.mark.parametrize(
    "status",
    [CaseStatus.READY_FOR_REVIEW, CaseStatus.COMPLETED],
)
def test_get_case_review_returns_fields_in_catalog_order(
    status: CaseStatus,
) -> None:
    email = make_review_field("email", None)
    full_name = make_review_field(
        "ho_ten",
        "NGUYỄN VĂN AN",
        with_source=True,
    )
    repository = FakeRepository(make_case(status), [email, full_name])
    service = ReviewService(repository)

    review = service.get_case_review("case-001")

    assert review.case_id == "case-001"
    assert review.status is status
    assert [item.field.field_code for item in review.fields] == [
        "ho_ten",
        "email",
    ]
    assert review.fields[0].sources[0].ocr_block.id == "ocr-ho-ten"
    assert repository.review_reads == 1


def test_get_case_review_reports_processing_status_without_reading_fields() -> None:
    repository = FakeRepository(make_case(CaseStatus.PROCESSING), [])
    service = ReviewService(repository)

    with pytest.raises(CaseNotReadyForReviewError) as error:
        service.get_case_review("case-001")

    assert error.value.case_status is CaseStatus.PROCESSING
    assert repository.review_reads == 0


def test_get_case_review_reports_missing_case() -> None:
    service = ReviewService(FakeRepository(None, []))

    with pytest.raises(CaseNotFoundError, match="missing-case"):
        service.get_case_review("missing-case")
