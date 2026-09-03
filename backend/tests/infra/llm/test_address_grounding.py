from datetime import UTC, datetime

from app.domain.models import DocumentType, OCRBlock
from app.domain.ports.llm_provider import LLMDocumentInput, LLMExtractedField
from app.infra.llm.address_grounding import (
    CURRENT_ADDRESS_FIELD,
    PERMANENT_ADDRESS_FIELD,
    build_loan_address_scopes,
    ground_address_sources,
)


def _block(
    source_id: str,
    text: str,
    x: float,
    y: float,
    width: float = 0.15,
    height: float = 0.02,
) -> OCRBlock:
    return OCRBlock(
        id=source_id,
        document_id="loan-document",
        page_number=2,
        text=text,
        bbox_x=x,
        bbox_y=y,
        bbox_width=width,
        bbox_height=height,
        confidence=0.9,
        created_at=datetime(2026, 9, 3, tzinfo=UTC),
    )


def _loan_document() -> LLMDocumentInput:
    return LLMDocumentInput(
        document_id="loan-document",
        document_type=DocumentType.LOAN_APPLICATION,
        blocks=[
            _block("header-permanent", "3.1. Địa chỉ thường trú", 0.04, 0.20),
            _block("label-p-street", "Số nhà, tên đường/thôn/xóm", 0.05, 0.23),
            _block("p-street", "Số 6, ngõ 5 Van Phúc", 0.07, 0.255, 0.32),
            _block("label-p-ward", "Phường/Xã", 0.05, 0.28),
            _block("label-p-district", "Quận/Huyện", 0.36, 0.28),
            _block("label-p-city", "Tỉnh/Thành phố", 0.66, 0.28),
            _block("p-ward", "Kim Mã", 0.07, 0.305),
            _block("p-district", "Ba Đinh", 0.37, 0.305),
            _block("p-city", "Hà Nội", 0.67, 0.305),
            _block("header-current", "3.2. Địa chỉ nơi ở hiện tại", 0.04, 0.34),
            _block("label-c-street", "Số nhà, tên đường/thôn/xóm", 0.05, 0.37),
            _block("stray-mark", "x", 0.52, 0.375),
            _block("c-street", "Số 6, ngõ 5 Van Phúc", 0.07, 0.395, 0.32),
            _block("label-c-ward", "Phường/Xã", 0.05, 0.42),
            _block("label-c-district", "Quận/Huyện", 0.36, 0.42),
            _block("label-c-city", "Tỉnh/Thành phố", 0.66, 0.42),
            _block("c-ward", "Kim Mã", 0.07, 0.445),
            _block("c-district", "Ba Đinh", 0.37, 0.445),
            _block("c-city", "Hà Nội", 0.67, 0.445),
            _block(
                "current-end",
                "Thời gian cư trú tại địa chỉ hiện tại (năm)",
                0.05,
                0.48,
            ),
        ],
    )


def test_build_scopes_separates_duplicate_address_rows() -> None:
    scopes = build_loan_address_scopes([_loan_document()])

    assert scopes[PERMANENT_ADDRESS_FIELD].source_ids == (
        "p-street",
        "p-ward",
        "p-district",
        "p-city",
    )
    assert scopes[CURRENT_ADDRESS_FIELD].source_ids == (
        "c-street",
        "c-ward",
        "c-district",
        "c-city",
    )
    assert "stray-mark" not in scopes[CURRENT_ADDRESS_FIELD].source_ids


def test_grounding_remaps_same_text_source_from_the_other_row() -> None:
    document = _loan_document()
    scopes = build_loan_address_scopes([document])
    fields = [
        LLMExtractedField(
            field_code=PERMANENT_ADDRESS_FIELD,
            value="Số 6, ngõ 5 Van Phúc, Kim Mã, Ba Đinh, Hà Nội",
            source_ids=["p-street", "p-ward", "c-district", "p-city"],
        ),
        LLMExtractedField(
            field_code=CURRENT_ADDRESS_FIELD,
            value="Số 6, ngõ 5 Van Phúc, Kim Mã, Ba Đinh, Hà Nội",
            source_ids=["c-street", "c-ward", "p-district", "c-city"],
        ),
    ]

    grounded = ground_address_sources(fields, [document], scopes)

    assert grounded[0].source_ids == [
        "p-street",
        "p-ward",
        "p-district",
        "p-city",
    ]
    assert grounded[1].source_ids == [
        "c-street",
        "c-ward",
        "c-district",
        "c-city",
    ]


def test_grounding_blanks_incomplete_address_instead_of_mixing_rows() -> None:
    document = _loan_document()
    scopes = build_loan_address_scopes([document])
    fields = [
        LLMExtractedField(
            field_code=CURRENT_ADDRESS_FIELD,
            value="Số 6, ngõ 5 Van Phúc, Ba Đinh, Hà Nội",
            source_ids=["c-street", "p-district", "c-city"],
        )
    ]

    grounded = ground_address_sources(fields, [document], scopes)

    assert grounded == [
        LLMExtractedField(
            field_code=CURRENT_ADDRESS_FIELD,
            value=None,
            source_ids=[],
        )
    ]


def test_scope_detection_fails_closed_when_section_boundary_is_missing() -> None:
    document = _loan_document()
    document.blocks[:] = [
        block for block in document.blocks if block.id != "current-end"
    ]

    assert build_loan_address_scopes([document]) == {}
