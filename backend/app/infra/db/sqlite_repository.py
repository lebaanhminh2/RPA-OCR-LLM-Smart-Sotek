from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentType,
)
from app.domain.ports.repository import Repository
from app.infra.db.orm_models import CaseRecord, DocumentRecord


def _case_to_domain(record: CaseRecord) -> Case:
    return Case(
        id=record.id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _document_to_domain(record: DocumentRecord) -> Document:
    return Document(
        id=record.id,
        case_id=record.case_id,
        document_type=record.document_type,
        file_path=record.file_path,
        page_count=record.page_count,
        ocr_status=record.ocr_status,
        uploaded_at=record.uploaded_at,
    )


class SQLiteRepository(Repository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_case(self, case: Case) -> Case:
        record = CaseRecord(
            id=case.id,
            status=case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

        with self._session_factory() as session:
            session.add(record)
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            session.refresh(record)
            return _case_to_domain(record)

    def get_case(self, case_id: str) -> Case | None:
        with self._session_factory() as session:
            record = session.get(CaseRecord, case_id)
            return _case_to_domain(record) if record is not None else None

    def update_case_status(
        self,
        case_id: str,
        status: CaseStatus,
        updated_at: datetime,
    ) -> Case | None:
        with self._session_factory() as session:
            record = session.get(CaseRecord, case_id)
            if record is None:
                return None

            record.status = status
            record.updated_at = updated_at
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            session.refresh(record)
            return _case_to_domain(record)

    def create_document(self, document: Document) -> Document:
        record = DocumentRecord(
            id=document.id,
            case_id=document.case_id,
            document_type=document.document_type,
            file_path=document.file_path,
            page_count=document.page_count,
            ocr_status=document.ocr_status,
            uploaded_at=document.uploaded_at,
        )

        with self._session_factory() as session:
            session.add(record)
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            session.refresh(record)
            return _document_to_domain(record)

    def get_document(self, document_id: str) -> Document | None:
        with self._session_factory() as session:
            record = session.get(DocumentRecord, document_id)
            return _document_to_domain(record) if record is not None else None

    def list_documents_by_case_id(self, case_id: str) -> list[Document]:
        statement = select(DocumentRecord).where(
            DocumentRecord.case_id == case_id
        )
        with self._session_factory() as session:
            records = session.scalars(statement).all()
            return [_document_to_domain(record) for record in records]

    def document_type_exists(
        self,
        case_id: str,
        document_type: DocumentType,
    ) -> bool:
        statement = (
            select(DocumentRecord.id)
            .where(
                DocumentRecord.case_id == case_id,
                DocumentRecord.document_type == document_type,
            )
            .limit(1)
        )
        with self._session_factory() as session:
            return session.scalar(statement) is not None
