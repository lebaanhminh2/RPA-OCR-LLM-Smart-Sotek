import json
from datetime import UTC, datetime
from typing import cast

import pytest
from google.genai import errors, types

from app.domain.models import DocumentType, OCRBlock, OCRBlockKind
from app.domain.ports.llm_provider import MVP_FIELD_CODES, LLMDocumentInput
from app.infra.llm.gemini_extractor import (
    GEMINI_MODEL,
    GeminiConfigurationError,
    GeminiExtractionResponse,
    GeminiExtractor,
    GeminiRateLimitError,
    GeminiResponseError,
)


class FakeGenerateContent:
    def __init__(self, outcomes: list[str | Exception]) -> None:
        self._outcomes = outcomes
        self.calls: list[dict[str, object]] = []

    def __call__(
        self,
        *,
        model: str,
        contents: str,
        config: types.GenerateContentConfig,
    ) -> types.GenerateContentResponse:
        self.calls.append(
            {"model": model, "contents": contents, "config": config}
        )
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return cast(
            types.GenerateContentResponse,
            type("FakeResponse", (), {"text": outcome})(),
        )


def _documents() -> list[LLMDocumentInput]:
    return [
        LLMDocumentInput(
            document_id="document-cccd-front",
            document_type=DocumentType.CCCD_FRONT,
            blocks=[
                OCRBlock(
                    id="source-ho-ten",
                    document_id="document-cccd-front",
                    page_number=1,
                    text="Họ và tên: NGUYỄN VĂN AN",
                    bbox_x=0.1,
                    bbox_y=0.2,
                    bbox_width=0.4,
                    bbox_height=0.05,
                    confidence=0.98,
                    created_at=datetime(2026, 9, 2, tzinfo=UTC),
                )
            ],
        ),
        LLMDocumentInput(
            document_id="document-loan",
            document_type=DocumentType.LOAN_APPLICATION,
            blocks=[
                OCRBlock(
                    id="source-married",
                    document_id="document-loan",
                    page_number=1,
                    text="Đã kết hôn",
                    bbox_x=0.2,
                    bbox_y=0.3,
                    bbox_width=0.2,
                    bbox_height=0.04,
                    confidence=0.95,
                    created_at=datetime(2026, 9, 2, tzinfo=UTC),
                    block_kind=OCRBlockKind.CHECKBOX_SELECTION,
                )
            ],
        ),
    ]


def _response_json(
    values: dict[str, tuple[str, list[str]]] | None = None,
) -> str:
    values = values or {}
    return json.dumps(
        {
            "fields": [
                {
                    "field_code": field_code,
                    "value": values.get(field_code, (None, []))[0],
                    "source_ids": values.get(field_code, (None, []))[1],
                }
                for field_code in MVP_FIELD_CODES
            ]
        },
        ensure_ascii=False,
    )


def test_extract_uses_document_aware_prompt_and_structured_output() -> None:
    generate_content = FakeGenerateContent(
        [
            _response_json(
                {
                    "ho_ten": ("NGUYỄN VĂN AN", ["source-ho-ten"]),
                    "tinh_trang_hon_nhan": (
                        "Đã kết hôn",
                        ["source-married"],
                    ),
                }
            )
        ]
    )
    extractor = GeminiExtractor(generate_content=generate_content)

    result = extractor.extract(_documents())

    assert len(result) == 40
    assert [field.field_code for field in result] == list(MVP_FIELD_CODES)
    assert result[0].value == "NGUYỄN VĂN AN"
    assert result[0].source_ids == ["source-ho-ten"]

    call = generate_content.calls[0]
    assert GEMINI_MODEL == "gemini-3.5-flash-lite"
    assert call["model"] == GEMINI_MODEL
    prompt = json.loads(cast(str, call["contents"]))
    assert prompt["documents"][0]["document_type"] == "CCCD_FRONT"
    assert prompt["documents"][1]["blocks"][0]["block_kind"] == (
        "CHECKBOX_SELECTION"
    )
    assert prompt["documents"][0]["blocks"][0]["source_id"] == (
        "source-ho-ten"
    )

    config = cast(types.GenerateContentConfig, call["config"])
    assert config.response_mime_type == "application/json"
    assert config.response_schema is None
    assert config.response_json_schema == (
        GeminiExtractionResponse.model_json_schema()
    )
    assert config.temperature == 0


def test_extractor_retains_sdk_client_for_its_lifetime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generate_content = FakeGenerateContent([_response_json()])
    created_clients: list[object] = []

    class FakeModels:
        def __init__(self) -> None:
            self.generate_content = generate_content

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            assert api_key == "synthetic-api-key"
            self.models = FakeModels()
            created_clients.append(self)

    monkeypatch.setattr(
        "app.infra.llm.gemini_extractor.genai.Client",
        FakeClient,
    )

    extractor = GeminiExtractor(api_key="synthetic-api-key")

    assert extractor._client is created_clients[0]


def test_extract_rejects_incomplete_field_catalog() -> None:
    response = json.loads(_response_json())
    response["fields"].pop()
    generate_content = FakeGenerateContent([json.dumps(response)])
    extractor = GeminiExtractor(generate_content=generate_content)

    with pytest.raises(GeminiResponseError):
        extractor.extract(_documents())


def test_extract_preserves_value_without_source_for_domain_validation() -> None:
    generate_content = FakeGenerateContent(
        [_response_json({"ho_ten": ("NGUYỄN VĂN AN", [])})]
    )
    extractor = GeminiExtractor(generate_content=generate_content)

    result = extractor.extract(_documents())

    assert result[0].field_code == "ho_ten"
    assert result[0].value == "NGUYỄN VĂN AN"
    assert result[0].source_ids == []


def test_extract_preserves_invented_source_id_for_domain_validation() -> None:
    generate_content = FakeGenerateContent(
        [_response_json({"ho_ten": ("NGUYỄN VĂN AN", ["invented-id"])})]
    )
    extractor = GeminiExtractor(generate_content=generate_content)

    result = extractor.extract(_documents())

    assert result[0].field_code == "ho_ten"
    assert result[0].value == "NGUYỄN VĂN AN"
    assert result[0].source_ids == ["invented-id"]


def test_rate_limit_retries_with_finite_exponential_backoff() -> None:
    generate_content = FakeGenerateContent(
        [
            errors.ClientError(429, {"error": {"message": "quota"}}),
            errors.ClientError(429, {"error": {"message": "quota"}}),
            _response_json(),
        ]
    )
    sleep_delays: list[float] = []
    extractor = GeminiExtractor(
        generate_content=generate_content,
        initial_backoff_seconds=0.25,
        sleep=sleep_delays.append,
    )

    extractor.extract(_documents())

    assert len(generate_content.calls) == 3
    assert sleep_delays == [0.25, 0.5]


def test_rate_limit_stops_after_max_attempts() -> None:
    generate_content = FakeGenerateContent(
        [
            errors.ClientError(429, {"error": {"message": "quota"}}),
            errors.ClientError(429, {"error": {"message": "quota"}}),
            errors.ClientError(429, {"error": {"message": "quota"}}),
        ]
    )
    sleep_delays: list[float] = []
    extractor = GeminiExtractor(
        generate_content=generate_content,
        initial_backoff_seconds=0.25,
        sleep=sleep_delays.append,
    )

    with pytest.raises(GeminiRateLimitError, match="after 3 attempts"):
        extractor.extract(_documents())

    assert len(generate_content.calls) == 3
    assert sleep_delays == [0.25, 0.5]


def test_non_rate_limit_api_error_is_not_retried() -> None:
    generate_content = FakeGenerateContent(
        [errors.ClientError(400, {"error": {"message": "bad request"}})]
    )
    extractor = GeminiExtractor(generate_content=generate_content)

    with pytest.raises(errors.ClientError):
        extractor.extract(_documents())

    assert len(generate_content.calls) == 1


def test_api_key_is_required_without_injected_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(GeminiConfigurationError, match="GEMINI_API_KEY"):
        GeminiExtractor()
