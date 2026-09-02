from dataclasses import dataclass

from app.domain.models import CaseStatus
from app.domain.ports.llm_provider import MVP_FIELD_CODES
from app.domain.ports.repository import (
    ExtractedFieldWithSources,
    ExtractionRepository,
)
from app.domain.services.case_service import CaseNotFoundError


class CaseNotReadyForReviewError(Exception):
    def __init__(self, case_id: str, case_status: CaseStatus) -> None:
        self.case_id = case_id
        self.case_status = case_status
        super().__init__(
            f"Case {case_id} is not ready for review: {case_status.value}"
        )


@dataclass(frozen=True)
class CaseReview:
    case_id: str
    status: CaseStatus
    fields: tuple[ExtractedFieldWithSources, ...]


class ReviewService:
    def __init__(self, repository: ExtractionRepository) -> None:
        self._repository = repository

    def get_case_review(self, case_id: str) -> CaseReview:
        case = self._repository.get_case(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)
        if case.status not in {
            CaseStatus.READY_FOR_REVIEW,
            CaseStatus.COMPLETED,
        }:
            raise CaseNotReadyForReviewError(case_id, case.status)

        field_order = {
            field_code: index
            for index, field_code in enumerate(MVP_FIELD_CODES)
        }
        fields = self._repository.list_extracted_fields_with_sources_by_case_id(
            case_id
        )
        fields.sort(
            key=lambda item: (
                field_order.get(item.field.field_code, len(field_order)),
                item.field.field_code,
            )
        )
        return CaseReview(
            case_id=case.id,
            status=case.status,
            fields=tuple(fields),
        )
