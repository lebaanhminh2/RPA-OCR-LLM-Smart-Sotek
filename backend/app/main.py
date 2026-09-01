from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.cases import create_cases_router
from app.api.documents import create_documents_router
from app.domain.services.case_service import CaseService
from app.domain.services.document_service import DocumentService
from app.infra.db.database import (
    SessionFactory,
    engine,
    verify_database_connection,
)
from app.infra.db.orm_models import Base
from app.infra.db.sqlite_repository import SQLiteRepository


class HealthResponse(BaseModel):
    status: Literal["ok"]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    verify_database_connection(engine)
    Base.metadata.create_all(engine)
    try:
        yield
    finally:
        engine.dispose()


repository = SQLiteRepository(SessionFactory)
case_service = CaseService(repository)
document_service = DocumentService(repository)
upload_root = Path(__file__).resolve().parents[1] / "uploads"

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(create_cases_router(case_service))
app.include_router(
    create_documents_router(case_service, document_service, upload_root)
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
