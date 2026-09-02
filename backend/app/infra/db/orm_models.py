from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.models import (
    CaseStatus,
    DocumentOcrStatus,
    DocumentType,
    OCRBlockKind,
)


class Base(DeclarativeBase):
    pass


class CaseRecord(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, native_enum=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("case_id", "document_type"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id"),
        nullable=False,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, native_enum=False),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ocr_status: Mapped[DocumentOcrStatus] = mapped_column(
        Enum(DocumentOcrStatus, native_enum=False),
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OCRBlockRecord(Base):
    __tablename__ = "ocr_blocks"
    __table_args__ = (
        CheckConstraint("page_number >= 1", name="ck_ocr_blocks_page_number"),
        CheckConstraint(
            "bbox_x >= 0.0 AND bbox_x <= 1.0",
            name="ck_ocr_blocks_bbox_x",
        ),
        CheckConstraint(
            "bbox_y >= 0.0 AND bbox_y <= 1.0",
            name="ck_ocr_blocks_bbox_y",
        ),
        CheckConstraint(
            "bbox_width >= 0.0 AND bbox_width <= 1.0",
            name="ck_ocr_blocks_bbox_width",
        ),
        CheckConstraint(
            "bbox_height >= 0.0 AND bbox_height <= 1.0",
            name="ck_ocr_blocks_bbox_height",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_ocr_blocks_confidence",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
    )
    block_kind: Mapped[OCRBlockKind] = mapped_column(
        Enum(OCRBlockKind, native_enum=False),
        nullable=False,
        default=OCRBlockKind.TEXT,
        server_default=OCRBlockKind.TEXT.value,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class ExtractedFieldRecord(Base):
    __tablename__ = "extracted_fields"
    __table_args__ = (UniqueConstraint("case_id", "field_code"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id"),
        nullable=False,
    )
    field_code: Mapped[str] = mapped_column(String, nullable=False)
    original_value: Mapped[str | None] = mapped_column(String, nullable=True)
    current_value: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class FieldSourceRecord(Base):
    __tablename__ = "field_sources"
    __table_args__ = (
        UniqueConstraint("extracted_field_id", "ocr_block_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    extracted_field_id: Mapped[str] = mapped_column(
        ForeignKey("extracted_fields.id"),
        nullable=False,
    )
    ocr_block_id: Mapped[str] = mapped_column(
        ForeignKey("ocr_blocks.id"),
        nullable=False,
    )
