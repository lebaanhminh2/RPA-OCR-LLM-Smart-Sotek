import pytest

from app.domain.services.field_value_normalizer import (
    normalize_field_value,
    normalize_monetary_value,
)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("15000000", "15.000.000"),
        ("15.000.000", "15.000.000"),
        ("15,000,000 VNĐ", "15.000.000"),
        ("15 triệu", "15.000.000"),
        ("1,5 triệu", "1.500.000"),
        ("40.000.000 VNĐ/tháng (gross)", "40.000.000"),
        ("38 000.000", "38.000.000"),
    ],
)
def test_normalize_monetary_value_formats_supported_amounts(
    raw_value: str,
    expected: str,
) -> None:
    assert normalize_monetary_value(raw_value) == expected


@pytest.mark.parametrize(
    "raw_value",
    ["", "không rõ", "15,50,000", "15 triệu hoặc 20 triệu"],
)
def test_normalize_monetary_value_fails_closed_for_ambiguous_values(
    raw_value: str,
) -> None:
    assert normalize_monetary_value(raw_value) is None


def test_normalize_field_value_does_not_change_identifier_fields() -> None:
    assert normalize_field_value("so_cccd", "001234567890") == "001234567890"
    assert normalize_field_value("so_dien_thoai_di_dong", "0912345678") == (
        "0912345678"
    )
