from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.cases import create_cases_router
from app.api.documents import create_documents_router
from app.api.review import create_review_router
from app.domain.services.case_service import CaseService
from app.domain.services.document_service import DocumentService
from app.domain.services.extraction_service import ExtractionService
from app.domain.services.review_service import ReviewService
from app.infra.db.database import (
    SessionFactory,
    engine,
    ensure_ocr_block_kind_column,
    verify_database_connection,
)
from app.infra.db.orm_models import Base
from app.infra.db.sqlite_repository import SQLiteRepository
from app.infra.llm.gemini_extractor import GeminiExtractor
from app.infra.ocr.local_ocr_adapter import LocalOCRAdapter

_extraction_service: ExtractionService | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _extraction_service

    verify_database_connection(engine)
    Base.metadata.create_all(engine)
    ensure_ocr_block_kind_column(engine)
    try:
        _extraction_service = ExtractionService(
            repository,
            LocalOCRAdapter(),
            GeminiExtractor(),
        )
        yield
    finally:
        _extraction_service = None
        engine.dispose()


repository = SQLiteRepository(SessionFactory)
case_service = CaseService(repository)
document_service = DocumentService(repository)
review_service = ReviewService(repository)
upload_root = Path(__file__).resolve().parents[1] / "uploads"


def get_extraction_service() -> ExtractionService:
    if _extraction_service is None:
        raise RuntimeError("Extraction service is unavailable before startup.")
    return _extraction_service

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)
app.include_router(create_cases_router(case_service))
app.include_router(
    create_documents_router(
        case_service,
        document_service,
        get_extraction_service,
        upload_root,
    )
)
app.include_router(create_review_router(review_service))


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
