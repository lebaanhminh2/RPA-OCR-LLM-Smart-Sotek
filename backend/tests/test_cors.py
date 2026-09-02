import pytest
from fastapi.testclient import TestClient

from app.domain.models import DocumentType, OCRBlock
from app.domain.ports.llm_provider import (
    MVP_FIELD_CODES,
    LLMDocumentInput,
    LLMExtractedField,
)
from app.main import app


class FakeOCRProvider:
    def extract(
        self,
        document_id: str,
        document_type: DocumentType,
        file_path: str,
    ) -> list[OCRBlock]:
        return []


class FakeLLMProvider:
    def extract(
        self,
        documents: list[LLMDocumentInput],
    ) -> list[LLMExtractedField]:
        return [
            LLMExtractedField(field_code=code, value=None, source_ids=[])
            for code in MVP_FIELD_CODES
        ]


@pytest.fixture(autouse=True)
def use_fake_ocr_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.main.LocalOCRAdapter",
        lambda: FakeOCRProvider(),
    )
    monkeypatch.setattr(
        "app.main.GeminiExtractor",
        lambda: FakeLLMProvider(),
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)
def test_allowed_frontend_origins_are_reflected(origin: str) -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers


def test_origin_outside_allow_list_is_not_reflected() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={"Origin": "http://example.com"},
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
