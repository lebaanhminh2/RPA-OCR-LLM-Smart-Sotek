from datetime import UTC, datetime

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
from app.domain.ports.llm_provider import (
    MVP_FIELD_CODES,
    LLMDocumentInput,
    LLMExtractedField,
)
from app.domain.ports.repository import ExtractedFieldWithSources
from app.domain.services.extraction_service import ExtractionService


class FakeRepository:
    def __init__(self, case: Case, documents: list[Document]) -> None:
        self.cases = {case.id: case}
        self.documents = {document.id: document for document in documents}
        self.ocr_blocks: list[OCRBlock] = []
        self.extracted_fields: list[ExtractedField] = []
        self.field_sources: list[FieldSource] = []

    def create_case(self, case: Case) -> Case:
        self.cases[case.id] = case
        return case

    def get_case(self, case_id: str) -> Case | None:
        return self.cases.get(case_id)

    def update_case_status(
        self,
        case_id: str,
        status: CaseStatus,
        updated_at: datetime,
    ) -> Case | None:
        case = self.cases.get(case_id)
        if case is None:
            return None
        updated = Case(case.id, status, case.created_at, updated_at)
        self.cases[case_id] = updated
        return updated

    def create_document(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    def get_document(self, document_id: str) -> Document | None:
        return self.documents.get(document_id)

    def update_document_ocr_status(
        self,
        document_id: str,
        status: DocumentOcrStatus,
    ) -> Document | None:
        document = self.documents.get(document_id)
        if document is not None:
            document.ocr_status = status
        return document

    def list_documents_by_case_id(self, case_id: str) -> list[Document]:
        return [
            document
            for document in self.documents.values()
            if document.case_id == case_id
        ]

    def document_type_exists(
        self,
        case_id: str,
        document_type: DocumentType,
    ) -> bool:
        return any(
            document.case_id == case_id
            and document.document_type is document_type
            for document in self.documents.values()
        )

    def create_ocr_blocks(self, blocks: list[OCRBlock]) -> list[OCRBlock]:
        self.ocr_blocks.extend(blocks)
        return blocks

    def list_ocr_blocks_by_document_id(
        self,
        document_id: str,
    ) -> list[OCRBlock]:
        return [
            block
            for block in self.ocr_blocks
            if block.document_id == document_id
        ]

    def create_extracted_fields(
        self,
        fields: list[ExtractedField],
        sources: list[FieldSource],
    ) -> tuple[list[ExtractedField], list[FieldSource]]:
        self.extracted_fields.extend(fields)
        self.field_sources.extend(sources)
        return fields, sources

    def list_extracted_fields_with_sources_by_case_id(
        self,
        case_id: str,
    ) -> list[ExtractedFieldWithSources]:
        return []


class FakeOCRProvider:
    def __init__(self, failing_document_ids: set[str] | None = None) -> None:
        self.failing_document_ids = failing_document_ids or set()
        self.calls: list[tuple[str, DocumentType, str]] = []

    def extract(
        self,
        document_id: str,
        document_type: DocumentType,
        file_path: str,
    ) -> list[OCRBlock]:
        self.calls.append((document_id, document_type, file_path))
        if document_id in self.failing_document_ids:
            raise RuntimeError("synthetic OCR failure")
        return [
            OCRBlock(
                id=f"block-{document_id}",
                document_id=document_id,
                page_number=1,
                text=f"text for {document_id}",
                bbox_x=0.1,
                bbox_y=0.2,
                bbox_width=0.3,
                bbox_height=0.1,
                confidence=0.9,
                created_at=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
            )
        ]


class FakeLLMProvider:
    def __init__(
        self,
        fields: list[LLMExtractedField] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.fields = fields if fields is not None else make_null_llm_fields()
        self.error = error
        self.calls: list[list[LLMDocumentInput]] = []

    def extract(
        self,
        documents: list[LLMDocumentInput],
    ) -> list[LLMExtractedField]:
        self.calls.append(documents)
        if self.error is not None:
            raise self.error
        return self.fields


def make_null_llm_fields() -> list[LLMExtractedField]:
    return [
        LLMExtractedField(field_code=code, value=None, source_ids=[])
        for code in MVP_FIELD_CODES
    ]


def make_llm_fields_with(
    field: LLMExtractedField,
) -> list[LLMExtractedField]:
    return [
        field
        if code == field.field_code
        else LLMExtractedField(field_code=code, value=None, source_ids=[])
        for code in MVP_FIELD_CODES
    ]


def make_case(status: CaseStatus = CaseStatus.PROCESSING) -> Case:
    created_at = datetime(2026, 9, 2, 7, 0, tzinfo=UTC)
    return Case("case-001", status, created_at, created_at)


def make_document(document_id: str, document_type: DocumentType) -> Document:
    return Document(
        id=document_id,
        case_id="case-001",
        document_type=document_type,
        file_path=f"uploads/{document_id}.png",
        page_count=1,
        ocr_status=DocumentOcrStatus.PENDING,
        uploaded_at=datetime(2026, 9, 2, 7, 30, tzinfo=UTC),
    )


def test_process_case_runs_ocr_llm_and_moves_to_review() -> None:
    case = make_case()
    documents = [
        make_document("front", DocumentType.CCCD_FRONT),
        make_document("back", DocumentType.CCCD_BACK),
        make_document("application", DocumentType.LOAN_APPLICATION),
        make_document("contract", DocumentType.LABOR_CONTRACT),
    ]
    repository = FakeRepository(case, documents)
    ocr_provider = FakeOCRProvider()
    llm_provider = FakeLLMProvider(
        make_llm_fields_with(
            LLMExtractedField(
                field_code="ho_ten",
                value="NGUYỄN VĂN AN",
                source_ids=["block-front"],
            )
        )
    )
    service = ExtractionService(repository, ocr_provider, llm_provider)

    service.process_case_ocr(case.id)

    assert ocr_provider.calls == [
        (document.id, document.document_type, document.file_path)
        for document in documents
    ]
    assert {block.document_id for block in repository.ocr_blocks} == {
        document.id for document in documents
    }
    assert all(
        document.ocr_status is DocumentOcrStatus.DONE
        for document in repository.documents.values()
    )
    assert len(llm_provider.calls) == 1
    llm_documents = llm_provider.calls[0]
    assert [item.document_type for item in llm_documents] == [
        document.document_type for document in documents
    ]
    assert [item.blocks[0].id for item in llm_documents] == [
        f"block-{document.id}" for document in documents
    ]
    assert len(repository.extracted_fields) == 40
    by_code = {field.field_code: field for field in repository.extracted_fields}
    assert by_code["ho_ten"].original_value == "NGUYỄN VĂN AN"
    assert by_code["email"].original_value is None
    assert len(repository.field_sources) == 1
    assert repository.field_sources[0].ocr_block_id == "block-front"
    assert repository.cases[case.id].status is CaseStatus.READY_FOR_REVIEW


def test_process_case_ocr_marks_failure_and_continues_other_documents() -> None:
    case = make_case()
    failed = make_document("front", DocumentType.CCCD_FRONT)
    successful = make_document("back", DocumentType.CCCD_BACK)
    repository = FakeRepository(case, [failed, successful])
    ocr_provider = FakeOCRProvider({failed.id})
    llm_provider = FakeLLMProvider()
    service = ExtractionService(repository, ocr_provider, llm_provider)

    service.process_case_ocr(case.id)

    assert repository.documents[failed.id].ocr_status is DocumentOcrStatus.FAILED
    assert (
        repository.documents[successful.id].ocr_status
        is DocumentOcrStatus.DONE
    )
    assert [block.document_id for block in repository.ocr_blocks] == [
        successful.id
    ]
    assert repository.cases[case.id].status is CaseStatus.FAILED
    assert llm_provider.calls == []


def test_process_case_ocr_is_noop_until_case_is_processing() -> None:
    case = make_case(CaseStatus.UPLOADING)
    document = make_document("front", DocumentType.CCCD_FRONT)
    repository = FakeRepository(case, [document])
    ocr_provider = FakeOCRProvider()
    llm_provider = FakeLLMProvider()
    service = ExtractionService(repository, ocr_provider, llm_provider)

    assert not service.is_case_ready_for_ocr(case.id)
    assert not service.is_case_ready_for_ocr("missing-case")

    service.process_case_ocr(case.id)

    assert ocr_provider.calls == []
    assert llm_provider.calls == []
    assert repository.ocr_blocks == []
    assert document.ocr_status is DocumentOcrStatus.PENDING


def test_invalid_source_becomes_blank_field_without_failing_case() -> None:
    case = make_case()
    documents = [
        make_document("front", DocumentType.CCCD_FRONT),
        make_document("back", DocumentType.CCCD_BACK),
        make_document("application", DocumentType.LOAN_APPLICATION),
        make_document("contract", DocumentType.LABOR_CONTRACT),
    ]
    repository = FakeRepository(case, documents)
    llm_provider = FakeLLMProvider(
        make_llm_fields_with(
            LLMExtractedField(
                field_code="ho_ten",
                value="GIÁ TRỊ KHÔNG CÓ BẰNG CHỨNG",
                source_ids=["invented-source"],
            )
        )
    )
    service = ExtractionService(
        repository,
        FakeOCRProvider(),
        llm_provider,
    )

    service.process_case_ocr(case.id)

    by_code = {field.field_code: field for field in repository.extracted_fields}
    assert len(by_code) == 40
    assert by_code["ho_ten"].original_value is None
    assert by_code["ho_ten"].current_value is None
    assert repository.field_sources == []
    assert repository.cases[case.id].status is CaseStatus.READY_FOR_REVIEW


def test_missing_and_duplicate_outputs_still_create_40_blankable_fields() -> None:
    case = make_case()
    documents = [
        make_document("front", DocumentType.CCCD_FRONT),
        make_document("back", DocumentType.CCCD_BACK),
        make_document("application", DocumentType.LOAN_APPLICATION),
        make_document("contract", DocumentType.LABOR_CONTRACT),
    ]
    repository = FakeRepository(case, documents)
    llm_provider = FakeLLMProvider(
        [
            LLMExtractedField(
                field_code="ho_ten",
                value="NGUYỄN VĂN AN",
                source_ids=["block-front"],
            ),
            LLMExtractedField(
                field_code="ho_ten",
                value="TRÙNG LẶP",
                source_ids=["block-front"],
            ),
            LLMExtractedField(
                field_code="unsupported_field",
                value="BỎ QUA",
                source_ids=["block-front"],
            ),
        ]
    )
    service = ExtractionService(
        repository,
        FakeOCRProvider(),
        llm_provider,
    )

    service.process_case_ocr(case.id)

    assert len(repository.extracted_fields) == 40
    assert all(
        field.original_value is None for field in repository.extracted_fields
    )
    assert repository.cases[case.id].status is CaseStatus.READY_FOR_REVIEW


def test_llm_failure_marks_case_failed_without_persisting_fields() -> None:
    case = make_case()
    documents = [
        make_document("front", DocumentType.CCCD_FRONT),
        make_document("back", DocumentType.CCCD_BACK),
        make_document("application", DocumentType.LOAN_APPLICATION),
        make_document("contract", DocumentType.LABOR_CONTRACT),
    ]
    repository = FakeRepository(case, documents)
    llm_provider = FakeLLMProvider(error=RuntimeError("synthetic LLM failure"))
    service = ExtractionService(
        repository,
        FakeOCRProvider(),
        llm_provider,
    )

    service.process_case_ocr(case.id)

    assert len(llm_provider.calls) == 1
    assert repository.extracted_fields == []
    assert repository.field_sources == []
    assert repository.cases[case.id].status is CaseStatus.FAILED


def test_secondary_ocr_status_error_cannot_leave_case_processing() -> None:
    class FailingDocumentStatusRepository(FakeRepository):
        def update_document_ocr_status(
            self,
            document_id: str,
            status: DocumentOcrStatus,
        ) -> Document | None:
            raise RuntimeError("synthetic document status failure")

    case = make_case()
    document = make_document("front", DocumentType.CCCD_FRONT)
    repository = FailingDocumentStatusRepository(case, [document])
    service = ExtractionService(
        repository,
        FakeOCRProvider({document.id}),
        FakeLLMProvider(),
    )

    service.process_case_ocr(case.id)

    assert repository.cases[case.id].status is CaseStatus.FAILED
