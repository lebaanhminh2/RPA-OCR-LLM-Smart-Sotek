import re
import unicodedata
from decimal import Decimal, InvalidOperation

MONETARY_FIELD_CODES = frozenset(
    {
        "so_tien_vay_de_nghi",
        "muc_luong_gross",
        "thu_nhap_thuc_lanh_hang_thang",
        "chi_phi_sinh_hoat_hang_thang",
    }
)

_NUMBER_PATTERN = re.compile(r"\d+(?:[\s.,]\d+)*")
_SCALE_PATTERN = re.compile(r"\b(ty|trieu|nghin|ngan|k)\b")
_SCALES = {
    "ty": Decimal("1000000000"),
    "trieu": Decimal("1000000"),
    "nghin": Decimal("1000"),
    "ngan": Decimal("1000"),
    "k": Decimal("1000"),
}


def normalize_field_value(
    field_code: str,
    value: str | None,
) -> str | None:
    """Return the canonical persisted value for a known field."""
    if value is None or field_code not in MONETARY_FIELD_CODES:
        return value
    return normalize_monetary_value(value)


def normalize_monetary_value(value: str) -> str | None:
    """Normalize an unambiguous VND amount using dot group separators."""
    normalized_text = value.strip().replace("\u00a0", " ")
    if not normalized_text:
        return None

    number_matches = _NUMBER_PATTERN.findall(normalized_text)
    if len(number_matches) != 1:
        return None

    folded_text = _fold_vietnamese(normalized_text).lower()
    scale_matches = _SCALE_PATTERN.findall(folded_text)
    if len(scale_matches) > 1:
        return None

    number_text = number_matches[0]
    scale = _SCALES[scale_matches[0]] if scale_matches else None
    amount = _parse_amount(number_text, scale)
    if amount is None or amount < 0 or amount != amount.to_integral_value():
        return None

    return f"{int(amount):,}".replace(",", ".")


def _parse_amount(number_text: str, scale: Decimal | None) -> Decimal | None:
    groups = re.split(r"[\s.,]", number_text)
    if any(not group for group in groups):
        return None

    try:
        if len(groups) == 1:
            coefficient = Decimal(groups[0])
        elif all(len(group) == 3 for group in groups[1:]):
            coefficient = Decimal("".join(groups))
        elif scale is not None and len(groups) == 2 and len(groups[1]) <= 2:
            coefficient = Decimal(f"{groups[0]}.{groups[1]}")
        else:
            return None
    except InvalidOperation:
        return None

    return coefficient * (scale or Decimal(1))


def _fold_vietnamese(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return without_marks.replace("đ", "d").replace("Đ", "D")
