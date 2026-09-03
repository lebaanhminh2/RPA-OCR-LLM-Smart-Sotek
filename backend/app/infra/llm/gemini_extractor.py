import json
import os
import time
from collections.abc import Callable
from typing import Protocol, Self

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from app.domain.models import OCRBlock
from app.domain.ports.llm_provider import (
    MVP_FIELD_CODES,
    MVP_FIELD_SOURCE_RULES,
    LLMDocumentInput,
    LLMExtractedField,
    LLMProvider,
)
from app.infra.llm.address_grounding import (
    AddressEvidenceScope,
    build_loan_address_scopes,
    ground_address_sources,
)

GEMINI_MODEL = "gemini-3.5-flash-lite"

_SYSTEM_INSTRUCTION = """
Bạn trích xuất dữ liệu thô từ OCR của hồ sơ vay theo lương.

Quy tắc bắt buộc:
- Trả đúng một kết quả cho mỗi field_code được yêu cầu, không thêm field.
- Chỉ dùng nội dung trong các OCR block và giữ ngữ cảnh document_type.
- source_ids chỉ được chọn từ source_id có trong input; không tạo ID hay bbox mới.
- Không tìm thấy bằng chứng thì value=null và source_ids=[].
- Có value thì value phải là chuỗi khác rỗng và source_ids có ít nhất một ID.
- CHECKBOX_SELECTION là lựa chọn đã được OMR local xác nhận. Không suy đoán
  checkbox khác từ TEXT hoặc từ lựa chọn không xuất hiện.
- muc_dich_vay có nhiều lựa chọn thì value là JSON array đã serialize thành chuỗi,
  ví dụ [\"Sửa nhà\",\"Học tập\"].
- Với so_tien_vay_de_nghi, muc_luong_gross, thu_nhap_thuc_lanh_hang_thang và
  chi_phi_sinh_hoat_hang_thang: chỉ trả số tiền VND với dấu chấm phân cách hàng
  nghìn, không kèm đơn vị hoặc mô tả, ví dụ 15.000.000. Không tìm thấy số tiền
  chắc chắn thì trả null.
- Với email: được sửa lỗi OCR nhẹ và rõ ràng ở dấu phân cách như khoảng trắng
  hoặc ký tự bị đọc nhầm thành @. Kết quả phải có đúng một @, không có khoảng
  trắng và domain phải chứa dấu chấm. Không tự thay đổi nhiều ký tự của tên
  người dùng/domain; nếu có nhiều cách hiểu hợp lý thì trả null.
- Với mọi field dựa trên TEXT, ngoài ngoại lệ tiền và email nêu trên: chỉ lấy
  nguyên văn chuỗi hoặc chuỗi con từ các OCR block đã chọn. Được bỏ khoảng
  trắng thừa và thêm dấu phân cách khi ghép nhiều block; không sửa chính tả,
  dấu tiếng Việt, chữ hoa/thường, không thay ký tự và không mở rộng chữ viết
  tắt. Giữ nguyên lỗi OCR để chuyên viên review, không đoán và sửa hộ.
- Với mọi field địa chỉ: nếu biểu mẫu tách địa chỉ thành các ô có nhãn, phải
  ghép đủ mọi ô có nội dung theo thứ tự trên biểu mẫu: số nhà/đường, phường/xã,
  quận/huyện, tỉnh/thành phố. Không bỏ thành phần đã có OCR evidence và
  source_ids phải chứa mọi OCR block đóng góp vào giá trị, không chứa block chỉ
  có nhãn. Giữ nguyên text của từng thành phần và không suy diễn ô còn trống.
- Khi address_evidence_scopes có field tương ứng, nếu lấy địa chỉ từ document
  được chỉ định thì phải dùng đủ và chỉ dùng required_value_source_ids theo
  đúng thứ tự. Không thay source bằng block có cùng text ở section khác.
- Ngoài hai ngoại lệ tiền và email, không chuẩn hoá field hoặc suy diễn ngoài
  nội dung tài liệu.
""".strip()

_SOURCE_GROUNDING_INSTRUCTION = """
Enforce field_source_rules exactly for every returned source_id.
A TEXT block containing a printed checkbox label or option is not evidence that
the option was selected. Only CHECKBOX_SELECTION proves a selection on the loan
application. When no allowed evidence exists, return value=null and
source_ids=[].
""".strip()


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiResponseError(RuntimeError):
    pass


class GeminiRateLimitError(RuntimeError):
    pass


class GeminiFieldOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_code: str
    value: str | None
    source_ids: list[str]


class GeminiExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[GeminiFieldOutput]

    @model_validator(mode="after")
    def validate_field_catalog(self) -> Self:
        returned_codes = [field.field_code for field in self.fields]
        if len(returned_codes) != len(set(returned_codes)):
            raise ValueError("Duplicate field_code in Gemini response")

        expected = set(MVP_FIELD_CODES)
        returned = set(returned_codes)
        if returned != expected:
            missing = sorted(expected - returned)
            unexpected = sorted(returned - expected)
            raise ValueError(
                f"Gemini response field catalog mismatch: "
                f"missing={missing}, unexpected={unexpected}"
            )
        return self


class _GenerateContent(Protocol):
    def __call__(
        self,
        *,
        model: str,
        contents: str,
        config: types.GenerateContentConfig,
    ) -> types.GenerateContentResponse: ...


class GeminiExtractor(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        generate_content: _GenerateContent | None = None,
        max_attempts: int = 3,
        initial_backoff_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds must not be negative")

        self._client: genai.Client | None = None
        if generate_content is None:
            resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not resolved_api_key:
                raise GeminiConfigurationError("GEMINI_API_KEY is required")
            self._client = genai.Client(api_key=resolved_api_key)
            generate_content = self._client.models.generate_content

        self._generate_content = generate_content
        self._max_attempts = max_attempts
        self._initial_backoff_seconds = initial_backoff_seconds
        self._sleep = sleep

    def extract(
        self,
        documents: list[LLMDocumentInput],
    ) -> list[LLMExtractedField]:
        self._validate_documents(documents)
        address_scopes = build_loan_address_scopes(documents)
        prompt = self._build_prompt(documents, address_scopes)
        response = self._generate_with_retry(prompt)

        if not response.text:
            raise GeminiResponseError("Gemini returned an empty response")

        try:
            parsed = GeminiExtractionResponse.model_validate_json(response.text)
        except ValidationError as exc:
            raise GeminiResponseError("Gemini returned an invalid response") from exc

        fields_by_code = {field.field_code: field for field in parsed.fields}
        fields = [
            LLMExtractedField(
                field_code=field_code,
                value=fields_by_code[field_code].value,
                source_ids=fields_by_code[field_code].source_ids,
            )
            for field_code in MVP_FIELD_CODES
        ]
        return ground_address_sources(fields, documents, address_scopes)

    def _generate_with_retry(self, prompt: str) -> types.GenerateContentResponse:
        config = types.GenerateContentConfig(
            system_instruction=(
                f"{_SYSTEM_INSTRUCTION}\n{_SOURCE_GROUNDING_INSTRUCTION}"
            ),
            response_mime_type="application/json",
            response_json_schema=(
                GeminiExtractionResponse.model_json_schema()
            ),
            temperature=0,
        )

        for attempt in range(self._max_attempts):
            try:
                return self._generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=config,
                )
            except errors.APIError as exc:
                if exc.code != 429:
                    raise
                if attempt == self._max_attempts - 1:
                    raise GeminiRateLimitError(
                        f"Gemini rate limit persisted after "
                        f"{self._max_attempts} attempts"
                    ) from exc
                delay = self._initial_backoff_seconds * (2**attempt)
                self._sleep(delay)

        raise AssertionError("Retry loop exited unexpectedly")

    @staticmethod
    def _validate_documents(
        documents: list[LLMDocumentInput],
    ) -> None:
        source_ids: set[str] = set()
        for document in documents:
            for block in document.blocks:
                if block.document_id != document.document_id:
                    raise ValueError(
                        f"OCR block {block.id} does not belong to "
                        f"document {document.document_id}"
                    )
                if block.id in source_ids:
                    raise ValueError(f"Duplicate OCR source ID: {block.id}")
                source_ids.add(block.id)

    @staticmethod
    def _build_prompt(
        documents: list[LLMDocumentInput],
        address_scopes: dict[str, AddressEvidenceScope],
    ) -> str:
        payload = {
            "required_field_codes": list(MVP_FIELD_CODES),
            "field_source_rules": {
                field_code: [
                    {
                        "document_type": document_type.value,
                        "block_kind": block_kind.value,
                    }
                    for document_type, block_kind in sorted(
                        constraints,
                        key=lambda item: (item[0].value, item[1].value),
                    )
                ]
                for field_code, constraints in MVP_FIELD_SOURCE_RULES.items()
            },
            "address_evidence_scopes": {
                field_code: {
                    "document_id": scope.document_id,
                    "page_number": scope.page_number,
                    "required_value_source_ids": list(scope.source_ids),
                }
                for field_code, scope in address_scopes.items()
            },
            "documents": [
                {
                    "document_id": document.document_id,
                    "document_type": document.document_type.value,
                    "blocks": [
                        GeminiExtractor._serialize_block(block)
                        for block in document.blocks
                    ],
                }
                for document in documents
            ],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _serialize_block(block: OCRBlock) -> dict[str, object]:
        return {
            "source_id": block.id,
            "block_kind": block.block_kind.value,
            "page_number": block.page_number,
            "text": block.text,
            "bbox": {
                "x": block.bbox_x,
                "y": block.bbox_y,
                "width": block.bbox_width,
                "height": block.bbox_height,
            },
            "confidence": block.confidence,
        }
