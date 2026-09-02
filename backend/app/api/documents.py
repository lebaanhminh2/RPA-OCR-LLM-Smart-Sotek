import re
from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.domain.models import DocumentOcrStatus, DocumentType
from app.domain.services.case_service import (
    CaseNotFoundError,
    CaseService,
    DuplicateDocumentTypeError,
)
from app.domain.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
)
from app.domain.services.extraction_service import ExtractionService


class DocumentResponse(BaseModel):
    id: str
    case_id: str
    document_type: DocumentType
    file_path: str
    page_count: int
    ocr_status: DocumentOcrStatus
    uploaded_at: datetime


def _get_page_count(
    content: bytes,
    content_type: str | None,
    filename: str | None,
) -> tuple[int, bool]:
    media_type = (content_type or "").partition(";")[0].strip().lower()
    suffix = Path(filename or "").suffix.lower()
    is_pdf = media_type == "application/pdf" or suffix == ".pdf"

    if is_pdf:
        try:
            return len(PdfReader(BytesIO(content)).pages), True
        except PdfReadError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded PDF is malformed.",
            ) from error

    if media_type.startswith("image/"):
        return 1, False

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Only PDF and image files are supported.",
    )


def _get_safe_suffix(filename: str | None, is_pdf: bool) -> str:
    if is_pdf:
        return ".pdf"

    suffix = Path(filename or "").suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ""


def _store_file(
    upload_root: Path,
    content: bytes,
    suffix: str,
) -> Path:
    resolved_root = upload_root.resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)
    stored_path = resolved_root / f"{uuid4()}{suffix}"
    stored_path.write_bytes(content)
    return stored_path


def create_documents_router(
    case_service: CaseService,
    document_service: DocumentService,
    extraction_service_provider: Callable[[], ExtractionService],
    upload_root: Path,
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/cases/{case_id}/documents",
        response_model=DocumentResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def upload_document(
        case_id: str,
        background_tasks: BackgroundTasks,
        document_type: Annotated[DocumentType, Form()],
        file: Annotated[UploadFile, File()],
    ) -> DocumentResponse:
        content = file.file.read()
        page_count, is_pdf = _get_page_count(
            content,
            file.content_type,
            file.filename,
        )
        stored_path = _store_file(
            upload_root,
            content,
            _get_safe_suffix(file.filename, is_pdf),
        )

        try:
            document = case_service.add_document(
                case_id=case_id,
                document_type=document_type,
                file_path=str(stored_path),
                page_count=page_count,
            )
        except CaseNotFoundError as error:
            stored_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except DuplicateDocumentTypeError as error:
            stored_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        extraction_service = extraction_service_provider()
        if extraction_service.is_case_ready_for_ocr(case_id):
            background_tasks.add_task(
                extraction_service.process_case_ocr,
                case_id,
            )

        return DocumentResponse(
            id=document.id,
            case_id=document.case_id,
            document_type=document.document_type,
            file_path=document.file_path,
            page_count=document.page_count,
            ocr_status=document.ocr_status,
            uploaded_at=document.uploaded_at,
        )

    @router.get(
        "/documents/{document_id}/file",
        response_class=FileResponse,
    )
    def get_document_file(document_id: str) -> FileResponse:
        try:
            document = document_service.get_document(document_id)
        except DocumentNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error

        return FileResponse(document.file_path)

    return router
