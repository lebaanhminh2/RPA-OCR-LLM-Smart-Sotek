import os
from pathlib import Path

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray
from PIL import Image  # type: ignore[import-untyped]

from app.domain.models import OCRBlockKind
from app.infra.ocr.checkbox_detector import (
    AlignmentResult,
    CheckboxState,
    CheckboxThresholds,
    TemplateCheckboxDetector,
    _page_is_saturated,
    align_page,
    classify_checkbox,
)
from app.infra.ocr.checkbox_template import (
    CheckboxGroup,
    CheckboxOption,
    CheckboxTemplate,
    CheckboxTemplatePage,
    ChoiceMode,
    MarkerSpec,
    NormalizedBox,
    load_checkbox_template,
)

CONFIG_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "infra"
    / "ocr"
    / "templates"
    / "loan_application_v1.json"
)
REFERENCE_PATH_ENV = "OCR_LOAN_APPLICATION_TEMPLATE_PATH"


def _draw_empty_box(
    image: NDArray[np.uint8],
    box: NormalizedBox,
) -> tuple[int, int, int, int]:
    height, width = image.shape
    x = round(box.x * width)
    y = round(box.y * height)
    box_width = round(box.width * width)
    box_height = round(box.height * height)
    cv2.rectangle(
        image,
        (x, y),
        (x + box_width - 1, y + box_height - 1),
        (0,),
        2,
    )
    return x, y, box_width, box_height


def _draw_tick(
    image: NDArray[np.uint8],
    box: NormalizedBox,
) -> None:
    x, y, width, height = _draw_empty_box(image, box)
    cv2.line(
        image,
        (x + width // 4, y + height // 2),
        (x + width // 2, y + height - 3),
        (0,),
        2,
    )
    cv2.line(
        image,
        (x + width // 2, y + height - 3),
        (x + width - 2, y + 2),
        (0,),
        2,
    )


def _synthetic_template() -> tuple[
    CheckboxTemplate,
    NDArray[np.uint8],
    CheckboxOption,
    CheckboxOption,
]:
    reference = np.full((1000, 800), 255, dtype=np.uint8)
    for row in range(8):
        cv2.putText(
            reference,
            f"SMART SOTEK FORM ROW {row}",
            (45, 80 + row * 105),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,),
            2,
            cv2.LINE_AA,
        )
        cv2.line(
            reference,
            (40, 95 + row * 105),
            (750, 95 + row * 105),
            (80,),
            1,
        )
    first = CheckboxOption(
        "12 tháng",
        NormalizedBox(0.20, 0.20, 0.03, 0.024),
        NormalizedBox(0.20, 0.195, 0.16, 0.034),
    )
    second = CheckboxOption(
        "24 tháng",
        NormalizedBox(0.42, 0.20, 0.03, 0.024),
        NormalizedBox(0.42, 0.195, 0.16, 0.034),
    )
    _draw_empty_box(reference, first.box)
    _draw_empty_box(reference, second.box)
    template = CheckboxTemplate(
        "synthetic-v1",
        (
            CheckboxTemplatePage(
                1,
                (
                    CheckboxGroup(
                        "ky_han_vay",
                        ChoiceMode.SINGLE,
                        (first, second),
                    ),
                ),
            ),
        ),
    )
    return template, reference, first, second


def test_production_template_config_has_45_core_checkbox_options() -> None:
    template = load_checkbox_template(CONFIG_PATH)

    options = [
        option
        for page in template.pages
        for group in page.groups
        for option in group.options
    ]

    assert template.template_id == "loan_application_v1"
    assert [page.page_number for page in template.pages] == [1, 2, 3]
    assert len(options) == 45


def test_classifier_distinguishes_unchecked_uncertain_and_checked() -> None:
    box = NormalizedBox(0.40, 0.40, 0.12, 0.12)
    reference = np.full((100, 100), 255, dtype=np.uint8)
    _draw_empty_box(reference, box)
    unchecked = reference.copy()
    uncertain = reference.copy()
    uncertain[46, 46:48] = 0
    checked = reference.copy()
    _draw_tick(checked, box)
    thresholds = CheckboxThresholds()

    assert classify_checkbox(unchecked, reference, box, thresholds)[0] is (
        CheckboxState.UNCHECKED
    )
    assert classify_checkbox(uncertain, reference, box, thresholds)[0] is (
        CheckboxState.UNCERTAIN
    )
    assert classify_checkbox(checked, reference, box, thresholds)[0] is (
        CheckboxState.CHECKED
    )


def test_classifier_handles_uneven_dark_paper_and_print_through() -> None:
    first = NormalizedBox(0.20, 0.40, 0.12, 0.12)
    second = NormalizedBox(0.65, 0.40, 0.12, 0.12)
    reference = np.full((140, 180), 255, dtype=np.uint8)
    _draw_empty_box(reference, first)
    _draw_empty_box(reference, second)
    marked = reference.copy()
    _draw_tick(marked, first)

    horizontal_tone = np.linspace(0.48, 0.78, marked.shape[1])
    vertical_tone = np.linspace(0.92, 1.0, marked.shape[0])[:, None]
    observed = np.clip(
        marked.astype(np.float32) * horizontal_tone * vertical_tone,
        0,
        255,
    ).astype(np.uint8)
    cv2.putText(
        observed,
        "FAINT REVERSE-SIDE TEXT",
        (8, 78),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.35,
        (115,),
        1,
        cv2.LINE_AA,
    )

    thresholds = CheckboxThresholds()
    assert classify_checkbox(observed, reference, first, thresholds)[0] is (
        CheckboxState.CHECKED
    )
    assert classify_checkbox(observed, reference, second, thresholds)[0] is (
        CheckboxState.UNCHECKED
    )


def test_classifier_rejects_dense_axis_aligned_artifact() -> None:
    box = NormalizedBox(0.40, 0.40, 0.12, 0.12)
    reference = np.full((100, 100), 255, dtype=np.uint8)
    x, y, width, height = _draw_empty_box(reference, box)
    observed = reference.copy()
    cv2.line(
        observed,
        (x + width // 2 - 1, y + height // 4),
        (x + width // 2 - 1, y + height - height // 4),
        (0,),
        3,
    )

    assert classify_checkbox(
        observed,
        reference,
        box,
        CheckboxThresholds(),
    )[0] is CheckboxState.UNCHECKED


def test_page_saturation_guard_fails_closed() -> None:
    option = CheckboxOption(
        "option",
        NormalizedBox(0.1, 0.1, 0.1, 0.1),
        NormalizedBox(0.1, 0.1, 0.2, 0.1),
    )
    checked = (option, CheckboxState.CHECKED, 1.0, (0, 0))
    unchecked = (option, CheckboxState.UNCHECKED, 1.0, (0, 0))

    assert _page_is_saturated([checked, checked, checked, unchecked])
    assert not _page_is_saturated([checked, unchecked, unchecked, unchecked])


def test_detector_aligns_perspective_and_maps_selection_bbox_back() -> None:
    template, reference, first, _ = _synthetic_template()
    marked = reference.copy()
    _draw_tick(marked, first.box)
    source = np.asarray(
        [[0, 0], [799, 0], [799, 999], [0, 999]],
        dtype=np.float32,
    )
    target = np.asarray(
        [[35, 25], [765, 5], [790, 965], [15, 990]],
        dtype=np.float32,
    )
    perspective = cv2.getPerspectiveTransform(source, target)
    observed = cv2.warpPerspective(marked, perspective, (800, 1000))
    detector = TemplateCheckboxDetector(template, {1: reference})

    with Image.fromarray(observed, mode="L").convert("RGB") as image:
        blocks = detector.detect_page("document-1", 1, image)

    assert len(blocks) == 1
    block = blocks[0]
    assert block.block_kind is OCRBlockKind.CHECKBOX_SELECTION
    assert block.text == "field_code=ky_han_vay;option=12 tháng"
    assert 0.0 <= block.bbox_x < 1.0
    assert 0.0 <= block.bbox_y < 1.0
    assert 0.0 < block.bbox_width <= 1.0
    assert 0.0 < block.bbox_height <= 1.0


def test_single_choice_conflict_emits_no_selection() -> None:
    template, reference, first, second = _synthetic_template()
    marked = reference.copy()
    _draw_tick(marked, first.box)
    _draw_tick(marked, second.box)
    detector = TemplateCheckboxDetector(template, {1: reference})

    with Image.fromarray(marked, mode="L").convert("RGB") as image:
        blocks = detector.detect_page("document-1", 1, image)

    assert blocks == []


def test_single_choice_keeps_one_checked_when_another_option_is_uncertain() -> None:
    template, reference, first, second = _synthetic_template()
    detector = TemplateCheckboxDetector(template, {1: reference})
    group = template.pages[0].groups[0]
    alignment = AlignmentResult(reference, np.eye(3), 1.0)

    blocks = detector._group_blocks(
        "document-1",
        1,
        group,
        reference,
        reference,
        alignment,
        [
            (first, CheckboxState.CHECKED, 1.0, (0, 0)),
            (second, CheckboxState.UNCERTAIN, 0.0, (0, 0)),
        ],
    )

    assert [block.text for block in blocks] == [
        "field_code=ky_han_vay;option=12 tháng"
    ]


def test_multi_choice_keeps_confirmed_mark_when_another_option_is_uncertain() -> None:
    single_template, reference, first, second = _synthetic_template()
    page = single_template.pages[0]
    multi_template = CheckboxTemplate(
        "synthetic-multi-v1",
        (
            CheckboxTemplatePage(
                page.page_number,
                (
                    CheckboxGroup(
                        "muc_dich_vay",
                        ChoiceMode.MULTI,
                        (first, second),
                    ),
                ),
            ),
        ),
    )
    detector = TemplateCheckboxDetector(multi_template, {1: reference})
    group = multi_template.pages[0].groups[0]
    alignment = AlignmentResult(reference, np.eye(3), 1.0)

    blocks = detector._group_blocks(
        "document-1",
        1,
        group,
        reference,
        reference,
        alignment,
        [
            (first, CheckboxState.CHECKED, 1.0, (0, 0)),
            (second, CheckboxState.UNCERTAIN, 0.0, (0, 0)),
        ],
    )

    assert [block.text for block in blocks] == [
        "field_code=muc_dich_vay;option=12 tháng"
    ]


def test_marker_alignment_uses_configured_marker_ids() -> None:
    reference = np.full((600, 500), 255, dtype=np.uint8)
    marker_specs: list[MarkerSpec] = []
    placements = [(25, 25, 3), (425, 25, 7), (25, 525, 11), (425, 525, 19)]
    for x, y, marker_id in placements:
        marker = cv2.aruco.generateImageMarker(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
            marker_id,
            50,
        )
        reference[y : y + 50, x : x + 50] = marker
        marker_specs.append(
            MarkerSpec(
                marker_id,
                (
                    (x / 500, y / 600),
                    ((x + 50) / 500, y / 600),
                    ((x + 50) / 500, (y + 50) / 600),
                    (x / 500, (y + 50) / 600),
                ),
            )
        )
    page = CheckboxTemplatePage(1, (), tuple(marker_specs))

    result = align_page(reference.copy(), reference, page)

    assert result.confidence == pytest.approx(1.0)
    assert np.mean(np.abs(result.image.astype(int) - reference.astype(int))) < 2


@pytest.mark.skipif(
    not os.getenv(REFERENCE_PATH_ENV),
    reason=f"{REFERENCE_PATH_ENV} is not configured",
)
def test_real_blank_template_coordinates_detect_synthetic_marks() -> None:
    import pypdfium2 as pdfium  # type: ignore[import-untyped]

    reference_path = Path(os.environ[REFERENCE_PATH_ENV])
    template = load_checkbox_template(CONFIG_PATH)
    detector = TemplateCheckboxDetector.from_paths(CONFIG_PATH, reference_path)
    page = template.page(1)
    assert page is not None
    selected = page.groups[0].options[1]

    with pdfium.PdfDocument(str(reference_path)) as document:
        image = document[0].render(scale=2.0).to_pil().convert("RGB")
    try:
        marked = np.asarray(image.convert("L"), dtype=np.uint8).copy()
        _draw_tick(marked, selected.box)
        with Image.fromarray(marked, mode="L").convert("RGB") as input_image:
            blocks = detector.detect_page("loan-document", 1, input_image)
    finally:
        image.close()

    assert [block.text for block in blocks] == [
        "field_code=ky_han_vay;option=24 tháng"
    ]
