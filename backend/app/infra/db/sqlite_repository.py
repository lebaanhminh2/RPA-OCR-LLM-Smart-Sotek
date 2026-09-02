from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
    OCRBlock,
)
from app.domain.ports.repository import Repository
from app.infra.db.orm_models import CaseRecord, DocumentRecord, OCRBlockRecord


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


def _to_utc_storage(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _from_utc_storage(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _ocr_block_to_domain(record: OCRBlockRecord) -> OCRBlock:
    return OCRBlock(
        id=record.id,
        document_id=record.document_id,
        page_number=record.page_number,
        text=record.text,
        bbox_x=record.bbox_x,
        bbox_y=record.bbox_y,
        bbox_width=record.bbox_width,
        bbox_height=record.bbox_height,
        confidence=record.confidence,
        created_at=_from_utc_storage(record.created_at),
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

    def update_document_ocr_status(
        self,
        document_id: str,
        status: DocumentOcrStatus,
    ) -> Document | None:
        with self._session_factory() as session:
            record = session.get(DocumentRecord, document_id)
            if record is None:
                return None

            record.ocr_status = status
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            session.refresh(record)
            return _document_to_domain(record)

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

    def create_ocr_blocks(self, blocks: list[OCRBlock]) -> list[OCRBlock]:
        if not blocks:
            return []

        records = [
            OCRBlockRecord(
                id=block.id,
                document_id=block.document_id,
                page_number=block.page_number,
                text=block.text,
                bbox_x=block.bbox_x,
                bbox_y=block.bbox_y,
                bbox_width=block.bbox_width,
                bbox_height=block.bbox_height,
                confidence=block.confidence,
                created_at=_to_utc_storage(block.created_at),
            )
            for block in blocks
        ]
        with self._session_factory() as session:
            session.add_all(records)
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            for record in records:
                session.refresh(record)
            return [_ocr_block_to_domain(record) for record in records]

    def list_ocr_blocks_by_document_id(
        self,
        document_id: str,
    ) -> list[OCRBlock]:
        statement = (
            select(OCRBlockRecord)
            .where(OCRBlockRecord.document_id == document_id)
            .order_by(
                OCRBlockRecord.page_number,
                OCRBlockRecord.created_at,
                OCRBlockRecord.id,
            )
        )
        with self._session_factory() as session:
            records = session.scalars(statement).all()
            return [_ocr_block_to_domain(record) for record in records]
