from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class CaseStatus(str, Enum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentType(str, Enum):
    CCCD_FRONT = "CCCD_FRONT"
    CCCD_BACK = "CCCD_BACK"
    LOAN_APPLICATION = "LOAN_APPLICATION"
    LABOR_CONTRACT = "LABOR_CONTRACT"


class DocumentOcrStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"


class OCRBlockKind(str, Enum):
    TEXT = "TEXT"
    CHECKBOX_SELECTION = "CHECKBOX_SELECTION"


@dataclass
class Case:
    id: str
    status: CaseStatus
    created_at: datetime
    updated_at: datetime


@dataclass
class Document:
    id: str
    case_id: str
    document_type: DocumentType
    file_path: str
    page_count: int
    ocr_status: DocumentOcrStatus
    uploaded_at: datetime


@dataclass(frozen=True)
class OCRBlock:
    id: str
    document_id: str
    page_number: int
    text: str
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    confidence: float
    created_at: datetime
    block_kind: OCRBlockKind = OCRBlockKind.TEXT
