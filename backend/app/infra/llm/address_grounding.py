import re
import unicodedata
from dataclasses import dataclass

from app.domain.models import DocumentType, OCRBlock, OCRBlockKind
from app.domain.ports.llm_provider import LLMDocumentInput, LLMExtractedField

PERMANENT_ADDRESS_FIELD = "dia_chi_thuong_tru"
CURRENT_ADDRESS_FIELD = "dia_chi_hien_tai"

_SECTION_MARKERS = {
    PERMANENT_ADDRESS_FIELD: "3.1",
    CURRENT_ADDRESS_FIELD: "3.2",
}
_COMPONENT_LABELS = (
    "street",
    "ward",
    "district",
    "city",
)


@dataclass(frozen=True)
class AddressEvidenceScope:
    field_code: str
    document_id: str
    page_number: int
    value_blocks: tuple[OCRBlock, ...]
    label_source_ids: frozenset[str]

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(block.id for block in self.value_blocks)


def build_loan_address_scopes(
    documents: list[LLMDocumentInput],
) -> dict[str, AddressEvidenceScope]:
    loan_documents = [
        document
        for document in documents
        if document.document_type is DocumentType.LOAN_APPLICATION
    ]
    if len(loan_documents) != 1:
        return {}

    document = loan_documents[0]
    pages = sorted({block.page_number for block in document.blocks})
    for page_number in pages:
        page_blocks = sorted(
            (
                block
                for block in document.blocks
                if block.page_number == page_number
                and block.block_kind is OCRBlockKind.TEXT
            ),
            key=_reading_order,
        )
        scopes = _build_page_scopes(document.document_id, page_blocks)
        if set(scopes) == set(_SECTION_MARKERS):
            return scopes
    return {}


def ground_address_sources(
    fields: list[LLMExtractedField],
    documents: list[LLMDocumentInput],
    scopes: dict[str, AddressEvidenceScope],
) -> list[LLMExtractedField]:
    if not scopes:
        return fields

    blocks_by_id = {
        block.id: block
        for document in documents
        for block in document.blocks
    }
    grounded: list[LLMExtractedField] = []
    for field in fields:
        scope = scopes.get(field.field_code)
        if scope is None or field.value is None:
            grounded.append(field)
            continue
        grounded.append(_ground_field(field, scope, blocks_by_id))
    return grounded


def _build_page_scopes(
    document_id: str,
    blocks: list[OCRBlock],
) -> dict[str, AddressEvidenceScope]:
    permanent_header = _find_section_header(blocks, "3.1")
    current_header = _find_section_header(blocks, "3.2")
    if permanent_header is None or current_header is None:
        return {}
    current_end = _find_current_section_end(blocks, current_header)
    if current_end is None:
        return {}

    permanent = _build_section_scope(
        PERMANENT_ADDRESS_FIELD,
        document_id,
        blocks,
        _bottom(permanent_header),
        current_header.bbox_y,
    )
    current = _build_section_scope(
        CURRENT_ADDRESS_FIELD,
        document_id,
        blocks,
        _bottom(current_header),
        current_end,
    )
    if permanent is None or current is None:
        return {}
    return {
        PERMANENT_ADDRESS_FIELD: permanent,
        CURRENT_ADDRESS_FIELD: current,
    }


def _build_section_scope(
    field_code: str,
    document_id: str,
    blocks: list[OCRBlock],
    start_y: float,
    end_y: float,
) -> AddressEvidenceScope | None:
    section_blocks = [
        block for block in blocks if start_y <= block.bbox_y < end_y
    ]
    labels = {
        label: _find_component_label(section_blocks, label)
        for label in _COMPONENT_LABELS
    }
    if any(block is None for block in labels.values()):
        return None
    typed_labels = {
        label: block
        for label, block in labels.items()
        if block is not None
    }

    lower_label_y = min(
        typed_labels[label].bbox_y
        for label in ("ward", "district", "city")
    )
    street_blocks = _candidate_blocks(
        section_blocks,
        _bottom(typed_labels["street"]),
        lower_label_y,
    )

    lower_labels = [
        typed_labels[label] for label in ("ward", "district", "city")
    ]
    x_boundaries = [
        (
            lower_labels[index].bbox_x
            + lower_labels[index + 1].bbox_x
        )
        / 2
        for index in range(len(lower_labels) - 1)
    ]
    component_blocks: list[OCRBlock] = list(street_blocks)
    for index, label in enumerate(lower_labels):
        left = 0.0 if index == 0 else x_boundaries[index - 1]
        right = 1.0 if index == len(lower_labels) - 1 else x_boundaries[index]
        component_blocks.extend(
            block
            for block in _candidate_blocks(
                section_blocks,
                _bottom(label),
                end_y,
            )
            if left <= _center_x(block) < right
        )

    seen_ids: set[str] = set()
    ordered_block_list: list[OCRBlock] = []
    for block in component_blocks:
        if block.id in seen_ids:
            continue
        seen_ids.add(block.id)
        ordered_block_list.append(block)
    ordered_blocks = tuple(ordered_block_list)
    if not ordered_blocks:
        return None
    return AddressEvidenceScope(
        field_code=field_code,
        document_id=document_id,
        page_number=ordered_blocks[0].page_number,
        value_blocks=ordered_blocks,
        label_source_ids=frozenset(
            block.id for block in typed_labels.values()
        ),
    )


def _candidate_blocks(
    blocks: list[OCRBlock],
    start_y: float,
    end_y: float,
) -> list[OCRBlock]:
    return sorted(
        (
            block
            for block in blocks
            if start_y <= block.bbox_y < end_y
            and len(block.text.strip()) >= 2
            and _component_label(block.text) is None
            and not _is_section_header(block.text)
        ),
        key=_reading_order,
    )


def _ground_field(
    field: LLMExtractedField,
    scope: AddressEvidenceScope,
    blocks_by_id: dict[str, OCRBlock],
) -> LLMExtractedField:
    expected_ids = scope.source_ids
    expected_set = set(expected_ids)
    selected: list[str] = []
    used_loan_scope = False

    for source_id in dict.fromkeys(field.source_ids):
        if source_id in scope.label_source_ids:
            used_loan_scope = True
            continue
        if source_id in expected_set:
            used_loan_scope = True
            selected.append(source_id)
            continue

        block = blocks_by_id.get(source_id)
        if block is None or block.document_id != scope.document_id:
            selected.append(source_id)
            continue

        used_loan_scope = True
        replacements = [
            candidate.id
            for candidate in scope.value_blocks
            if candidate.text.strip() == block.text.strip()
        ]
        if len(replacements) != 1:
            return _blank_field(field.field_code)
        selected.append(replacements[0])

    if not used_loan_scope:
        return field

    selected_set = set(selected)
    if not expected_set.issubset(selected_set):
        return _blank_field(field.field_code)

    ordered_loan_ids = [
        source_id for source_id in expected_ids if source_id in selected_set
    ]
    other_ids = [
        source_id for source_id in selected if source_id not in expected_set
    ]
    return LLMExtractedField(
        field_code=field.field_code,
        value=field.value,
        source_ids=list(dict.fromkeys(ordered_loan_ids + other_ids)),
    )


def _blank_field(field_code: str) -> LLMExtractedField:
    return LLMExtractedField(
        field_code=field_code,
        value=None,
        source_ids=[],
    )


def _find_section_header(
    blocks: list[OCRBlock],
    marker: str,
) -> OCRBlock | None:
    return next(
        (
            block
            for block in blocks
            if _fold_text(block.text).startswith(marker)
            and "dia chi" in _fold_text(block.text)
        ),
        None,
    )


def _find_current_section_end(
    blocks: list[OCRBlock],
    current_header: OCRBlock,
) -> float | None:
    candidates = [
        block.bbox_y
        for block in blocks
        if block.bbox_y > current_header.bbox_y
        and "thoi gian cu tru tai dia chi hien tai" in _fold_text(block.text)
    ]
    return min(candidates) if candidates else None


def _find_component_label(
    blocks: list[OCRBlock],
    label: str,
) -> OCRBlock | None:
    return next(
        (block for block in blocks if _component_label(block.text) == label),
        None,
    )


def _component_label(text: str) -> str | None:
    folded = _fold_text(text)
    if "so nha" in folded and "duong" in folded:
        return "street"
    if "phuong" in folded and "xa" in folded:
        return "ward"
    if "quan" in folded and "huyen" in folded:
        return "district"
    if "tinh" in folded and "thanh pho" in folded:
        return "city"
    return None


def _is_section_header(text: str) -> bool:
    folded = _fold_text(text)
    return any(
        folded.startswith(marker) and "dia chi" in folded
        for marker in _SECTION_MARKERS.values()
    )


def _fold_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    normalized = without_marks.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _bottom(block: OCRBlock) -> float:
    return block.bbox_y + block.bbox_height


def _center_x(block: OCRBlock) -> float:
    return block.bbox_x + block.bbox_width / 2


def _reading_order(block: OCRBlock) -> tuple[float, float]:
    return block.bbox_y, block.bbox_x
