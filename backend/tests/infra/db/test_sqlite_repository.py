from collections.abc import Iterator
from datetime import datetime
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
)
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


def test_schema_has_only_required_tables_and_constraints(
    database: DatabaseFixture,
) -> None:
    _, engine = database
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {"cases", "documents"}

    case_columns = {
        column["name"] for column in inspector.get_columns("cases")
    }
    document_columns = {
        column["name"] for column in inspector.get_columns("documents")
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

    assert inspector.get_pk_constraint("cases")["constrained_columns"] == [
        "id"
    ]
    assert inspector.get_pk_constraint("documents")["constrained_columns"] == [
        "id"
    ]

    foreign_keys = inspector.get_foreign_keys("documents")
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["case_id"]
    assert foreign_keys[0]["referred_table"] == "cases"
    assert foreign_keys[0]["referred_columns"] == ["id"]

    unique_constraints = inspector.get_unique_constraints("documents")
    assert {
        tuple(constraint["column_names"])
        for constraint in unique_constraints
    } == {("case_id", "document_type")}
