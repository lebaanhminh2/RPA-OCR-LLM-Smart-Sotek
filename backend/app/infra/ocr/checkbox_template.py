import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import cast


class CheckboxTemplateError(ValueError):
    """Raised when a checkbox template configuration is invalid."""


class ChoiceMode(str, Enum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"


@dataclass(frozen=True)
class NormalizedBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if not all(0.0 <= value <= 1.0 for value in values):
            raise CheckboxTemplateError("Normalized box values must be 0..1.")
        if self.width <= 0.0 or self.height <= 0.0:
            raise CheckboxTemplateError(
                "Normalized box width and height must be positive."
            )
        if self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise CheckboxTemplateError(
                "Normalized box must remain inside its page."
            )


@dataclass(frozen=True)
class CheckboxOption:
    value: str
    box: NormalizedBox
    evidence_box: NormalizedBox


@dataclass(frozen=True)
class CheckboxGroup:
    field_code: str
    mode: ChoiceMode
    options: tuple[CheckboxOption, ...]


@dataclass(frozen=True)
class MarkerSpec:
    marker_id: int
    corners: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class CheckboxTemplatePage:
    page_number: int
    groups: tuple[CheckboxGroup, ...]
    markers: tuple[MarkerSpec, ...] = ()


@dataclass(frozen=True)
class CheckboxTemplate:
    template_id: str
    pages: tuple[CheckboxTemplatePage, ...]

    def page(self, page_number: int) -> CheckboxTemplatePage | None:
        return next(
            (
                page
                for page in self.pages
                if page.page_number == page_number
            ),
            None,
        )


def _as_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CheckboxTemplateError(f"{context} must be an object.")
    return cast(Mapping[str, object], value)


def _as_sequence(value: object, context: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise CheckboxTemplateError(f"{context} must be an array.")
    return cast(Sequence[object], value)


def _as_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CheckboxTemplateError(f"{context} must be a non-empty string.")
    return value


def _as_integer(value: object, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CheckboxTemplateError(f"{context} must be an integer.")
    return value


def _as_float(value: object, context: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CheckboxTemplateError(f"{context} must be a number.")
    return float(value)


def _load_box(value: object, context: str) -> NormalizedBox:
    values = _as_sequence(value, context)
    if len(values) != 4:
        raise CheckboxTemplateError(f"{context} must contain four numbers.")
    return NormalizedBox(
        *(
            _as_float(item, f"{context}[{index}]")
            for index, item in enumerate(values)
        )
    )


def _load_option(value: object, context: str) -> CheckboxOption:
    data = _as_mapping(value, context)
    return CheckboxOption(
        value=_as_string(data.get("value"), f"{context}.value"),
        box=_load_box(data.get("box"), f"{context}.box"),
        evidence_box=_load_box(
            data.get("evidence_box"),
            f"{context}.evidence_box",
        ),
    )


def _load_group(value: object, context: str) -> CheckboxGroup:
    data = _as_mapping(value, context)
    mode_text = _as_string(data.get("mode"), f"{context}.mode")
    try:
        mode = ChoiceMode(mode_text)
    except ValueError as error:
        raise CheckboxTemplateError(
            f"{context}.mode must be SINGLE or MULTI."
        ) from error
    options = tuple(
        _load_option(option, f"{context}.options[{index}]")
        for index, option in enumerate(
            _as_sequence(data.get("options"), f"{context}.options")
        )
    )
    if not options:
        raise CheckboxTemplateError(f"{context} must define options.")
    return CheckboxGroup(
        field_code=_as_string(
            data.get("field_code"),
            f"{context}.field_code",
        ),
        mode=mode,
        options=options,
    )


def _load_marker(value: object, context: str) -> MarkerSpec:
    data = _as_mapping(value, context)
    raw_corners = _as_sequence(data.get("corners"), f"{context}.corners")
    if len(raw_corners) != 4:
        raise CheckboxTemplateError(f"{context} must define four corners.")
    corners: list[tuple[float, float]] = []
    for index, raw_corner in enumerate(raw_corners):
        corner = _as_sequence(raw_corner, f"{context}.corners[{index}]")
        if len(corner) != 2:
            raise CheckboxTemplateError(
                f"{context}.corners[{index}] must contain x and y."
            )
        point = (
            _as_float(corner[0], f"{context}.corners[{index}][0]"),
            _as_float(corner[1], f"{context}.corners[{index}][1]"),
        )
        if not all(0.0 <= coordinate <= 1.0 for coordinate in point):
            raise CheckboxTemplateError(
                f"{context}.corners[{index}] must be normalized."
            )
        corners.append(point)
    return MarkerSpec(
        marker_id=_as_integer(data.get("id"), f"{context}.id"),
        corners=tuple(corners),
    )


def _load_page(value: object, context: str) -> CheckboxTemplatePage:
    data = _as_mapping(value, context)
    groups = tuple(
        _load_group(group, f"{context}.groups[{index}]")
        for index, group in enumerate(
            _as_sequence(data.get("groups"), f"{context}.groups")
        )
    )
    markers = tuple(
        _load_marker(marker, f"{context}.markers[{index}]")
        for index, marker in enumerate(
            _as_sequence(data.get("markers", []), f"{context}.markers")
        )
    )
    return CheckboxTemplatePage(
        page_number=_as_integer(
            data.get("page_number"),
            f"{context}.page_number",
        ),
        groups=groups,
        markers=markers,
    )


def load_checkbox_template(path: str | Path) -> CheckboxTemplate:
    config_path = Path(path)
    try:
        raw: object = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CheckboxTemplateError(
            f"Unable to load checkbox template: {config_path}."
        ) from error
    data = _as_mapping(raw, "template")
    pages = tuple(
        _load_page(page, f"template.pages[{index}]")
        for index, page in enumerate(
            _as_sequence(data.get("pages"), "template.pages")
        )
    )
    if not pages:
        raise CheckboxTemplateError("Template must contain pages.")
    page_numbers = [page.page_number for page in pages]
    if len(page_numbers) != len(set(page_numbers)):
        raise CheckboxTemplateError("Template page numbers must be unique.")
    return CheckboxTemplate(
        template_id=_as_string(data.get("template_id"), "template.template_id"),
        pages=pages,
    )
