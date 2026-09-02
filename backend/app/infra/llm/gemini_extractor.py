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
    LLMDocumentInput,
    LLMExtractedField,
    LLMProvider,
)

GEMINI_MODEL = "gemini-3.7-flash"
FIELD_CODES = (
    "ho_ten",
    "gioi_tinh",
    "ngay_sinh",
    "so_cccd",
    "ngay_cap_cccd",
    "co_quan_cap_cccd",
    "so_dien_thoai_di_dong",
    "email",
    "tinh_trang_hon_nhan",
    "trinh_do_hoc_van",
    "hinh_thuc_so_huu_nha",
    "dia_chi_thuong_tru",
    "dia_chi_hien_tai",
    "thoi_gian_cu_tru_hien_tai",
    "so_tien_vay_de_nghi",
    "so_tien_vay_de_nghi_bang_chu",
    "ngay_lam_don",
    "ky_han_vay",
    "muc_dich_vay",
    "chi_tiet_muc_dich_vay_khac",
    "phuong_thuc_giai_ngan",
    "loai_tai_khoan_nhan_giai_ngan",
    "ngan_hang_nhan_giai_ngan",
    "chi_nhanh_nhan_giai_ngan",
    "so_tai_khoan_nhan_giai_ngan",
    "ten_chu_tai_khoan_nhan_giai_ngan",
    "nghe_nghiep_chuyen_mon",
    "ten_don_vi_cong_tac",
    "ma_so_thue_cong_ty",
    "dia_chi_cong_ty",
    "dien_thoai_cong_ty",
    "chuc_vu",
    "loai_hop_dong_lao_dong",
    "ngay_bat_dau_lam_viec",
    "ngay_nhan_luong_hang_thang",
    "muc_luong_gross",
    "thu_nhap_thuc_lanh_hang_thang",
    "chi_phi_sinh_hoat_hang_thang",
    "hinh_thuc_nhan_luong",
    "so_nguoi_phu_thuoc",
)

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
- Không chuẩn hoá hoặc suy diễn ngoài nội dung tài liệu.
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

    @model_validator(mode="after")
    def validate_value_and_sources(self) -> Self:
        if self.value is None:
            if self.source_ids:
                raise ValueError("A null value must have no source_ids")
            return self

        if not self.value.strip():
            raise ValueError("A non-null value must not be blank")
        if not self.source_ids:
            raise ValueError("A non-null value must have at least one source_id")
        return self


class GeminiExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[GeminiFieldOutput]

    @model_validator(mode="after")
    def validate_field_catalog(self) -> Self:
        returned_codes = [field.field_code for field in self.fields]
        if len(returned_codes) != len(set(returned_codes)):
            raise ValueError("Duplicate field_code in Gemini response")

        expected = set(FIELD_CODES)
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

        if generate_content is None:
            resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not resolved_api_key:
                raise GeminiConfigurationError("GEMINI_API_KEY is required")
            client = genai.Client(api_key=resolved_api_key)
            generate_content = client.models.generate_content

        self._generate_content = generate_content
        self._max_attempts = max_attempts
        self._initial_backoff_seconds = initial_backoff_seconds
        self._sleep = sleep

    def extract(
        self,
        documents: list[LLMDocumentInput],
    ) -> list[LLMExtractedField]:
        source_ids = self._validate_and_collect_source_ids(documents)
        prompt = self._build_prompt(documents)
        response = self._generate_with_retry(prompt)

        if not response.text:
            raise GeminiResponseError("Gemini returned an empty response")

        try:
            parsed = GeminiExtractionResponse.model_validate_json(response.text)
        except ValidationError as exc:
            raise GeminiResponseError("Gemini returned an invalid response") from exc

        for field in parsed.fields:
            invalid_source_ids = set(field.source_ids) - source_ids
            if invalid_source_ids:
                raise GeminiResponseError(
                    "Gemini returned source_ids that were not present in the input: "
                    f"{sorted(invalid_source_ids)}"
                )

        fields_by_code = {field.field_code: field for field in parsed.fields}
        return [
            LLMExtractedField(
                field_code=field_code,
                value=fields_by_code[field_code].value,
                source_ids=fields_by_code[field_code].source_ids,
            )
            for field_code in FIELD_CODES
        ]

    def _generate_with_retry(self, prompt: str) -> types.GenerateContentResponse:
        config = types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=GeminiExtractionResponse,
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
    def _validate_and_collect_source_ids(
        documents: list[LLMDocumentInput],
    ) -> set[str]:
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
        return source_ids

    @staticmethod
    def _build_prompt(documents: list[LLMDocumentInput]) -> str:
        payload = {
            "required_field_codes": list(FIELD_CODES),
            "documents": [
                {
                    "document_id": document.document_id,
                    "document_type": document.document_type.value,
                    "blocks": [GeminiExtractor._serialize_block(block) for block in document.blocks],
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
