from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image  # type: ignore[import-untyped]

from app.domain.models import OCRBlock, OCRBlockKind
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

REFERENCE_RENDER_SCALE = 2.0
MIN_FEATURE_MATCHES = 12
MIN_INLIER_RATIO = 0.35
MIN_MARKERS = 2
INK_BACKGROUND_KERNEL = 31
INK_DARKNESS_DELTA = 25.0
LOCAL_SEARCH_RADIUS = 3
CHECKBOX_BORDER_BAND = 2
LOCAL_OFFSET_PENALTY = 0.5
AXIS_ARTIFACT_OCCUPANCY = 0.90
DENSE_MARK_MIN_INK = 0.30
MIN_PAGE_SANITY_OPTIONS = 4
MAX_PAGE_CHECKED_RATIO = 0.60


class CheckboxDetectionError(RuntimeError):
    """Base error raised by template checkbox detection."""


class CheckboxAlignmentError(CheckboxDetectionError):
    """Raised when an input page cannot be aligned safely."""


class CheckboxState(str, Enum):
    CHECKED = "CHECKED"
    UNCHECKED = "UNCHECKED"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class CheckboxThresholds:
    unchecked_max: float = 0.03
    checked_min: float = 0.08

    def __post_init__(self) -> None:
        if not 0.0 <= self.unchecked_max < self.checked_min <= 1.0:
            raise ValueError("Invalid checkbox classification thresholds.")


@dataclass(frozen=True)
class AlignmentResult:
    image: NDArray[np.uint8]
    observed_to_reference: NDArray[np.float64]
    confidence: float


ClassifiedOption = tuple[
    CheckboxOption,
    CheckboxState,
    float,
    tuple[int, int],
]


class CheckboxPageDetector(Protocol):
    def detect_page(
        self,
        document_id: str,
        page_number: int,
        image: Image.Image,
    ) -> list[OCRBlock]: ...


def _to_gray(image: Image.Image) -> NDArray[np.uint8]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    return cast(
        NDArray[np.uint8],
        cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY),
    )


def _render_reference_pages(path: Path) -> dict[int, NDArray[np.uint8]]:
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped]

        pages: dict[int, NDArray[np.uint8]] = {}
        with pdfium.PdfDocument(str(path)) as document:
            for index in range(len(document)):
                image = document[index].render(
                    scale=REFERENCE_RENDER_SCALE
                ).to_pil()
                try:
                    pages[index + 1] = _to_gray(image)
                finally:
                    image.close()
        return pages
    except Exception as error:
        raise CheckboxDetectionError(
            f"Unable to render checkbox reference PDF: {path}."
        ) from error


def _marker_points(
    observed: NDArray[np.uint8],
    reference_shape: tuple[int, int],
    specs: tuple[MarkerSpec, ...],
) -> tuple[NDArray[np.float32], NDArray[np.float32]] | None:
    if not specs or not hasattr(cv2, "aruco"):
        return None
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dictionary)
    detected_corners, detected_ids, _ = detector.detectMarkers(observed)
    if detected_ids is None:
        return None
    corners_by_id = {
        int(marker_id): np.asarray(corners, dtype=np.float32).reshape(4, 2)
        for marker_id, corners in zip(
            detected_ids.flatten(), detected_corners, strict=True
        )
    }
    height, width = reference_shape
    source: list[tuple[float, float]] = []
    target: list[tuple[float, float]] = []
    matched_markers = 0
    for spec in specs:
        observed_corners = corners_by_id.get(spec.marker_id)
        if observed_corners is None:
            continue
        matched_markers += 1
        source.extend(
            (float(point[0]), float(point[1]))
            for point in observed_corners
        )
        target.extend(
            (corner[0] * width, corner[1] * height)
            for corner in spec.corners
        )
    if matched_markers < MIN_MARKERS:
        return None
    return np.asarray(source, np.float32), np.asarray(target, np.float32)


def _feature_points(
    observed: NDArray[np.uint8],
    reference: NDArray[np.uint8],
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    detector = cv2.SIFT_create(  # type: ignore[attr-defined]
        nfeatures=5000,
        contrastThreshold=0.02,
    )
    observed_keypoints, observed_descriptors = detector.detectAndCompute(
        observed, None
    )
    reference_keypoints, reference_descriptors = detector.detectAndCompute(
        reference, None
    )
    if observed_descriptors is None or reference_descriptors is None:
        raise CheckboxAlignmentError(
            "Checkbox template alignment found no page features."
        )
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    pairs = matcher.knnMatch(observed_descriptors, reference_descriptors, k=2)
    matches = [
        first
        for pair in pairs
        if len(pair) == 2
        for first, second in [pair]
        if first.distance < 0.72 * second.distance
    ]
    if len(matches) < MIN_FEATURE_MATCHES:
        raise CheckboxAlignmentError(
            "Checkbox template alignment has insufficient feature matches: "
            f"{len(matches)}."
        )
    source = np.asarray(
        [observed_keypoints[match.queryIdx].pt for match in matches],
        dtype=np.float32,
    )
    target = np.asarray(
        [reference_keypoints[match.trainIdx].pt for match in matches],
        dtype=np.float32,
    )
    return source, target


def align_page(
    observed: NDArray[np.uint8],
    reference: NDArray[np.uint8],
    page: CheckboxTemplatePage,
) -> AlignmentResult:
    reference_shape = (reference.shape[0], reference.shape[1])
    marker_matches = _marker_points(observed, reference_shape, page.markers)
    source, target = (
        marker_matches
        if marker_matches is not None
        else _feature_points(observed, reference)
    )
    homography, inlier_mask = cv2.findHomography(
        source,
        target,
        cv2.RANSAC,
        4.0,
    )
    if homography is None or inlier_mask is None:
        raise CheckboxAlignmentError("Unable to calculate page homography.")
    inlier_ratio = float(np.mean(inlier_mask))
    if inlier_ratio < MIN_INLIER_RATIO:
        raise CheckboxAlignmentError(
            "Checkbox template alignment confidence is too low: "
            f"{inlier_ratio:.3f}."
        )
    height, width = reference.shape
    aligned = cv2.warpPerspective(observed, homography, (width, height))
    return AlignmentResult(
        image=cast(NDArray[np.uint8], aligned),
        observed_to_reference=np.asarray(homography, dtype=np.float64),
        confidence=min(1.0, inlier_ratio),
    )


def _pixel_box(
    box: NormalizedBox,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x = max(0, min(width - 1, round(box.x * width)))
    y = max(0, min(height - 1, round(box.y * height)))
    right = max(x + 1, min(width, round((box.x + box.width) * width)))
    bottom = max(y + 1, min(height, round((box.y + box.height) * height)))
    return x, y, right - x, bottom - y


def _ink_response(image: NDArray[np.uint8]) -> NDArray[np.float32]:
    """Measure dark ink relative to the slowly varying local paper tone."""
    background = cv2.GaussianBlur(
        image,
        (INK_BACKGROUND_KERNEL, INK_BACKGROUND_KERNEL),
        0,
    ).astype(np.float32)
    return np.maximum(0.0, background - image.astype(np.float32))


def _border_strength(patch: NDArray[np.float32]) -> float:
    band = min(
        CHECKBOX_BORDER_BAND,
        max(1, min(patch.shape) // 3),
    )
    sides = (
        float(np.mean(patch[:band, :])),
        float(np.mean(patch[-band:, :])),
        float(np.mean(patch[:, :band])),
        float(np.mean(patch[:, -band:])),
    )
    return float(np.mean(sides)) + 0.3 * min(sides)


def _refine_box(
    observed_ink: NDArray[np.float32],
    reference: NDArray[np.uint8],
    box: NormalizedBox,
) -> tuple[int, int, int, int, int, int]:
    height, width = reference.shape
    x, y, box_width, box_height = _pixel_box(box, width, height)
    best = (float("-inf"), 0, 0)
    for offset_y in range(-LOCAL_SEARCH_RADIUS, LOCAL_SEARCH_RADIUS + 1):
        for offset_x in range(
            -LOCAL_SEARCH_RADIUS,
            LOCAL_SEARCH_RADIUS + 1,
        ):
            candidate_x = x + offset_x
            candidate_y = y + offset_y
            if (
                candidate_x < 0
                or candidate_y < 0
                or candidate_x + box_width > width
                or candidate_y + box_height > height
            ):
                continue
            candidate = observed_ink[
                candidate_y : candidate_y + box_height,
                candidate_x : candidate_x + box_width,
            ]
            score = _border_strength(candidate) - LOCAL_OFFSET_PENALTY * (
                abs(offset_x) + abs(offset_y)
            )
            if score > best[0]:
                best = (score, offset_x, offset_y)
    return x + best[1], y + best[2], box_width, box_height, best[1], best[2]


def _remove_axis_aligned_artifacts(
    ink: NDArray[np.bool_],
) -> NDArray[np.bool_]:
    """Remove residual straight box-border rows/columns after local alignment."""
    artifacts = np.zeros_like(ink)
    artifacts[:, np.mean(ink, axis=0) >= AXIS_ARTIFACT_OCCUPANCY] = True
    artifacts[np.mean(ink, axis=1) >= AXIS_ARTIFACT_OCCUPANCY, :] = True
    return np.logical_and(ink, np.logical_not(artifacts))


def classify_checkbox(
    aligned: NDArray[np.uint8],
    reference: NDArray[np.uint8],
    box: NormalizedBox,
    thresholds: CheckboxThresholds,
    *,
    observed_ink: NDArray[np.float32] | None = None,
    reference_ink: NDArray[np.float32] | None = None,
) -> tuple[CheckboxState, float, tuple[int, int]]:
    observed_response = (
        observed_ink if observed_ink is not None else _ink_response(aligned)
    )
    reference_response = (
        reference_ink
        if reference_ink is not None
        else _ink_response(reference)
    )
    x, y, width, height, offset_x, offset_y = _refine_box(
        observed_response,
        reference,
        box,
    )
    inset_x = max(1, width // 4)
    inset_y = max(1, height // 4)
    observed_inner = observed_response[
        y + inset_y : y + height - inset_y,
        x + inset_x : x + width - inset_x,
    ]
    reference_x = x - offset_x
    reference_y = y - offset_y
    reference_inner = reference_response[
        reference_y + inset_y : reference_y + height - inset_y,
        reference_x + inset_x : reference_x + width - inset_x,
    ]
    if observed_inner.size == 0 or reference_inner.size == 0:
        return CheckboxState.UNCERTAIN, 0.0, (offset_x, offset_y)
    observed_mask = observed_inner > INK_DARKNESS_DELTA
    reference_mask = reference_inner > INK_DARKNESS_DELTA
    reference_mask = cv2.dilate(
        reference_mask.astype(np.uint8),
        np.ones((3, 3), dtype=np.uint8),
    ).astype(bool)
    added_ink = np.logical_and(observed_mask, np.logical_not(reference_mask))
    cleaned_ink = _remove_axis_aligned_artifacts(added_ink)
    raw_score = float(np.mean(added_ink))
    cleaned_score = float(np.mean(cleaned_ink))
    dense_score = (
        raw_score
        if raw_score >= DENSE_MARK_MIN_INK
        and cleaned_score > thresholds.unchecked_max
        else 0.0
    )
    score = max(
        cleaned_score,
        dense_score,
    )
    if score <= thresholds.unchecked_max:
        confidence = 1.0 - score / max(thresholds.unchecked_max, 0.001)
        return CheckboxState.UNCHECKED, confidence, (offset_x, offset_y)
    if score >= thresholds.checked_min:
        confidence = min(1.0, score / thresholds.checked_min)
        return CheckboxState.CHECKED, confidence, (offset_x, offset_y)
    return CheckboxState.UNCERTAIN, 0.0, (offset_x, offset_y)


def _page_is_saturated(classified: list[ClassifiedOption]) -> bool:
    if len(classified) < MIN_PAGE_SANITY_OPTIONS:
        return False
    checked_count = sum(
        state is CheckboxState.CHECKED for _, state, _, _ in classified
    )
    return checked_count / len(classified) >= MAX_PAGE_CHECKED_RATIO


def _map_box_to_observed(
    box: NormalizedBox,
    offset: tuple[int, int],
    reference_shape: tuple[int, int],
    observed_shape: tuple[int, int],
    observed_to_reference: NDArray[np.float64],
) -> tuple[float, float, float, float]:
    reference_height, reference_width = reference_shape
    observed_height, observed_width = observed_shape
    offset_x, offset_y = offset
    x = box.x * reference_width + offset_x
    y = box.y * reference_height + offset_y
    right = (box.x + box.width) * reference_width + offset_x
    bottom = (box.y + box.height) * reference_height + offset_y
    corners = np.asarray(
        [[[x, y], [right, y], [right, bottom], [x, bottom]]],
        dtype=np.float32,
    )
    try:
        inverse = np.linalg.inv(observed_to_reference)
    except np.linalg.LinAlgError as error:
        raise CheckboxAlignmentError("Page homography is singular.") from error
    mapped_points = cast(
        NDArray[np.float32],
        cv2.perspectiveTransform(
            corners,
            np.asarray(inverse, dtype=np.float64),
        ),
    )
    mapped = mapped_points[0]
    min_x = max(0.0, float(np.min(mapped[:, 0])) / observed_width)
    min_y = max(0.0, float(np.min(mapped[:, 1])) / observed_height)
    max_x = min(1.0, float(np.max(mapped[:, 0])) / observed_width)
    max_y = min(1.0, float(np.max(mapped[:, 1])) / observed_height)
    return min_x, min_y, max_x - min_x, max_y - min_y


class TemplateCheckboxDetector(CheckboxPageDetector):
    def __init__(
        self,
        template: CheckboxTemplate,
        reference_pages: dict[int, NDArray[np.uint8]],
        thresholds: CheckboxThresholds | None = None,
    ) -> None:
        missing_pages = {
            page.page_number for page in template.pages
        } - reference_pages.keys()
        if missing_pages:
            raise CheckboxDetectionError(
                "Reference PDF is missing configured pages: "
                f"{sorted(missing_pages)}."
            )
        self._template = template
        self._reference_pages = reference_pages
        self._thresholds = thresholds or CheckboxThresholds()

    @classmethod
    def from_paths(
        cls,
        config_path: str | Path,
        reference_pdf_path: str | Path,
    ) -> "TemplateCheckboxDetector":
        template = load_checkbox_template(config_path)
        pages = _render_reference_pages(Path(reference_pdf_path))
        return cls(template, pages)

    def _group_blocks(
        self,
        document_id: str,
        page_number: int,
        group: CheckboxGroup,
        reference: NDArray[np.uint8],
        observed: NDArray[np.uint8],
        alignment: AlignmentResult,
        classified: list[ClassifiedOption],
    ) -> list[OCRBlock]:
        checked = [
            item for item in classified if item[1] is CheckboxState.CHECKED
        ]
        if group.mode is ChoiceMode.SINGLE and len(checked) != 1:
            return []
        if not checked:
            return []

        created_at = datetime.now(UTC)
        blocks: list[OCRBlock] = []
        for option, _, confidence, offset in checked:
            x, y, width, height = _map_box_to_observed(
                option.evidence_box,
                offset,
                (reference.shape[0], reference.shape[1]),
                (observed.shape[0], observed.shape[1]),
                alignment.observed_to_reference,
            )
            blocks.append(
                OCRBlock(
                    id=str(uuid4()),
                    document_id=document_id,
                    page_number=page_number,
                    text=(
                        f"field_code={group.field_code};option={option.value}"
                    ),
                    bbox_x=x,
                    bbox_y=y,
                    bbox_width=width,
                    bbox_height=height,
                    confidence=min(confidence, alignment.confidence),
                    created_at=created_at,
                    block_kind=OCRBlockKind.CHECKBOX_SELECTION,
                )
            )
        return blocks

    def detect_page(
        self,
        document_id: str,
        page_number: int,
        image: Image.Image,
    ) -> list[OCRBlock]:
        page = self._template.page(page_number)
        if page is None or not page.groups:
            return []
        observed = _to_gray(image)
        reference = self._reference_pages[page_number]
        alignment = align_page(observed, reference, page)
        observed_ink = _ink_response(alignment.image)
        reference_ink = _ink_response(reference)
        classifications = [
            [
                (
                    option,
                    *classify_checkbox(
                        alignment.image,
                        reference,
                        option.box,
                        self._thresholds,
                        observed_ink=observed_ink,
                        reference_ink=reference_ink,
                    ),
                )
                for option in group.options
            ]
            for group in page.groups
        ]
        if _page_is_saturated(
            [item for group_items in classifications for item in group_items]
        ):
            return []
        blocks: list[OCRBlock] = []
        for group, classified in zip(
            page.groups,
            classifications,
            strict=True,
        ):
            blocks.extend(
                self._group_blocks(
                    document_id,
                    page_number,
                    group,
                    reference,
                    observed,
                    alignment,
                    classified,
                )
            )
        return blocks
