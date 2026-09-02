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
    ExtractedField,
    FieldSource,
    OCRBlock,
    ReviewAction,
)
from app.domain.ports.repository import (
    ExtractedFieldWithSources,
    FieldSourceEvidence,
    ReviewRepository,
)
from app.infra.db.orm_models import (
    CaseRecord,
    DocumentRecord,
    ExtractedFieldRecord,
    FieldSourceRecord,
    OCRBlockRecord,
    ReviewActionRecord,
)


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
        block_kind=record.block_kind,
        page_number=record.page_number,
        text=record.text,
        bbox_x=record.bbox_x,
        bbox_y=record.bbox_y,
        bbox_width=record.bbox_width,
        bbox_height=record.bbox_height,
        confidence=record.confidence,
        created_at=_from_utc_storage(record.created_at),
    )


def _extracted_field_to_domain(record: ExtractedFieldRecord) -> ExtractedField:
    return ExtractedField(
        id=record.id,
        case_id=record.case_id,
        field_code=record.field_code,
        original_value=record.original_value,
        current_value=record.current_value,
        created_at=_from_utc_storage(record.created_at),
        updated_at=_from_utc_storage(record.updated_at),
    )


def _field_source_to_domain(record: FieldSourceRecord) -> FieldSource:
    return FieldSource(
        id=record.id,
        extracted_field_id=record.extracted_field_id,
        ocr_block_id=record.ocr_block_id,
    )


def _review_action_to_domain(record: ReviewActionRecord) -> ReviewAction:
    return ReviewAction(
        id=record.id,
        case_id=record.case_id,
        extracted_field_id=record.extracted_field_id,
        action_type=record.action_type,
        previous_value=record.previous_value,
        new_value=record.new_value,
        created_at=_from_utc_storage(record.created_at),
    )


def _review_action_record(action: ReviewAction) -> ReviewActionRecord:
    return ReviewActionRecord(
        id=action.id,
        case_id=action.case_id,
        extracted_field_id=action.extracted_field_id,
        action_type=action.action_type,
        previous_value=action.previous_value,
        new_value=action.new_value,
        created_at=_to_utc_storage(action.created_at),
    )


class SQLiteRepository(ReviewRepository):
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
                block_kind=block.block_kind,
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

    def create_extracted_fields(
        self,
        fields: list[ExtractedField],
        sources: list[FieldSource],
    ) -> tuple[list[ExtractedField], list[FieldSource]]:
        if not fields:
            if sources:
                raise ValueError("Cannot create field sources without fields")
            return [], []

        field_ids = {field.id for field in fields}
        unknown_field_ids = {
            source.extracted_field_id
            for source in sources
            if source.extracted_field_id not in field_ids
        }
        if unknown_field_ids:
            raise ValueError(
                "Field sources must reference fields from the same batch: "
                f"{sorted(unknown_field_ids)}"
            )

        field_records = [
            ExtractedFieldRecord(
                id=field.id,
                case_id=field.case_id,
                field_code=field.field_code,
                original_value=field.original_value,
                current_value=field.current_value,
                created_at=_to_utc_storage(field.created_at),
                updated_at=_to_utc_storage(field.updated_at),
            )
            for field in fields
        ]
        source_records = [
            FieldSourceRecord(
                id=source.id,
                extracted_field_id=source.extracted_field_id,
                ocr_block_id=source.ocr_block_id,
            )
            for source in sources
        ]

        with self._session_factory() as session:
            session.add_all(field_records)
            try:
                session.flush()
                session.add_all(source_records)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            for field_record in field_records:
                session.refresh(field_record)
            for source_record in source_records:
                session.refresh(source_record)
            return (
                [
                    _extracted_field_to_domain(field_record)
                    for field_record in field_records
                ],
                [
                    _field_source_to_domain(source_record)
                    for source_record in source_records
                ],
            )

    def list_extracted_fields_with_sources_by_case_id(
        self,
        case_id: str,
    ) -> list[ExtractedFieldWithSources]:
        statement = (
            select(
                ExtractedFieldRecord,
                FieldSourceRecord,
                OCRBlockRecord,
            )
            .outerjoin(
                FieldSourceRecord,
                FieldSourceRecord.extracted_field_id
                == ExtractedFieldRecord.id,
            )
            .outerjoin(
                OCRBlockRecord,
                OCRBlockRecord.id == FieldSourceRecord.ocr_block_id,
            )
            .where(ExtractedFieldRecord.case_id == case_id)
            .order_by(
                ExtractedFieldRecord.created_at,
                ExtractedFieldRecord.field_code,
                ExtractedFieldRecord.id,
                FieldSourceRecord.id,
            )
        )

        grouped: dict[
            str,
            tuple[ExtractedField, list[FieldSourceEvidence]],
        ] = {}
        with self._session_factory() as session:
            rows = session.execute(statement)
            for field_record, source_record, block_record in rows:
                if field_record.id not in grouped:
                    grouped[field_record.id] = (
                        _extracted_field_to_domain(field_record),
                        [],
                    )
                if source_record is None:
                    continue
                if block_record is None:
                    raise RuntimeError(
                        f"OCR block {source_record.ocr_block_id} is missing"
                    )
                grouped[field_record.id][1].append(
                    FieldSourceEvidence(
                        field_source=_field_source_to_domain(source_record),
                        ocr_block=_ocr_block_to_domain(block_record),
                    )
                )

        return [
            ExtractedFieldWithSources(field=field, sources=tuple(sources))
            for field, sources in grouped.values()
        ]

    def get_extracted_field(
        self,
        extracted_field_id: str,
    ) -> ExtractedField | None:
        with self._session_factory() as session:
            record = session.get(ExtractedFieldRecord, extracted_field_id)
            return (
                _extracted_field_to_domain(record)
                if record is not None
                else None
            )

    def create_review_action(self, action: ReviewAction) -> ReviewAction:
        record = _review_action_record(action)
        with self._session_factory() as session:
            session.add(record)
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            session.refresh(record)
            return _review_action_to_domain(record)

    def list_review_actions_by_case_id(
        self,
        case_id: str,
    ) -> list[ReviewAction]:
        statement = (
            select(ReviewActionRecord)
            .where(ReviewActionRecord.case_id == case_id)
            .order_by(
                ReviewActionRecord.created_at,
                ReviewActionRecord.id,
            )
        )
        with self._session_factory() as session:
            records = session.scalars(statement).all()
            return [_review_action_to_domain(record) for record in records]

    def update_extracted_field_with_action(
        self,
        extracted_field_id: str,
        current_value: str | None,
        updated_at: datetime,
        action: ReviewAction,
    ) -> tuple[ExtractedField, ReviewAction] | None:
        with self._session_factory() as session:
            field_record = session.get(
                ExtractedFieldRecord,
                extracted_field_id,
            )
            if field_record is None:
                return None

            field_record.current_value = current_value
            field_record.updated_at = _to_utc_storage(updated_at)
            action_record = _review_action_record(action)
            session.add(action_record)
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            session.refresh(field_record)
            session.refresh(action_record)
            return (
                _extracted_field_to_domain(field_record),
                _review_action_to_domain(action_record),
            )

    def complete_case_with_action(
        self,
        case_id: str,
        updated_at: datetime,
        action: ReviewAction,
    ) -> tuple[Case, ReviewAction] | None:
        with self._session_factory() as session:
            case_record = session.get(CaseRecord, case_id)
            if case_record is None:
                return None

            case_record.status = CaseStatus.COMPLETED
            case_record.updated_at = _to_utc_storage(updated_at)
            action_record = _review_action_record(action)
            session.add(action_record)
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            session.refresh(case_record)
            session.refresh(action_record)
            return (
                _case_to_domain(case_record),
                _review_action_to_domain(action_record),
            )
