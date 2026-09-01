from datetime import datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.cases import create_cases_router
from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentType,
)
from app.domain.services.case_service import CaseService


class FakeRepository:
    def __init__(self) -> None:
        self.cases: dict[str, Case] = {}
        self.documents: list[Document] = []

    def create_case(self, case: Case) -> Case:
        self.cases[case.id] = case
        return case

    def get_case(self, case_id: str) -> Case | None:
        return self.cases.get(case_id)

    def update_case_status(
        self,
        case_id: str,
        status: CaseStatus,
        updated_at: datetime,
    ) -> Case | None:
        case = self.cases.get(case_id)
        if case is None:
            return None

        updated_case = Case(
            id=case.id,
            status=status,
            created_at=case.created_at,
            updated_at=updated_at,
        )
        self.cases[case_id] = updated_case
        return updated_case

    def create_document(self, document: Document) -> Document:
        self.documents.append(document)
        return document

    def list_documents_by_case_id(self, case_id: str) -> list[Document]:
        return [
            document
            for document in self.documents
            if document.case_id == case_id
        ]

    def document_type_exists(
        self,
        case_id: str,
        document_type: DocumentType,
    ) -> bool:
        return any(
            document.case_id == case_id
            and document.document_type is document_type
            for document in self.documents
        )


def test_create_case_returns_created_case_from_case_service() -> None:
    repository = FakeRepository()
    case_service = CaseService(repository)
    test_app = FastAPI()
    test_app.include_router(create_cases_router(case_service))

    with TestClient(test_app) as client:
        response = client.post("/cases")

    response_data = response.json()
    assert response.status_code == 201
    assert set(response_data) == {
        "id",
        "status",
        "created_at",
        "updated_at",
    }
    assert response_data["status"] == "UPLOADING"

    case_id = response_data["id"]
    parsed_id = UUID(case_id)
    assert parsed_id.version == 4
    assert str(parsed_id) == case_id

    created_at = datetime.fromisoformat(response_data["created_at"])
    updated_at = datetime.fromisoformat(response_data["updated_at"])
    assert created_at == updated_at

    persisted_case = repository.cases[case_id]
    assert persisted_case.id == case_id
    assert persisted_case.status is CaseStatus.UPLOADING
    assert persisted_case.created_at == created_at
    assert persisted_case.updated_at == updated_at


def test_get_case_returns_existing_case_from_case_service() -> None:
    repository = FakeRepository()
    case_service = CaseService(repository)
    case = case_service.create_case()
    test_app = FastAPI()
    test_app.include_router(create_cases_router(case_service))

    with TestClient(test_app) as client:
        response = client.get(f"/cases/{case.id}")

    response_data = response.json()
    assert response.status_code == 200
    assert set(response_data) == {
        "id",
        "status",
        "created_at",
        "updated_at",
    }
    assert response_data == {
        "id": case.id,
        "status": "UPLOADING",
        "created_at": case.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": case.updated_at.isoformat().replace("+00:00", "Z"),
    }


def test_get_case_returns_404_when_case_does_not_exist() -> None:
    repository = FakeRepository()
    case_service = CaseService(repository)
    test_app = FastAPI()
    test_app.include_router(create_cases_router(case_service))

    with TestClient(test_app) as client:
        response = client.get("/cases/missing-case")

    assert response.status_code == 404
    assert response.json() == {"detail": "Case not found: missing-case"}
