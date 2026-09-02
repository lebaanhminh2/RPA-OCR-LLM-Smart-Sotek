from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError

from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
    ExtractedField,
    FieldSource,
    OCRBlock,
    OCRBlockKind,
)
from app.domain.ports.repository import ExtractionRepository, Repository
from app.infra.db.database import create_session_factory, create_sqlite_engine
from app.infra.db.orm_models import Base
from app.infra.db.sqlite_repository import SQLiteRepository

DatabaseFixture = tuple[SQLiteRepository, Engine]


@pytest.fixture
def database(tmp_path: Path) -> Iterator[DatabaseFixture]:
    database_path = tmp_path / "repository.db"
    engine = create_sqlite_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    repository = SQLiteRepository(create_session_factory(engine))

    try:
        yield repository, engine
    finally:
        engine.dispose()


def make_case(case_id: str) -> Case:
    created_at = datetime(2026, 9, 1, 8, 0)
    return Case(
        id=case_id,
        status=CaseStatus.UPLOADING,
        created_at=created_at,
        updated_at=created_at,
    )


def make_document(
    document_id: str,
    case_id: str,
    document_type: DocumentType,
    *,
    ocr_status: DocumentOcrStatus = DocumentOcrStatus.PENDING,
) -> Document:
    return Document(
        id=document_id,
        case_id=case_id,
        document_type=document_type,
        file_path=f"uploads/{case_id}/{document_id}.pdf",
        page_count=1,
        ocr_status=ocr_status,
        uploaded_at=datetime(2026, 9, 1, 8, 30),
    )


def make_ocr_block(
    block_id: str,
    document_id: str,
    *,
    page_number: int = 1,
    text: str = "Đơn đề nghị vay vốn",
    block_kind: OCRBlockKind = OCRBlockKind.TEXT,
    created_at: datetime | None = None,
) -> OCRBlock:
    return OCRBlock(
        id=block_id,
        document_id=document_id,
        page_number=page_number,
        text=text,
        bbox_x=0.12,
        bbox_y=0.34,
        bbox_width=0.30,
        bbox_height=0.04,
        confidence=0.97,
        created_at=created_at or datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        block_kind=block_kind,
    )


def make_extracted_field(
    field_id: str,
    case_id: str,
    field_code: str,
    value: str | None,
) -> ExtractedField:
    timestamp = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
    return ExtractedField(
        id=field_id,
        case_id=case_id,
        field_code=field_code,
        original_value=value,
        current_value=value,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_create_and_get_case_round_trips_domain_enum(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")

    created = repository.create_case(case)
    retrieved = repository.get_case(case.id)

    assert created == case
    assert retrieved == case
    assert retrieved is not None
    assert retrieved.status is CaseStatus.UPLOADING


def test_get_case_returns_none_when_case_does_not_exist(
    database: DatabaseFixture,
) -> None:
    repository, _ = database

    assert repository.get_case("missing-case") is None


def test_update_case_status_persists_caller_timestamp(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    repository.create_case(case)
    updated_at = datetime(2026, 9, 1, 10, 15)

    updated = repository.update_case_status(
        case.id,
        CaseStatus.PROCESSING,
        updated_at,
    )
    retrieved = repository.get_case(case.id)

    assert updated is not None
    assert updated.status is CaseStatus.PROCESSING
    assert updated.updated_at == updated_at
    assert retrieved == updated


def test_create_document_round_trips_all_fields_and_domain_enums(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    document = make_document(
        "document-001",
        case.id,
        DocumentType.CCCD_FRONT,
        ocr_status=DocumentOcrStatus.DONE,
    )
    repository.create_case(case)

    created = repository.create_document(document)
    retrieved = repository.list_documents_by_case_id(case.id)

    assert created == document
    assert retrieved == [document]
    assert retrieved[0].document_type is DocumentType.CCCD_FRONT
    assert retrieved[0].ocr_status is DocumentOcrStatus.DONE


def test_get_document_round_trips_domain_document_and_enums(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    document = make_document(
        "document-001",
        case.id,
        DocumentType.CCCD_BACK,
        ocr_status=DocumentOcrStatus.DONE,
    )
    repository.create_case(case)
    repository.create_document(document)

    retrieved = repository.get_document(document.id)

    assert retrieved == document
    assert retrieved is not None
    assert retrieved.document_type is DocumentType.CCCD_BACK
    assert retrieved.ocr_status is DocumentOcrStatus.DONE


def test_get_document_returns_none_when_document_does_not_exist(
    database: DatabaseFixture,
) -> None:
    repository, _ = database

    assert repository.get_document("missing-document") is None


def test_update_document_ocr_status_persists_transition(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    document = make_document(
        "document-001",
        case.id,
        DocumentType.CCCD_FRONT,
    )
    repository.create_case(case)
    repository.create_document(document)

    updated = repository.update_document_ocr_status(
        document.id,
        DocumentOcrStatus.DONE,
    )

    assert updated is not None
    assert updated.ocr_status is DocumentOcrStatus.DONE
    assert repository.get_document(document.id) == updated
    assert (
        repository.update_document_ocr_status(
            "missing-document",
            DocumentOcrStatus.FAILED,
        )
        is None
    )


def test_list_documents_only_returns_documents_for_requested_case(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    first_case = make_case("case-001")
    second_case = make_case("case-002")
    first_document = make_document(
        "document-001",
        first_case.id,
        DocumentType.CCCD_FRONT,
    )
    second_document = make_document(
        "document-002",
        second_case.id,
        DocumentType.CCCD_BACK,
    )
    repository.create_case(first_case)
    repository.create_case(second_case)
    repository.create_document(first_document)
    repository.create_document(second_document)

    assert repository.list_documents_by_case_id(first_case.id) == [
        first_document
    ]
    assert repository.list_documents_by_case_id(second_case.id) == [
        second_document
    ]


def test_document_type_exists_before_and_after_creation(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    document = make_document(
        "document-001",
        case.id,
        DocumentType.LOAN_APPLICATION,
    )
    repository.create_case(case)

    assert not repository.document_type_exists(
        case.id,
        DocumentType.LOAN_APPLICATION,
    )

    repository.create_document(document)

    assert repository.document_type_exists(
        case.id,
        DocumentType.LOAN_APPLICATION,
    )


def test_duplicate_document_type_rolls_back_and_repository_remains_usable(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    original = make_document(
        "document-001",
        case.id,
        DocumentType.CCCD_FRONT,
    )
    duplicate = make_document(
        "document-002",
        case.id,
        DocumentType.CCCD_FRONT,
    )
    valid_after_failure = make_document(
        "document-003",
        case.id,
        DocumentType.CCCD_BACK,
    )
    repository.create_case(case)
    repository.create_document(original)

    with pytest.raises(IntegrityError):
        repository.create_document(duplicate)

    created_after_failure = repository.create_document(valid_after_failure)
    persisted_documents = repository.list_documents_by_case_id(case.id)

    assert created_after_failure == valid_after_failure
    assert {
        document.id: document for document in persisted_documents
    } == {
        original.id: original,
        valid_after_failure.id: valid_after_failure,
    }


def test_create_and_list_ocr_blocks_round_trip_all_fields(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    document = make_document(
        "document-001",
        case.id,
        DocumentType.LOAN_APPLICATION,
    )
    block = make_ocr_block("ocr-block-001", document.id)
    repository.create_case(case)
    repository.create_document(document)

    created = repository.create_ocr_blocks([block])
    retrieved = repository.list_ocr_blocks_by_document_id(document.id)

    assert created == [block]
    assert retrieved == [block]
    assert retrieved[0].created_at.tzinfo is UTC


def test_checkbox_selection_block_round_trips_kind(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    document = make_document(
        "document-001",
        case.id,
        DocumentType.LOAN_APPLICATION,
    )
    block = make_ocr_block(
        "ocr-checkbox-001",
        document.id,
        text="field_code=ky_han_vay;option=24 tháng",
        block_kind=OCRBlockKind.CHECKBOX_SELECTION,
    )
    repository.create_case(case)
    repository.create_document(document)

    repository.create_ocr_blocks([block])

    assert repository.list_ocr_blocks_by_document_id(document.id) == [block]


def test_list_ocr_blocks_filters_document_and_orders_deterministically(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    first_document = make_document(
        "document-001",
        case.id,
        DocumentType.CCCD_FRONT,
    )
    second_document = make_document(
        "document-002",
        case.id,
        DocumentType.CCCD_BACK,
    )
    created_at = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
    later_on_page_one = make_ocr_block(
        "ocr-block-002",
        first_document.id,
        created_at=created_at + timedelta(seconds=1),
    )
    page_two = make_ocr_block(
        "ocr-block-003",
        first_document.id,
        page_number=2,
        created_at=created_at,
    )
    earlier_on_page_one = make_ocr_block(
        "ocr-block-001",
        first_document.id,
        created_at=created_at,
    )
    other_document_block = make_ocr_block(
        "ocr-block-004",
        second_document.id,
    )
    repository.create_case(case)
    repository.create_document(first_document)
    repository.create_document(second_document)

    repository.create_ocr_blocks(
        [page_two, later_on_page_one, other_document_block, earlier_on_page_one]
    )

    assert repository.list_ocr_blocks_by_document_id(first_document.id) == [
        earlier_on_page_one,
        later_on_page_one,
        page_two,
    ]


def test_list_ocr_blocks_returns_empty_for_document_without_blocks(
    database: DatabaseFixture,
) -> None:
    repository, _ = database

    assert repository.list_ocr_blocks_by_document_id("missing-document") == []
    assert repository.create_ocr_blocks([]) == []


def test_repository_exposes_no_ocr_block_update_or_delete_api() -> None:
    forbidden_methods = {
        "update_ocr_block",
        "update_ocr_blocks",
        "delete_ocr_block",
        "delete_ocr_blocks",
    }

    for method_name in forbidden_methods:
        assert not hasattr(Repository, method_name)
        assert not hasattr(SQLiteRepository, method_name)


def test_create_and_list_extracted_fields_with_sources(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    document = make_document(
        "document-001",
        case.id,
        DocumentType.CCCD_FRONT,
    )
    block = make_ocr_block(
        "ocr-block-001",
        document.id,
        text="Họ và tên: NGUYỄN VĂN AN",
    )
    populated_field = make_extracted_field(
        "field-001",
        case.id,
        "ho_ten",
        "NGUYỄN VĂN AN",
    )
    missing_field = make_extracted_field(
        "field-002",
        case.id,
        "email",
        None,
    )
    source = FieldSource(
        id="field-source-001",
        extracted_field_id=populated_field.id,
        ocr_block_id=block.id,
    )
    repository.create_case(case)
    repository.create_document(document)
    repository.create_ocr_blocks([block])

    created_fields, created_sources = repository.create_extracted_fields(
        [populated_field, missing_field],
        [source],
    )
    retrieved = repository.list_extracted_fields_with_sources_by_case_id(
        case.id
    )

    assert created_fields == [populated_field, missing_field]
    assert created_sources == [source]
    by_code = {item.field.field_code: item for item in retrieved}
    assert set(by_code) == {"ho_ten", "email"}
    assert by_code["email"].field == missing_field
    assert by_code["email"].sources == ()
    assert by_code["ho_ten"].field == populated_field
    assert len(by_code["ho_ten"].sources) == 1
    evidence = by_code["ho_ten"].sources[0]
    assert evidence.field_source == source
    assert evidence.ocr_block == block


def test_extracted_fields_are_filtered_by_case(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    first_case = make_case("case-001")
    second_case = make_case("case-002")
    first_field = make_extracted_field(
        "field-001", first_case.id, "ho_ten", "NGUYỄN VĂN AN"
    )
    second_field = make_extracted_field(
        "field-002", second_case.id, "ho_ten", "TRẦN THỊ BÌNH"
    )
    repository.create_case(first_case)
    repository.create_case(second_case)
    repository.create_extracted_fields([first_field], [])
    repository.create_extracted_fields([second_field], [])

    retrieved = repository.list_extracted_fields_with_sources_by_case_id(
        first_case.id
    )

    assert [item.field for item in retrieved] == [first_field]


def test_create_extracted_fields_rejects_source_outside_batch(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    field = make_extracted_field(
        "field-001", "case-001", "ho_ten", "NGUYỄN VĂN AN"
    )
    source = FieldSource(
        id="field-source-001",
        extracted_field_id="field-outside-batch",
        ocr_block_id="ocr-block-001",
    )

    with pytest.raises(ValueError, match="same batch"):
        repository.create_extracted_fields([field], [source])


def test_create_extracted_fields_rolls_back_whole_batch_on_conflict(
    database: DatabaseFixture,
) -> None:
    repository, _ = database
    case = make_case("case-001")
    first = make_extracted_field(
        "field-001", case.id, "ho_ten", "NGUYỄN VĂN AN"
    )
    conflicting = make_extracted_field(
        "field-002", case.id, "ho_ten", "TRẦN THỊ BÌNH"
    )
    repository.create_case(case)

    with pytest.raises(IntegrityError):
        repository.create_extracted_fields([first, conflicting], [])

    assert repository.list_extracted_fields_with_sources_by_case_id(
        case.id
    ) == []


def test_repository_exposes_no_field_source_update_or_delete_api() -> None:
    forbidden_methods = {
        "update_field_source",
        "update_field_sources",
        "delete_field_source",
        "delete_field_sources",
    }

    for method_name in forbidden_methods:
        assert not hasattr(ExtractionRepository, method_name)
        assert not hasattr(SQLiteRepository, method_name)


def test_schema_has_only_required_tables_and_constraints(
    database: DatabaseFixture,
) -> None:
    _, engine = database
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {
        "cases",
        "documents",
        "extracted_fields",
        "field_sources",
        "ocr_blocks",
    }

    case_columns = {
        column["name"] for column in inspector.get_columns("cases")
    }
    document_columns = {
        column["name"] for column in inspector.get_columns("documents")
    }
    ocr_block_columns = {
        column["name"] for column in inspector.get_columns("ocr_blocks")
    }
    extracted_field_columns = {
        column["name"]
        for column in inspector.get_columns("extracted_fields")
    }
    field_source_columns = {
        column["name"] for column in inspector.get_columns("field_sources")
    }
    assert case_columns == {"id", "status", "created_at", "updated_at"}
    assert document_columns == {
        "id",
        "case_id",
        "document_type",
        "file_path",
        "page_count",
        "ocr_status",
        "uploaded_at",
    }
    assert ocr_block_columns == {
        "id",
        "document_id",
        "block_kind",
        "page_number",
        "text",
        "bbox_x",
        "bbox_y",
        "bbox_width",
        "bbox_height",
        "confidence",
        "created_at",
    }
    assert extracted_field_columns == {
        "id",
        "case_id",
        "field_code",
        "original_value",
        "current_value",
        "created_at",
        "updated_at",
    }
    assert field_source_columns == {
        "id",
        "extracted_field_id",
        "ocr_block_id",
    }

    assert inspector.get_pk_constraint("cases")["constrained_columns"] == [
        "id"
    ]
    assert inspector.get_pk_constraint("documents")["constrained_columns"] == [
        "id"
    ]
    assert inspector.get_pk_constraint("ocr_blocks")["constrained_columns"] == [
        "id"
    ]
    assert inspector.get_pk_constraint("extracted_fields")[
        "constrained_columns"
    ] == ["id"]
    assert inspector.get_pk_constraint("field_sources")[
        "constrained_columns"
    ] == ["id"]

    foreign_keys = inspector.get_foreign_keys("documents")
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["case_id"]
    assert foreign_keys[0]["referred_table"] == "cases"
    assert foreign_keys[0]["referred_columns"] == ["id"]

    ocr_block_foreign_keys = inspector.get_foreign_keys("ocr_blocks")
    assert len(ocr_block_foreign_keys) == 1
    assert ocr_block_foreign_keys[0]["constrained_columns"] == ["document_id"]
    assert ocr_block_foreign_keys[0]["referred_table"] == "documents"
    assert ocr_block_foreign_keys[0]["referred_columns"] == ["id"]

    extracted_field_foreign_keys = inspector.get_foreign_keys(
        "extracted_fields"
    )
    assert len(extracted_field_foreign_keys) == 1
    assert extracted_field_foreign_keys[0]["constrained_columns"] == [
        "case_id"
    ]
    assert extracted_field_foreign_keys[0]["referred_table"] == "cases"

    field_source_foreign_keys = {
        foreign_key["constrained_columns"][0]: foreign_key
        for foreign_key in inspector.get_foreign_keys("field_sources")
    }
    assert set(field_source_foreign_keys) == {
        "extracted_field_id",
        "ocr_block_id",
    }
    assert (
        field_source_foreign_keys["extracted_field_id"]["referred_table"]
        == "extracted_fields"
    )
    assert (
        field_source_foreign_keys["ocr_block_id"]["referred_table"]
        == "ocr_blocks"
    )

    unique_constraints = inspector.get_unique_constraints("documents")
    assert {
        tuple(constraint["column_names"])
        for constraint in unique_constraints
    } == {("case_id", "document_type")}

    extracted_field_unique_constraints = inspector.get_unique_constraints(
        "extracted_fields"
    )
    assert {
        tuple(constraint["column_names"])
        for constraint in extracted_field_unique_constraints
    } == {("case_id", "field_code")}

    field_source_unique_constraints = inspector.get_unique_constraints(
        "field_sources"
    )
    assert {
        tuple(constraint["column_names"])
        for constraint in field_source_unique_constraints
    } == {("extracted_field_id", "ocr_block_id")}

    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("ocr_blocks")
    } == {
        "ck_ocr_blocks_bbox_height",
        "ck_ocr_blocks_bbox_width",
        "ck_ocr_blocks_bbox_x",
        "ck_ocr_blocks_bbox_y",
        "ck_ocr_blocks_confidence",
        "ck_ocr_blocks_page_number",
    }
