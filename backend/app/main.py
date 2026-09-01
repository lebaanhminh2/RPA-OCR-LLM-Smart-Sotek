from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.infra.db.database import engine, verify_database_connection


class HealthResponse(BaseModel):
    status: Literal["ok"]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    verify_database_connection(engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
