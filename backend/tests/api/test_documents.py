from collections.abc import Iterator
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.background import BackgroundTasks
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.api.documents import create_documents_router
from app.domain.models import (
    Case,
    CaseStatus,
    Document,
    DocumentOcrStatus,
    DocumentType,
    OCRBlock,
)
from app.domain.services.case_service import CaseService
from app.domain.services.document_service import DocumentService
from app.domain.services.extraction_service import ExtractionService

ApiFixture = tuple[TestClient, "FakeRepository", Case, Path]


class FakeOCRProvider:
    def extract(
        self,
        document_id: str,
        document_type: DocumentType,
        file_path: str,
    ) -> list[OCRBlock]:
        return []


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

    def get_document(self, document_id: str) -> Document | None:
        return next(
            (
                document
                for document in self.documents
                if document.id == document_id
            ),
            None,
        )

    def update_document_ocr_status(
        self,
        document_id: str,
        status: DocumentOcrStatus,
    ) -> Document | None:
        for document in self.documents:
            if document.id == document_id:
                document.ocr_status = status
                return document
        return None

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

    def create_ocr_blocks(self, blocks: list[OCRBlock]) -> list[OCRBlock]:
        return blocks

    def list_ocr_blocks_by_document_id(
        self,
        document_id: str,
    ) -> list[OCRBlock]:
        return []


@pytest.fixture
def api(tmp_path: Path) -> Iterator[ApiFixture]:
    repository = FakeRepository()
    case_service = CaseService(repository)
    document_service = DocumentService(repository)
    extraction_service = ExtractionService(repository, FakeOCRProvider())
    case = case_service.create_case()
    upload_root = tmp_path / "uploads"
    test_app = FastAPI()
    test_app.include_router(
        create_documents_router(
            case_service,
            document_service,
            lambda: extraction_service,
            upload_root,
        )
    )

    with TestClient(test_app) as client:
        yield client, repository, case, upload_root


def test_valid_image_upload_persists_file_and_document(
    api: ApiFixture,
) -> None:
    client, repository, case, upload_root = api
    image_content = b"synthetic-image-content"

    response = client.post(
        f"/cases/{case.id}/documents",
        data={"document_type": "CCCD_FRONT"},
        files={"file": ("front.png", image_content, "image/png")},
    )

    response_data = response.json()
    assert response.status_code == 201
    assert set(response_data) == {
        "id",
        "case_id",
        "document_type",
        "file_path",
        "page_count",
        "ocr_status",
        "uploaded_at",
    }
    assert response_data["case_id"] == case.id
    assert response_data["document_type"] == "CCCD_FRONT"
    assert response_data["page_count"] == 1
    assert response_data["ocr_status"] == "PENDING"
    datetime.fromisoformat(response_data["uploaded_at"])

    stored_path = Path(response_data["file_path"])
    assert stored_path.parent == upload_root.resolve()
    assert stored_path.name != "front.png"
    assert stored_path.read_bytes() == image_content
    assert repository.documents == [
        Document(
            id=response_data["id"],
            case_id=case.id,
            document_type=DocumentType.CCCD_FRONT,
            file_path=str(stored_path),
            page_count=1,
            ocr_status=DocumentOcrStatus.PENDING,
            uploaded_at=datetime.fromisoformat(response_data["uploaded_at"]),
        )
    ]


def test_valid_multipage_pdf_uses_actual_page_count(
    api: ApiFixture,
) -> None:
    client, repository, case, _ = api
    pdf_content = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    writer.write(pdf_content)

    response = client.post(
        f"/cases/{case.id}/documents",
        data={"document_type": "LOAN_APPLICATION"},
        files={
            "file": (
                "loan-application.pdf",
                pdf_content.getvalue(),
                "application/pdf",
            )
        },
    )

    response_data = response.json()
    assert response.status_code == 201
    assert response_data["page_count"] == 2
    assert Path(response_data["file_path"]).is_file()
    assert repository.documents[0].page_count == 2


def test_missing_case_returns_404_without_record_or_orphan_file(
    api: ApiFixture,
) -> None:
    client, repository, _, upload_root = api

    response = client.post(
        "/cases/missing-case/documents",
        data={"document_type": "CCCD_FRONT"},
        files={"file": ("front.png", b"image", "image/png")},
    )

    assert response.status_code == 404
    assert repository.documents == []
    assert list(upload_root.iterdir()) == []


def test_duplicate_document_type_returns_409_and_removes_rejected_file(
    api: ApiFixture,
) -> None:
    client, repository, case, upload_root = api
    first_response = client.post(
        f"/cases/{case.id}/documents",
        data={"document_type": "CCCD_FRONT"},
        files={"file": ("front.png", b"first-image", "image/png")},
    )
    first_path = Path(first_response.json()["file_path"])

    duplicate_response = client.post(
        f"/cases/{case.id}/documents",
        data={"document_type": "CCCD_FRONT"},
        files={"file": ("replacement.png", b"second-image", "image/png")},
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert len(repository.documents) == 1
    assert first_path.read_bytes() == b"first-image"
    assert list(upload_root.iterdir()) == [first_path]


def test_four_required_uploads_transition_case_to_processing(
    api: ApiFixture,
) -> None:
    client, repository, case, _ = api
    required_types = (
        DocumentType.CCCD_FRONT,
        DocumentType.CCCD_BACK,
        DocumentType.LOAN_APPLICATION,
        DocumentType.LABOR_CONTRACT,
    )

    for document_type in required_types:
        response = client.post(
            f"/cases/{case.id}/documents",
            data={"document_type": document_type.value},
            files={
                "file": (
                    f"{document_type.value.lower()}.png",
                    b"synthetic-image",
                    "image/png",
                )
            },
        )
        assert response.status_code == 201

    assert len(repository.documents) == 4
    assert repository.cases[case.id].status is CaseStatus.PROCESSING


def test_fourth_upload_schedules_ocr_without_calling_it_inline(
    api: ApiFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, case, _ = api
    scheduled: list[tuple[object, tuple[object, ...], dict[str, object]]] = []

    def capture_task(
        _: BackgroundTasks,
        function: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        scheduled.append((function, args, kwargs))

    monkeypatch.setattr(BackgroundTasks, "add_task", capture_task)

    for document_type in (
        DocumentType.CCCD_FRONT,
        DocumentType.CCCD_BACK,
        DocumentType.LOAN_APPLICATION,
        DocumentType.LABOR_CONTRACT,
    ):
        response = client.post(
            f"/cases/{case.id}/documents",
            data={"document_type": document_type.value},
            files={
                "file": (
                    f"{document_type.value.lower()}.png",
                    b"synthetic-image",
                    "image/png",
                )
            },
        )
        assert response.status_code == 201

    assert len(scheduled) == 1
    scheduled_function, scheduled_args, scheduled_kwargs = scheduled[0]
    assert getattr(scheduled_function, "__name__", None) == "process_case_ocr"
    assert scheduled_args == (case.id,)
    assert scheduled_kwargs == {}


def test_unsupported_file_returns_415_without_persisting_or_storing(
    api: ApiFixture,
) -> None:
    client, repository, case, upload_root = api

    response = client.post(
        f"/cases/{case.id}/documents",
        data={"document_type": "CCCD_FRONT"},
        files={"file": ("notes.txt", b"not-a-document", "text/plain")},
    )

    assert response.status_code == 415
    assert repository.documents == []
    assert not upload_root.exists()


def test_malformed_pdf_returns_400_without_persisting_or_storing(
    api: ApiFixture,
) -> None:
    client, repository, case, upload_root = api

    response = client.post(
        f"/cases/{case.id}/documents",
        data={"document_type": "LOAN_APPLICATION"},
        files={
            "file": (
                "malformed.pdf",
                b"this-is-not-a-pdf",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert repository.documents == []
    assert not upload_root.exists()


@pytest.mark.parametrize(
    ("filename", "content", "expected_media_type"),
    [
        ("synthetic.pdf", b"synthetic-pdf-bytes", "application/pdf"),
        ("synthetic.png", b"synthetic-image-bytes", "image/png"),
    ],
)
def test_get_document_file_returns_exact_bytes_and_media_type(
    api: ApiFixture,
    filename: str,
    content: bytes,
    expected_media_type: str,
) -> None:
    client, repository, case, upload_root = api
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_path = upload_root / filename
    stored_path.write_bytes(content)
    document = Document(
        id=f"document-{stored_path.suffix[1:]}",
        case_id=case.id,
        document_type=DocumentType.CCCD_FRONT,
        file_path=str(stored_path),
        page_count=1,
        ocr_status=DocumentOcrStatus.PENDING,
        uploaded_at=datetime(2026, 9, 1, 12, 0),
    )
    repository.documents.append(document)

    response = client.get(f"/documents/{document.id}/file")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == expected_media_type


def test_get_document_file_returns_404_for_unknown_document(
    api: ApiFixture,
) -> None:
    client, _, _, _ = api

    response = client.get("/documents/missing-document/file")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document not found: missing-document"
    }
