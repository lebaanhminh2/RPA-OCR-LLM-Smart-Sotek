from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.domain.models import CaseStatus
from app.domain.ports.repository import ExtractedFieldWithSources
from app.domain.services.case_service import CaseNotFoundError
from app.domain.services.review_service import (
    CaseNotReadyForReviewError,
    ReviewService,
)


class ReviewSourceResponse(BaseModel):
    ocr_block_id: str
    document_id: str
    page_number: int
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float


class ReviewFieldResponse(BaseModel):
    id: str
    case_id: str
    field_code: str
    original_value: str | None
    current_value: str | None
    sources: list[ReviewSourceResponse]


class CaseReviewResponse(BaseModel):
    case_id: str
    status: CaseStatus
    fields: list[ReviewFieldResponse]


def _field_response(item: ExtractedFieldWithSources) -> ReviewFieldResponse:
    return ReviewFieldResponse(
        id=item.field.id,
        case_id=item.field.case_id,
        field_code=item.field.field_code,
        original_value=item.field.original_value,
        current_value=item.field.current_value,
        sources=[
            ReviewSourceResponse(
                ocr_block_id=evidence.ocr_block.id,
                document_id=evidence.ocr_block.document_id,
                page_number=evidence.ocr_block.page_number,
                bbox_x=evidence.ocr_block.bbox_x,
                bbox_y=evidence.ocr_block.bbox_y,
                bbox_width=evidence.ocr_block.bbox_width,
                bbox_height=evidence.ocr_block.bbox_height,
            )
            for evidence in item.sources
        ],
    )


def create_review_router(review_service: ReviewService) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/cases/{case_id}/review",
        response_model=CaseReviewResponse,
    )
    def get_case_review(case_id: str) -> CaseReviewResponse:
        try:
            review = review_service.get_case_review(case_id)
        except CaseNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except CaseNotReadyForReviewError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": str(error),
                    "case_status": error.case_status.value,
                },
            ) from error

        return CaseReviewResponse(
            case_id=review.case_id,
            status=review.status,
            fields=[_field_response(item) for item in review.fields],
        )

    return router
