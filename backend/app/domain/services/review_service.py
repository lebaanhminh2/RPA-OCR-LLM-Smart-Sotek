from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.models import (
    Case,
    CaseStatus,
    ExtractedField,
    ReviewAction,
    ReviewActionType,
)
from app.domain.ports.llm_provider import MVP_FIELD_CODES
from app.domain.ports.repository import (
    ExtractedFieldWithSources,
    ReviewRepository,
)
from app.domain.services.case_service import CaseNotFoundError


class CaseNotReadyForReviewError(Exception):
    def __init__(self, case_id: str, case_status: CaseStatus) -> None:
        self.case_id = case_id
        self.case_status = case_status
        super().__init__(
            f"Case {case_id} is not ready for review: {case_status.value}"
        )


class ExtractedFieldNotFoundError(Exception):
    def __init__(self, case_id: str, extracted_field_id: str) -> None:
        self.case_id = case_id
        self.extracted_field_id = extracted_field_id
        super().__init__(
            f"Extracted field not found in case {case_id}: "
            f"{extracted_field_id}"
        )


@dataclass(frozen=True)
class CaseReview:
    case_id: str
    status: CaseStatus
    fields: tuple[ExtractedFieldWithSources, ...]


class ReviewService:
    def __init__(
        self,
        repository: ReviewRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

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

    def update_field(
        self,
        case_id: str,
        extracted_field_id: str,
        current_value: str | None,
    ) -> ExtractedField:
        case = self._get_ready_case(case_id)
        field = self._repository.get_extracted_field(extracted_field_id)
        if field is None or field.case_id != case.id:
            raise ExtractedFieldNotFoundError(case_id, extracted_field_id)

        updated_at = self._clock()
        action = ReviewAction(
            id=self._id_factory(),
            case_id=case.id,
            extracted_field_id=field.id,
            action_type=ReviewActionType.EDIT_FIELD,
            previous_value=field.current_value,
            new_value=current_value,
            created_at=updated_at,
        )
        result = self._repository.update_extracted_field_with_action(
            field.id,
            current_value,
            updated_at,
            action,
        )
        if result is None:
            raise ExtractedFieldNotFoundError(case_id, extracted_field_id)
        updated_field, _ = result
        return updated_field

    def upload_case(self, case_id: str) -> Case:
        case = self._get_ready_case(case_id)
        completed_at = self._clock()
        action = ReviewAction(
            id=self._id_factory(),
            case_id=case.id,
            extracted_field_id=None,
            action_type=ReviewActionType.UPLOAD_CASE,
            previous_value=None,
            new_value=None,
            created_at=completed_at,
        )
        result = self._repository.complete_case_with_action(
            case.id,
            completed_at,
            action,
        )
        if result is None:
            raise CaseNotFoundError(case_id)
        completed_case, _ = result
        return completed_case

    def _get_ready_case(self, case_id: str) -> Case:
        case = self._repository.get_case(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)
        if case.status is not CaseStatus.READY_FOR_REVIEW:
            raise CaseNotReadyForReviewError(case_id, case.status)
        return case
