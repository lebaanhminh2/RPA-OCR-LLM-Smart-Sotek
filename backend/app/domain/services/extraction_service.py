from datetime import UTC, datetime
from uuid import uuid4

from app.domain.models import (
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
    ExtractedField,
    FieldSource,
    OCRBlock,
    OCRBlockKind,
)
from app.domain.ports.llm_provider import (
    MVP_FIELD_CODES,
    MVP_FIELD_SOURCE_RULES,
    LLMDocumentInput,
    LLMExtractedField,
    LLMProvider,
)
from app.domain.ports.ocr_provider import OCRProvider
from app.domain.ports.repository import ExtractionRepository


class ExtractionService:
    def __init__(
        self,
        repository: ExtractionRepository,
        ocr_provider: OCRProvider,
        llm_provider: LLMProvider,
    ) -> None:
        self._repository = repository
        self._ocr_provider = ocr_provider
        self._llm_provider = llm_provider

    def is_case_ready_for_ocr(self, case_id: str) -> bool:
        case = self._repository.get_case(case_id)
        return case is not None and case.status is CaseStatus.PROCESSING

    def process_case_ocr(self, case_id: str) -> None:
        if not self.is_case_ready_for_ocr(case_id):
            return

        try:
            self._process_ready_case(case_id)
        except Exception:
            self._mark_case_failed(case_id)

    def _process_ready_case(self, case_id: str) -> None:
        any_failed = False
        documents = self._repository.list_documents_by_case_id(case_id)
        for document in documents:
            if document.ocr_status is not DocumentOcrStatus.PENDING:
                continue
            if not self._process_document(document):
                any_failed = True

        if any_failed:
            self._mark_case_failed(case_id)
            return

        documents = self._repository.list_documents_by_case_id(case_id)
        if any(
            document.ocr_status is DocumentOcrStatus.FAILED
            for document in documents
        ):
            self._mark_case_failed(case_id)
            return
        if not documents or any(
            document.ocr_status is not DocumentOcrStatus.DONE
            for document in documents
        ):
            return

        self._process_llm(case_id, documents)

    def _process_document(self, document: Document) -> bool:
        try:
            blocks = self._ocr_provider.extract(
                document.id,
                document.document_type,
                document.file_path,
            )
            self._repository.create_ocr_blocks(blocks)
            updated_document = self._repository.update_document_ocr_status(
                document.id,
                DocumentOcrStatus.DONE,
            )
            if updated_document is None:
                raise RuntimeError(
                    f"Document disappeared during OCR: {document.id}"
                )
        except Exception:
            failed_document = self._repository.update_document_ocr_status(
                document.id,
                DocumentOcrStatus.FAILED,
            )
            if failed_document is None:
                raise RuntimeError(
                    f"Unable to mark missing document as failed: {document.id}"
                )
            return False
        return True

    def _process_llm(self, case_id: str, documents: list[Document]) -> None:
        llm_documents: list[LLMDocumentInput] = []
        blocks_by_id: dict[str, OCRBlock] = {}
        source_constraints_by_id: dict[
            str,
            tuple[DocumentType, OCRBlockKind],
        ] = {}
        for document in documents:
            blocks = self._repository.list_ocr_blocks_by_document_id(
                document.id
            )
            for block in blocks:
                if block.id in blocks_by_id:
                    raise RuntimeError(f"Duplicate OCR source ID: {block.id}")
                blocks_by_id[block.id] = block
                source_constraints_by_id[block.id] = (
                    document.document_type,
                    block.block_kind,
                )
            llm_documents.append(
                LLMDocumentInput(
                    document_id=document.id,
                    document_type=document.document_type,
                    blocks=blocks,
                )
            )

        llm_fields = self._llm_provider.extract(llm_documents)
        fields, sources = self._build_persisted_extraction(
            case_id,
            llm_fields,
            blocks_by_id,
            source_constraints_by_id,
        )
        self._repository.create_extracted_fields(fields, sources)
        updated_case = self._repository.update_case_status(
            case_id,
            CaseStatus.READY_FOR_REVIEW,
            datetime.now(UTC),
        )
        if updated_case is None:
            raise RuntimeError(f"Case disappeared during extraction: {case_id}")

    @staticmethod
    def _build_persisted_extraction(
        case_id: str,
        llm_fields: list[LLMExtractedField],
        blocks_by_id: dict[str, OCRBlock],
        source_constraints_by_id: dict[
            str,
            tuple[DocumentType, OCRBlockKind],
        ],
    ) -> tuple[list[ExtractedField], list[FieldSource]]:
        expected_codes = set(MVP_FIELD_CODES)
        fields_by_code: dict[str, LLMExtractedField] = {}
        ambiguous_codes: set[str] = set()
        for llm_field in llm_fields:
            if llm_field.field_code not in expected_codes:
                continue
            if llm_field.field_code in fields_by_code:
                ambiguous_codes.add(llm_field.field_code)
                continue
            fields_by_code[llm_field.field_code] = llm_field

        timestamp = datetime.now(UTC)
        fields: list[ExtractedField] = []
        sources: list[FieldSource] = []
        for field_code in MVP_FIELD_CODES:
            candidate = (
                None
                if field_code in ambiguous_codes
                else fields_by_code.get(field_code)
            )
            value, source_ids = ExtractionService._validated_field_value(
                candidate,
                blocks_by_id,
                source_constraints_by_id,
            )
            field = ExtractedField(
                id=str(uuid4()),
                case_id=case_id,
                field_code=field_code,
                original_value=value,
                current_value=value,
                created_at=timestamp,
                updated_at=timestamp,
            )
            fields.append(field)
            sources.extend(
                FieldSource(
                    id=str(uuid4()),
                    extracted_field_id=field.id,
                    ocr_block_id=source_id,
                )
                for source_id in source_ids
            )
        return fields, sources

    @staticmethod
    def _validated_field_value(
        field: LLMExtractedField | None,
        blocks_by_id: dict[str, OCRBlock],
        source_constraints_by_id: dict[
            str,
            tuple[DocumentType, OCRBlockKind],
        ],
    ) -> tuple[str | None, list[str]]:
        if field is None or field.value is None or not field.value.strip():
            return None, []

        source_ids = list(dict.fromkeys(field.source_ids))
        if not source_ids or any(
            source_id not in blocks_by_id for source_id in source_ids
        ):
            return None, []
        allowed_sources = MVP_FIELD_SOURCE_RULES[field.field_code]
        if any(
            source_constraints_by_id.get(source_id) not in allowed_sources
            for source_id in source_ids
        ):
            return None, []
        return field.value, source_ids

    def _mark_case_failed(self, case_id: str) -> None:
        updated_case = self._repository.update_case_status(
            case_id,
            CaseStatus.FAILED,
            datetime.now(UTC),
        )
        if updated_case is None:
            raise RuntimeError(
                f"Unable to mark missing case as failed: {case_id}"
            )
