from dataclasses import replace
from datetime import UTC, datetime, timedelta

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
    ReviewAction,
    ReviewActionType,
)
from app.domain.ports.repository import (
    ExtractedFieldWithSources,
    FieldSourceEvidence,
)
from app.domain.services.case_service import CaseNotFoundError
from app.domain.services.review_service import (
    CaseNotReadyForReviewError,
    ExtractedFieldNotFoundError,
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
        self.actions: list[ReviewAction] = []
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

    def get_extracted_field(
        self,
        extracted_field_id: str,
    ) -> ExtractedField | None:
        return next(
            (
                item.field
                for item in self.fields
                if item.field.id == extracted_field_id
            ),
            None,
        )

    def create_review_action(self, action: ReviewAction) -> ReviewAction:
        self.actions.append(action)
        return action

    def list_review_actions_by_case_id(
        self,
        case_id: str,
    ) -> list[ReviewAction]:
        return [action for action in self.actions if action.case_id == case_id]

    def update_extracted_field_with_action(
        self,
        extracted_field_id: str,
        current_value: str | None,
        updated_at: datetime,
        action: ReviewAction,
    ) -> tuple[ExtractedField, ReviewAction] | None:
        for index, item in enumerate(self.fields):
            if item.field.id != extracted_field_id:
                continue
            updated_field = replace(
                item.field,
                current_value=current_value,
                updated_at=updated_at,
            )
            self.fields[index] = replace(item, field=updated_field)
            self.actions.append(action)
            return updated_field, action
        return None

    def complete_case_with_action(
        self,
        case_id: str,
        updated_at: datetime,
        action: ReviewAction,
    ) -> tuple[Case, ReviewAction] | None:
        if self.case is None or self.case.id != case_id:
            return None
        self.case = replace(
            self.case,
            status=CaseStatus.COMPLETED,
            updated_at=updated_at,
        )
        self.actions.append(action)
        return self.case, action


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


def test_update_field_preserves_original_and_audits_every_edit() -> None:
    timestamp = datetime(2026, 9, 2, 11, 0, tzinfo=UTC)
    repository = FakeRepository(
        make_case(CaseStatus.READY_FOR_REVIEW),
        [make_review_field("ho_ten", "NGUYEN VAN A")],
    )
    action_ids = iter(["action-001", "action-002"])
    clock_values = iter([timestamp, timestamp + timedelta(minutes=1)])
    service = ReviewService(
        repository,
        clock=lambda: next(clock_values),
        id_factory=lambda: next(action_ids),
    )

    first_update = service.update_field(
        "case-001",
        "field-ho_ten",
        "Nguyễn Văn A",
    )
    second_update = service.update_field(
        "case-001",
        "field-ho_ten",
        "Nguyễn Văn Anh",
    )

    assert first_update.original_value == "NGUYEN VAN A"
    assert first_update.current_value == "Nguyễn Văn A"
    assert second_update.original_value == "NGUYEN VAN A"
    assert second_update.current_value == "Nguyễn Văn Anh"
    assert len(repository.fields) == 1
    assert [action.action_type for action in repository.actions] == [
        ReviewActionType.EDIT_FIELD,
        ReviewActionType.EDIT_FIELD,
    ]
    assert [
        (action.previous_value, action.new_value)
        for action in repository.actions
    ] == [
        ("NGUYEN VAN A", "Nguyễn Văn A"),
        ("Nguyễn Văn A", "Nguyễn Văn Anh"),
    ]


def test_update_field_normalizes_monetary_value_and_audits_canonical_value() -> None:
    timestamp = datetime(2026, 9, 2, 11, 0, tzinfo=UTC)
    repository = FakeRepository(
        make_case(CaseStatus.READY_FOR_REVIEW),
        [make_review_field("muc_luong_gross", "40.000.000")],
    )
    service = ReviewService(
        repository,
        clock=lambda: timestamp,
        id_factory=lambda: "action-money",
    )

    updated = service.update_field(
        "case-001",
        "field-muc_luong_gross",
        "15 triệu",
    )

    assert updated.current_value == "15.000.000"
    assert repository.actions[0].previous_value == "40.000.000"
    assert repository.actions[0].new_value == "15.000.000"


def test_update_field_rejects_missing_or_cross_case_field() -> None:
    repository = FakeRepository(
        make_case(CaseStatus.READY_FOR_REVIEW),
        [make_review_field("ho_ten", "NGUYỄN VĂN AN")],
    )
    service = ReviewService(repository)

    with pytest.raises(ExtractedFieldNotFoundError, match="missing-field"):
        service.update_field("case-001", "missing-field", "New value")

    repository.fields[0] = replace(
        repository.fields[0],
        field=replace(repository.fields[0].field, case_id="other-case"),
    )
    with pytest.raises(ExtractedFieldNotFoundError, match="field-ho_ten"):
        service.update_field("case-001", "field-ho_ten", "New value")

    assert repository.actions == []


def test_update_field_rejects_case_not_ready() -> None:
    repository = FakeRepository(
        make_case(CaseStatus.COMPLETED),
        [make_review_field("ho_ten", "NGUYỄN VĂN AN")],
    )

    with pytest.raises(CaseNotReadyForReviewError) as error:
        ReviewService(repository).update_field(
            "case-001",
            "field-ho_ten",
            "New value",
        )

    assert error.value.case_status is CaseStatus.COMPLETED
    assert repository.actions == []


def test_upload_case_completes_ready_case_and_records_one_action() -> None:
    completed_at = datetime(2026, 9, 2, 11, 30, tzinfo=UTC)
    repository = FakeRepository(
        make_case(CaseStatus.READY_FOR_REVIEW),
        [],
    )
    service = ReviewService(
        repository,
        clock=lambda: completed_at,
        id_factory=lambda: "action-upload",
    )

    completed_case = service.upload_case("case-001")

    assert completed_case.status is CaseStatus.COMPLETED
    assert completed_case.updated_at == completed_at
    assert repository.actions == [
        ReviewAction(
            id="action-upload",
            case_id="case-001",
            extracted_field_id=None,
            action_type=ReviewActionType.UPLOAD_CASE,
            previous_value=None,
            new_value=None,
            created_at=completed_at,
        )
    ]


@pytest.mark.parametrize(
    "status",
    [CaseStatus.UPLOADING, CaseStatus.PROCESSING, CaseStatus.COMPLETED],
)
def test_upload_case_rejects_case_not_ready(status: CaseStatus) -> None:
    repository = FakeRepository(make_case(status), [])

    with pytest.raises(CaseNotReadyForReviewError) as error:
        ReviewService(repository).upload_case("case-001")

    assert error.value.case_status is status
    assert repository.case is not None
    assert repository.case.status is status
    assert repository.actions == []
