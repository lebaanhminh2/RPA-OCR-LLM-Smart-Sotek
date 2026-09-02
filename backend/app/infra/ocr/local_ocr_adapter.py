import math
import os
from collections.abc import (
    Callable,
    Generator,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
)
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

import numpy as np
from numpy.typing import NDArray
from PIL import Image, UnidentifiedImageError  # type: ignore[import-untyped]

from app.domain.models import DocumentType, OCRBlock
from app.domain.ports.ocr_provider import OCRProvider
from app.infra.ocr.checkbox_detector import (
    CheckboxDetectionError,
    CheckboxPageDetector,
    TemplateCheckboxDetector,
)

PDF_RENDER_SCALE = 2.0
LOAN_TEMPLATE_PATH_ENV = "OCR_LOAN_APPLICATION_TEMPLATE_PATH"
LOAN_TEMPLATE_CONFIG = (
    Path(__file__).resolve().parent
    / "templates"
    / "loan_application_v1.json"
)


class LocalOCRError(RuntimeError):
    """Base error raised by the local OCR adapter."""


class OCRConfigurationError(LocalOCRError):
    """Raised when local OCR configuration or model assets are invalid."""


class OCRInputError(LocalOCRError):
    """Raised when an OCR input cannot be read."""


class UnsupportedOCRInputError(OCRInputError):
    """Raised when an input is neither a supported image nor a PDF."""


def _load_checkbox_detector() -> CheckboxPageDetector | None:
    reference_path = os.getenv(LOAN_TEMPLATE_PATH_ENV)
    if not reference_path:
        return None
    path = Path(reference_path).expanduser()
    if not path.is_file():
        raise OCRConfigurationError(
            f"{LOAN_TEMPLATE_PATH_ENV} does not point to a reference PDF: "
            f"{path}."
        )
    try:
        return TemplateCheckboxDetector.from_paths(
            LOAN_TEMPLATE_CONFIG,
            path,
        )
    except CheckboxDetectionError as error:
        raise OCRConfigurationError(
            "Unable to initialize loan-application checkbox template."
        ) from error


class OCRProcessingError(LocalOCRError):
    """Raised when detection or recognition fails."""


class _Detector(Protocol):
    def predict(
        self,
        image: NDArray[np.uint8],
    ) -> Iterable[Mapping[str, object]]: ...


class _Recognizer(Protocol):
    def predict(self, image: Image.Image) -> str: ...


class _DetectorFactory(Protocol):
    def __call__(
        self,
        *,
        model_dir: str,
        device: str,
        enable_mkldnn: bool,
    ) -> object: ...


class _PredictorFactory(Protocol):
    def __call__(self, config: MutableMapping[str, object]) -> object: ...


ConfigLoader = Callable[[str], MutableMapping[str, object]]


def _ensure_vietocr_pillow_compatibility() -> None:
    # VietOCR 0.3.12 still uses the alias removed by Pillow 10.
    if not hasattr(Image, "ANTIALIAS"):
        setattr(Image, "ANTIALIAS", Image.Resampling.LANCZOS)


def _load_detector(
    model_dir: Path,
    factory: _DetectorFactory | None = None,
) -> _Detector:
    if factory is None:
        from paddleocr import TextDetection  # type: ignore[import-untyped]

        factory = cast(_DetectorFactory, TextDetection)

    try:
        # PaddlePaddle 3.3.1 cannot execute this static model through oneDNN on
        # Windows, while the standard CPU inference engine supports it.
        detector = factory(
            model_dir=str(model_dir),
            device="cpu",
            enable_mkldnn=False,
        )
    except Exception as error:
        raise OCRConfigurationError(
            f"Unable to initialize Paddle text detection from {model_dir}."
        ) from error
    return cast(_Detector, detector)


def _load_recognizer(
    config_path: Path,
    weights_path: Path,
    config_loader: ConfigLoader | None = None,
    predictor_factory: _PredictorFactory | None = None,
) -> _Recognizer:
    _ensure_vietocr_pillow_compatibility()
    if config_loader is None or predictor_factory is None:
        from vietocr.tool.config import Cfg  # type: ignore[import-untyped]
        from vietocr.tool.predictor import Predictor  # type: ignore[import-untyped]

        config_loader = config_loader or cast(
            ConfigLoader,
            Cfg.load_config_from_file,
        )
        predictor_factory = predictor_factory or cast(
            _PredictorFactory,
            Predictor,
        )

    try:
        config = config_loader(str(config_path))
    except Exception as error:
        raise OCRConfigurationError(
            f"Unable to load VietOCR config from {config_path}."
        ) from error

    cnn_config = config.get("cnn")
    predictor_config = config.get("predictor")
    if not isinstance(cnn_config, MutableMapping):
        raise OCRConfigurationError(
            f"VietOCR config {config_path} is missing a 'cnn' mapping."
        )
    if not isinstance(predictor_config, MutableMapping):
        raise OCRConfigurationError(
            f"VietOCR config {config_path} is missing a 'predictor' mapping."
        )

    config["weights"] = str(weights_path)
    config["device"] = "cpu"
    cnn_config["pretrained"] = False
    predictor_config["beamsearch"] = False

    try:
        recognizer = predictor_factory(config)
    except Exception as error:
        raise OCRConfigurationError(
            f"Unable to initialize VietOCR from {weights_path}."
        ) from error
    return cast(_Recognizer, recognizer)


def _require_model_root(model_root: str | Path | None) -> Path:
    configured_root = model_root
    if configured_root is None:
        configured_root = os.getenv("OCR_MODEL_PATH")
    if configured_root is None or not str(configured_root).strip():
        raise OCRConfigurationError("OCR_MODEL_PATH is not configured.")

    try:
        resolved_root = Path(configured_root).expanduser().resolve()
    except OSError as error:
        raise OCRConfigurationError(
            f"Unable to resolve OCR model path: {configured_root}."
        ) from error
    if not resolved_root.is_dir():
        raise OCRConfigurationError(
            f"OCR model path is not a directory: {resolved_root}."
        )
    return resolved_root


def _require_file(path: Path, description: str) -> Path:
    if not path.is_file():
        raise OCRConfigurationError(f"Missing {description}: {path}.")
    return path.resolve()


def _resolve_model_assets(model_root: Path) -> tuple[Path, Path, Path]:
    paddle_dir = model_root / "paddle_detection"
    if not paddle_dir.is_dir():
        raise OCRConfigurationError(
            f"Missing Paddle detection model directory: {paddle_dir}."
        )
    _require_file(paddle_dir / "inference.yml", "Paddle inference config")
    _require_file(
        paddle_dir / "inference.pdiparams",
        "Paddle inference parameters",
    )
    model_files = (
        paddle_dir / "inference.json",
        paddle_dir / "inference.pdmodel",
    )
    if not any(path.is_file() for path in model_files):
        raise OCRConfigurationError(
            "Missing Paddle inference model: expected inference.json or "
            f"inference.pdmodel in {paddle_dir}."
        )

    vietocr_dir = model_root / "vietocr"
    config_path = _require_file(
        vietocr_dir / "config.yml",
        "VietOCR config",
    )
    weights_path = _require_file(
        vietocr_dir / "weights.pth",
        "VietOCR weights",
    )
    return paddle_dir.resolve(), config_path, weights_path


def _load_image(path: Path) -> Image.Image:
    try:
        with Image.open(path) as source_image:
            source_image.load()
            return source_image.convert("RGB")
    except UnidentifiedImageError as error:
        known_image_suffixes = {
            suffix.lower() for suffix in Image.registered_extensions()
        }
        if path.suffix.lower() in known_image_suffixes:
            raise OCRInputError(f"Unreadable or corrupt image: {path}.") from error
        raise UnsupportedOCRInputError(
            f"Unsupported OCR input type: {path}."
        ) from error
    except (OSError, ValueError) as error:
        raise OCRInputError(f"Unreadable or corrupt image: {path}.") from error


def _iter_pdf_pages(path: Path) -> Iterator[tuple[int, Image.Image]]:
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped]

        with pdfium.PdfDocument(str(path)) as document:
            for page_index in range(len(document)):
                try:
                    with closing(document[page_index]) as page:
                        with closing(
                            page.render(scale=PDF_RENDER_SCALE)
                        ) as bitmap:
                            source_image = bitmap.to_pil()
                            try:
                                image = source_image.convert("RGB")
                            finally:
                                source_image.close()
                except Exception as error:
                    raise OCRInputError(
                        f"Unable to render PDF page {page_index + 1}: {path}."
                    ) from error
                yield page_index + 1, image
    except OCRInputError:
        raise
    except Exception as error:
        raise OCRInputError(f"Unreadable or corrupt PDF: {path}.") from error


def _iter_page_images(path: Path) -> Generator[tuple[int, Image.Image], None, None]:
    if path.suffix.lower() == ".pdf":
        yield from _iter_pdf_pages(path)
        return
    yield 1, _load_image(path)


def _to_items(value: object, description: str, page_number: int) -> list[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise OCRProcessingError(
            f"Malformed detector response on page {page_number}: "
            f"{description} is not a collection."
        )
    return list(cast(Iterable[object], value))


def _to_finite_float(value: object, description: str, page_number: int) -> float:
    if isinstance(value, (bool, str, bytes)):
        raise OCRProcessingError(
            f"Malformed detector response on page {page_number}: "
            f"{description} is not numeric."
        )
    try:
        numeric_value = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError) as error:
        raise OCRProcessingError(
            f"Malformed detector response on page {page_number}: "
            f"{description} is not numeric."
        ) from error
    if not math.isfinite(numeric_value):
        raise OCRProcessingError(
            f"Malformed detector response on page {page_number}: "
            f"{description} is not finite."
        )
    return numeric_value


def _polygon_bounds(
    polygon: object,
    page_number: int,
    region_number: int,
) -> tuple[float, float, float, float]:
    points = _to_items(
        polygon,
        f"region {region_number} polygon",
        page_number,
    )
    if len(points) < 3:
        raise OCRProcessingError(
            f"Malformed detector response on page {page_number}: "
            f"region {region_number} polygon has fewer than three points."
        )

    x_values: list[float] = []
    y_values: list[float] = []
    for point_number, point in enumerate(points, start=1):
        coordinates = _to_items(
            point,
            f"region {region_number} point {point_number}",
            page_number,
        )
        if len(coordinates) != 2:
            raise OCRProcessingError(
                f"Malformed detector response on page {page_number}: "
                f"region {region_number} point {point_number} must have two "
                "coordinates."
            )
        x_values.append(
            _to_finite_float(
                coordinates[0],
                f"region {region_number} point {point_number} x",
                page_number,
            )
        )
        y_values.append(
            _to_finite_float(
                coordinates[1],
                f"region {region_number} point {point_number} y",
                page_number,
            )
        )
    return min(x_values), min(y_values), max(x_values), max(y_values)


class LocalOCRAdapter(OCRProvider):
    def __init__(
        self,
        model_root: str | Path | None = None,
        checkbox_detector: CheckboxPageDetector | None = None,
    ) -> None:
        resolved_root = _require_model_root(model_root)
        paddle_dir, config_path, weights_path = _resolve_model_assets(
            resolved_root
        )
        self._detector = _load_detector(paddle_dir)
        self._recognizer = _load_recognizer(config_path, weights_path)
        self._checkbox_detector = checkbox_detector or _load_checkbox_detector()

    def extract(
        self,
        document_id: str,
        document_type: DocumentType,
        file_path: str,
    ) -> list[OCRBlock]:
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise OCRInputError(f"OCR input file does not exist: {path}.")
        if (
            document_type is DocumentType.LOAN_APPLICATION
            and self._checkbox_detector is None
        ):
            raise OCRConfigurationError(
                f"{LOAN_TEMPLATE_PATH_ENV} is required for "
                "LOAN_APPLICATION checkbox extraction."
            )

        blocks: list[OCRBlock] = []
        pages = _iter_page_images(path)
        with closing(pages):
            for page_number, image in pages:
                try:
                    blocks.extend(
                        self._process_page(document_id, page_number, image)
                    )
                    if document_type is DocumentType.LOAN_APPLICATION:
                        assert self._checkbox_detector is not None
                        blocks.extend(
                            self._checkbox_detector.detect_page(
                                document_id,
                                page_number,
                                image,
                            )
                        )
                finally:
                    image.close()
        return blocks

    def _process_page(
        self,
        document_id: str,
        page_number: int,
        image: Image.Image,
    ) -> list[OCRBlock]:
        page_width, page_height = image.size
        if page_width <= 0 or page_height <= 0:
            raise OCRInputError(
                f"Page {page_number} has invalid dimensions: "
                f"{page_width}x{page_height}."
            )

        rgb_pixels = np.asarray(image, dtype=np.uint8)
        bgr_pixels = np.ascontiguousarray(rgb_pixels[:, :, ::-1])
        try:
            raw_results = self._detector.predict(bgr_pixels)
        except Exception as error:
            raise OCRProcessingError(
                f"Text detection failed on page {page_number}."
            ) from error

        try:
            results = list(raw_results)
        except (TypeError, ValueError) as error:
            raise OCRProcessingError(
                f"Malformed detector response on page {page_number}: "
                "result is not iterable."
            ) from error
        if not results:
            return []
        if len(results) != 1 or not isinstance(results[0], Mapping):
            raise OCRProcessingError(
                f"Malformed detector response on page {page_number}: "
                "expected exactly one page result."
            )

        result = results[0]
        if "dt_polys" not in result or "dt_scores" not in result:
            raise OCRProcessingError(
                f"Malformed detector response on page {page_number}: "
                "missing dt_polys or dt_scores."
            )
        polygons = _to_items(result["dt_polys"], "dt_polys", page_number)
        scores = _to_items(result["dt_scores"], "dt_scores", page_number)
        if len(polygons) != len(scores):
            raise OCRProcessingError(
                f"Malformed detector response on page {page_number}: "
                "dt_polys and dt_scores have different lengths."
            )

        blocks: list[OCRBlock] = []
        for region_number, (polygon, raw_score) in enumerate(
            zip(polygons, scores, strict=True),
            start=1,
        ):
            confidence = _to_finite_float(
                raw_score,
                f"region {region_number} confidence",
                page_number,
            )
            if not 0.0 <= confidence <= 1.0:
                raise OCRProcessingError(
                    f"Malformed detector response on page {page_number}: "
                    f"region {region_number} confidence {confidence} is outside "
                    "0.0-1.0."
                )

            left, top, right, bottom = _polygon_bounds(
                polygon,
                page_number,
                region_number,
            )
            left = min(max(left, 0.0), float(page_width))
            right = min(max(right, 0.0), float(page_width))
            top = min(max(top, 0.0), float(page_height))
            bottom = min(max(bottom, 0.0), float(page_height))
            if right <= left or bottom <= top:
                continue

            crop_left = min(max(math.floor(left), 0), page_width)
            crop_top = min(max(math.floor(top), 0), page_height)
            crop_right = min(max(math.ceil(right), 0), page_width)
            crop_bottom = min(max(math.ceil(bottom), 0), page_height)
            if crop_right <= crop_left or crop_bottom <= crop_top:
                continue

            with image.crop(
                (crop_left, crop_top, crop_right, crop_bottom)
            ) as crop:
                try:
                    text = self._recognizer.predict(crop)
                except Exception as error:
                    raise OCRProcessingError(
                        f"Text recognition failed on page {page_number}, "
                        f"region {region_number}."
                    ) from error
            if not isinstance(text, str):
                raise OCRProcessingError(
                    f"Malformed VietOCR response on page {page_number}, "
                    f"region {region_number}: expected text."
                )

            blocks.append(
                OCRBlock(
                    id=str(uuid4()),
                    document_id=document_id,
                    page_number=page_number,
                    text=text,
                    bbox_x=left / page_width,
                    bbox_y=top / page_height,
                    bbox_width=(right - left) / page_width,
                    bbox_height=(bottom - top) / page_height,
                    confidence=confidence,
                    created_at=datetime.now(UTC),
                )
            )
        return blocks
