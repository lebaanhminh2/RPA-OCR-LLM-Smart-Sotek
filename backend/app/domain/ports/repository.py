from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

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
)


@dataclass(frozen=True)
class FieldSourceEvidence:
    field_source: FieldSource
    ocr_block: OCRBlock


@dataclass(frozen=True)
class ExtractedFieldWithSources:
    field: ExtractedField
    sources: tuple[FieldSourceEvidence, ...]


class Repository(Protocol):
    def create_case(self, case: Case) -> Case: ...

    def get_case(self, case_id: str) -> Case | None: ...

    def update_case_status(
        self,
        case_id: str,
        status: CaseStatus,
        updated_at: datetime,
    ) -> Case | None: ...

    def create_document(self, document: Document) -> Document: ...

    def get_document(self, document_id: str) -> Document | None: ...

    def update_document_ocr_status(
        self,
        document_id: str,
        status: DocumentOcrStatus,
    ) -> Document | None: ...

    def list_documents_by_case_id(self, case_id: str) -> list[Document]: ...

    def document_type_exists(
        self,
        case_id: str,
        document_type: DocumentType,
    ) -> bool: ...

    def create_ocr_blocks(self, blocks: list[OCRBlock]) -> list[OCRBlock]: ...

    def list_ocr_blocks_by_document_id(
        self,
        document_id: str,
    ) -> list[OCRBlock]: ...


class ExtractionRepository(Repository, Protocol):
    def create_extracted_fields(
        self,
        fields: list[ExtractedField],
        sources: list[FieldSource],
    ) -> tuple[list[ExtractedField], list[FieldSource]]: ...

    def list_extracted_fields_with_sources_by_case_id(
        self,
        case_id: str,
    ) -> list[ExtractedFieldWithSources]: ...


class ReviewRepository(ExtractionRepository, Protocol):
    def get_extracted_field(
        self,
        extracted_field_id: str,
    ) -> ExtractedField | None: ...

    def create_review_action(self, action: ReviewAction) -> ReviewAction: ...

    def list_review_actions_by_case_id(
        self,
        case_id: str,
    ) -> list[ReviewAction]: ...

    def update_extracted_field_with_action(
        self,
        extracted_field_id: str,
        current_value: str | None,
        updated_at: datetime,
        action: ReviewAction,
    ) -> tuple[ExtractedField, ReviewAction] | None: ...

    def complete_case_with_action(
        self,
        case_id: str,
        updated_at: datetime,
        action: ReviewAction,
    ) -> tuple[Case, ReviewAction] | None: ...
