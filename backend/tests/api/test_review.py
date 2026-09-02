from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.review import create_review_router
from app.domain.models import (
    Case,
    CaseStatus,
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
    CaseReview,
    ExtractedFieldNotFoundError,
    ReviewService,
)


class FakeReviewService(ReviewService):
    def __init__(
        self,
        review: CaseReview | None = None,
        error: Exception | None = None,
        updated_field: ExtractedField | None = None,
        uploaded_case: Case | None = None,
    ) -> None:
        self.review = review
        self.error = error
        self.updated_field = updated_field
        self.uploaded_case = uploaded_case
        self.update_call: tuple[str, str, str | None] | None = None
        self.upload_call: str | None = None

    def get_case_review(self, case_id: str) -> CaseReview:
        if self.error is not None:
            raise self.error
        if self.review is None:
            raise AssertionError("Test must configure a review or error")
        return self.review

    def update_field(
        self,
        case_id: str,
        extracted_field_id: str,
        current_value: str | None,
    ) -> ExtractedField:
        self.update_call = (case_id, extracted_field_id, current_value)
        if self.error is not None:
            raise self.error
        if self.updated_field is None:
            raise AssertionError("Test must configure an updated field or error")
        return self.updated_field

    def upload_case(self, case_id: str) -> Case:
        self.upload_call = case_id
        if self.error is not None:
            raise self.error
        if self.uploaded_case is None:
            raise AssertionError("Test must configure an uploaded case or error")
        return self.uploaded_case


def make_review() -> CaseReview:
    timestamp = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
    field = ExtractedField(
        id="field-ho-ten",
        case_id="case-001",
        field_code="ho_ten",
        original_value="NGUYỄN VĂN AN",
        current_value="NGUYỄN VĂN AN",
        created_at=timestamp,
        updated_at=timestamp,
    )
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
    return CaseReview(
        case_id="case-001",
        status=CaseStatus.READY_FOR_REVIEW,
        fields=(
            ExtractedFieldWithSources(
                field=field,
                sources=(FieldSourceEvidence(source, block),),
            ),
        ),
    )


def make_client(service: ReviewService) -> TestClient:
    app = FastAPI()
    app.include_router(create_review_router(service))
    return TestClient(app)


def test_get_review_returns_field_and_highlight_source() -> None:
    with make_client(FakeReviewService(review=make_review())) as client:
        response = client.get("/cases/case-001/review")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": "case-001",
        "status": "READY_FOR_REVIEW",
        "fields": [
            {
                "id": "field-ho-ten",
                "case_id": "case-001",
                "field_code": "ho_ten",
                "original_value": "NGUYỄN VĂN AN",
                "current_value": "NGUYỄN VĂN AN",
                "sources": [
                    {
                        "ocr_block_id": "ocr-ho-ten",
                        "document_id": "document-front",
                        "page_number": 1,
                        "bbox_x": 0.1,
                        "bbox_y": 0.2,
                        "bbox_width": 0.4,
                        "bbox_height": 0.05,
                    }
                ],
            }
        ],
    }


def test_get_review_returns_conflict_with_current_case_status() -> None:
    error = CaseNotReadyForReviewError(
        "case-001",
        CaseStatus.PROCESSING,
    )
    with make_client(FakeReviewService(error=error)) as client:
        response = client.get("/cases/case-001/review")

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "message": "Case case-001 is not ready for review: PROCESSING",
            "case_status": "PROCESSING",
        }
    }


def test_get_review_returns_not_found_for_unknown_case() -> None:
    with make_client(
        FakeReviewService(error=CaseNotFoundError("missing-case"))
    ) as client:
        response = client.get("/cases/missing-case/review")

    assert response.status_code == 404
    assert response.json() == {"detail": "Case not found: missing-case"}


def test_patch_field_returns_updated_current_value() -> None:
    field = make_review().fields[0].field
    updated_field = ExtractedField(
        id=field.id,
        case_id=field.case_id,
        field_code=field.field_code,
        original_value=field.original_value,
        current_value="Nguyễn Văn Anh",
        created_at=field.created_at,
        updated_at=datetime(2026, 9, 2, 10, 30, tzinfo=UTC),
    )
    service = FakeReviewService(updated_field=updated_field)

    with make_client(service) as client:
        response = client.patch(
            "/cases/case-001/fields/field-ho-ten",
            json={"current_value": "Nguyễn Văn Anh"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": "field-ho-ten",
        "case_id": "case-001",
        "field_code": "ho_ten",
        "original_value": "NGUYỄN VĂN AN",
        "current_value": "Nguyễn Văn Anh",
    }
    assert service.update_call == (
        "case-001",
        "field-ho-ten",
        "Nguyễn Văn Anh",
    )


def test_patch_field_returns_not_found_for_unknown_field() -> None:
    error = ExtractedFieldNotFoundError("case-001", "missing-field")
    with make_client(FakeReviewService(error=error)) as client:
        response = client.patch(
            "/cases/case-001/fields/missing-field",
            json={"current_value": None},
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Extracted field not found in case case-001: missing-field"
    }


def test_upload_case_returns_completed_case() -> None:
    timestamp = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
    completed_at = datetime(2026, 9, 2, 10, 45, tzinfo=UTC)
    completed_case = Case(
        id="case-001",
        status=CaseStatus.COMPLETED,
        created_at=timestamp,
        updated_at=completed_at,
    )
    service = FakeReviewService(uploaded_case=completed_case)

    with make_client(service) as client:
        response = client.post("/cases/case-001/upload")

    assert response.status_code == 200
    assert response.json() == {
        "id": "case-001",
        "status": "COMPLETED",
        "created_at": "2026-09-02T10:00:00Z",
        "updated_at": "2026-09-02T10:45:00Z",
    }
    assert service.upload_call == "case-001"


def test_upload_case_returns_conflict_when_not_ready() -> None:
    error = CaseNotReadyForReviewError(
        "case-001",
        CaseStatus.PROCESSING,
    )
    with make_client(FakeReviewService(error=error)) as client:
        response = client.post("/cases/case-001/upload")

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "message": "Case case-001 is not ready for review: PROCESSING",
            "case_status": "PROCESSING",
        }
    }
