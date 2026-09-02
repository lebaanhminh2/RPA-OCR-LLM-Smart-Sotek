from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.review import create_review_router
from app.domain.models import (
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
    ReviewService,
)


class FakeReviewService(ReviewService):
    def __init__(
        self,
        review: CaseReview | None = None,
        error: Exception | None = None,
    ) -> None:
        self.review = review
        self.error = error

    def get_case_review(self, case_id: str) -> CaseReview:
        if self.error is not None:
            raise self.error
        if self.review is None:
            raise AssertionError("Test must configure a review or error")
        return self.review


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
