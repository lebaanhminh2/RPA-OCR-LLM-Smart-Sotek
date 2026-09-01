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
