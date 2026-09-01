from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.domain.models import CaseStatus
from app.domain.services.case_service import CaseNotFoundError, CaseService


class CaseResponse(BaseModel):
    id: str
    status: CaseStatus
    created_at: datetime
    updated_at: datetime


def create_cases_router(case_service: CaseService) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/cases",
        response_model=CaseResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_case() -> CaseResponse:
        case = case_service.create_case()
        return CaseResponse(
            id=case.id,
            status=case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    @router.get(
        "/cases/{case_id}",
        response_model=CaseResponse,
    )
    def get_case(case_id: str) -> CaseResponse:
        try:
            case = case_service.get_case(case_id)
        except CaseNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error

        return CaseResponse(
            id=case.id,
            status=case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    return router
