from collections.abc import Iterator, Mapping, MutableMapping
from pathlib import Path
from typing import cast
from uuid import UUID

import numpy as np
import pytest
from numpy.typing import NDArray
from PIL import Image  # type: ignore[import-untyped]

import app.infra.ocr.local_ocr_adapter as ocr
from app.infra.ocr.local_ocr_adapter import (
    LocalOCRAdapter,
    OCRConfigurationError,
    OCRInputError,
    OCRProcessingError,
    UnsupportedOCRInputError,
)


class FakeDetector:
    def __init__(
        self,
        results: list[Mapping[str, object]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.results = results if results is not None else []
        self.error = error
        self.calls: list[NDArray[np.uint8]] = []

    def predict(
        self,
        image: NDArray[np.uint8],
    ) -> list[Mapping[str, object]]:
        self.calls.append(image.copy())
        if self.error is not None:
            raise self.error
        return self.results


class FakeRecognizer:
    def __init__(
        self,
        text: object = "Văn bản tiếng Việt",
        error: Exception | None = None,
    ) -> None:
        self.text = text
        self.error = error
        self.crop_sizes: list[tuple[int, int]] = []

    def predict(self, image: Image.Image) -> str:
        self.crop_sizes.append(image.size)
        if self.error is not None:
            raise self.error
        return cast(str, self.text)


def _write_model_assets(root: Path, omitted: set[str] | None = None) -> None:
    omitted = omitted or set()
    paddle_dir = root / "paddle_detection"
    vietocr_dir = root / "vietocr"
    paddle_dir.mkdir(parents=True)
    vietocr_dir.mkdir(parents=True)

    files = {
        "inference.yml": paddle_dir / "inference.yml",
        "inference.pdiparams": paddle_dir / "inference.pdiparams",
        "inference.json": paddle_dir / "inference.json",
        "config.yml": vietocr_dir / "config.yml",
        "weights.pth": vietocr_dir / "weights.pth",
    }
    for name, path in files.items():
        if name not in omitted:
            path.write_bytes(b"test-only-placeholder")


@pytest.fixture
def model_root(tmp_path: Path) -> Path:
    root = tmp_path / "models"
    _write_model_assets(root)
    return root


def _write_image(
    path: Path,
    size: tuple[int, int] = (100, 80),
    color: tuple[int, int, int] = (10, 20, 30),
) -> None:
    with Image.new("RGB", size, color) as image:
        image.save(path)


def _build_adapter(
    monkeypatch: pytest.MonkeyPatch,
    model_root: Path,
    detector: FakeDetector,
    recognizer: FakeRecognizer,
) -> LocalOCRAdapter:
    monkeypatch.setattr(ocr, "_load_detector", lambda _: detector)
    monkeypatch.setattr(ocr, "_load_recognizer", lambda _config, _weights: recognizer)
    return LocalOCRAdapter(model_root)


def _single_result(
    polygons: list[object],
    scores: list[object],
) -> list[Mapping[str, object]]:
    return [{"dt_polys": polygons, "dt_scores": scores}]


def test_missing_ocr_model_path_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OCR_MODEL_PATH", raising=False)

    with pytest.raises(OCRConfigurationError, match="OCR_MODEL_PATH"):
        LocalOCRAdapter()


@pytest.mark.parametrize(
    ("omitted", "message"),
    [
        ({"inference.yml"}, "Paddle inference config"),
        ({"inference.pdiparams"}, "Paddle inference parameters"),
        ({"inference.json"}, "Paddle inference model"),
        ({"config.yml"}, "VietOCR config"),
        ({"weights.pth"}, "VietOCR weights"),
    ],
)
def test_missing_local_model_asset_fails_before_loading_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omitted: set[str],
    message: str,
) -> None:
    root = tmp_path / "models"
    _write_model_assets(root, omitted)
    detector_loads = 0

    def unexpected_detector_load(_: Path) -> FakeDetector:
        nonlocal detector_loads
        detector_loads += 1
        return FakeDetector()

    monkeypatch.setattr(ocr, "_load_detector", unexpected_detector_load)

    with pytest.raises(OCRConfigurationError, match=message):
        LocalOCRAdapter(root)

    assert detector_loads == 0


def test_model_loaders_are_called_once_during_initialization(
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detector = FakeDetector()
    recognizer = FakeRecognizer()
    detector_paths: list[Path] = []
    recognizer_paths: list[tuple[Path, Path]] = []

    def load_detector(path: Path) -> FakeDetector:
        detector_paths.append(path)
        return detector

    def load_recognizer(config: Path, weights: Path) -> FakeRecognizer:
        recognizer_paths.append((config, weights))
        return recognizer

    monkeypatch.setattr(ocr, "_load_detector", load_detector)
    monkeypatch.setattr(ocr, "_load_recognizer", load_recognizer)

    LocalOCRAdapter(model_root)

    assert detector_paths == [(model_root / "paddle_detection").resolve()]
    assert recognizer_paths == [
        (
            (model_root / "vietocr" / "config.yml").resolve(),
            (model_root / "vietocr" / "weights.pth").resolve(),
        )
    ]


def test_paddle_loader_uses_local_model_directory_and_cpu(tmp_path: Path) -> None:
    model_dir = (tmp_path / "paddle").resolve()
    detector = FakeDetector()
    calls: list[tuple[str, str, bool]] = []

    def factory(
        *,
        model_dir: str,
        device: str,
        enable_mkldnn: bool,
    ) -> object:
        calls.append((model_dir, device, enable_mkldnn))
        return detector

    loaded = ocr._load_detector(model_dir, factory=factory)

    assert loaded is detector
    assert calls == [(str(model_dir), "cpu", False)]


def test_vietocr_loader_forces_local_cpu_configuration(tmp_path: Path) -> None:
    config_path = (tmp_path / "config.yml").resolve()
    weights_path = (tmp_path / "weights.pth").resolve()
    config: dict[str, object] = {
        "weights": "https://example.invalid/remote.pth",
        "device": "cuda:0",
        "cnn": {"pretrained": True},
        "predictor": {"beamsearch": True},
    }
    recognizer = FakeRecognizer()
    loaded_paths: list[str] = []
    received_configs: list[object] = []

    def config_loader(path: str) -> dict[str, object]:
        loaded_paths.append(path)
        return config

    def predictor_factory(config: MutableMapping[str, object]) -> object:
        received_configs.append(config)
        return recognizer

    loaded = ocr._load_recognizer(
        config_path,
        weights_path,
        config_loader=config_loader,
        predictor_factory=predictor_factory,
    )

    assert loaded is recognizer
    assert loaded_paths == [str(config_path)]
    assert received_configs == [config]
    assert config["weights"] == str(weights_path)
    assert config["device"] == "cpu"
    assert config["cnn"] == {"pretrained": False}
    assert config["predictor"] == {"beamsearch": False}


def test_vietocr_loader_restores_removed_pillow_resampling_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = (tmp_path / "config.yml").resolve()
    weights_path = (tmp_path / "weights.pth").resolve()
    config: dict[str, object] = {
        "cnn": {"pretrained": True},
        "predictor": {"beamsearch": True},
    }
    monkeypatch.delattr(Image, "ANTIALIAS", raising=False)

    ocr._load_recognizer(
        config_path,
        weights_path,
        config_loader=lambda _: config,
        predictor_factory=lambda _: FakeRecognizer(),
    )

    assert getattr(Image, "ANTIALIAS") is Image.Resampling.LANCZOS


def test_repeated_image_extract_reuses_models_and_maps_evidence(
    tmp_path: Path,
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "input.png"
    _write_image(image_path)
    detector = FakeDetector(
        _single_result(
            [[[-1.2, 10.2], [80.4, 10.2], [80.4, 60.6], [-1.2, 60.6]]],
            [0.91],
        )
    )
    recognizer = FakeRecognizer("Đơn đề nghị vay vốn")
    adapter = _build_adapter(monkeypatch, model_root, detector, recognizer)

    first = adapter.extract("document-1", str(image_path))
    second = adapter.extract("document-1", str(image_path))

    assert len(detector.calls) == 2
    assert detector.calls[0][0, 0].tolist() == [30, 20, 10]
    assert recognizer.crop_sizes == [(81, 51), (81, 51)]
    assert len(first) == len(second) == 1
    block = first[0]
    assert block.document_id == "document-1"
    assert block.page_number == 1
    assert block.text == "Đơn đề nghị vay vốn"
    assert block.bbox_x == pytest.approx(0.0)
    assert block.bbox_y == pytest.approx(10.2 / 80)
    assert block.bbox_width == pytest.approx(80.4 / 100)
    assert block.bbox_height == pytest.approx((60.6 - 10.2) / 80)
    assert block.confidence == pytest.approx(0.91)
    assert block.created_at.utcoffset() is not None
    assert UUID(block.id).version == 4
    assert first[0].id != second[0].id
    assert not hasattr(block, "source_id")


def test_zero_area_and_fully_outside_regions_are_skipped(
    tmp_path: Path,
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "input.png"
    _write_image(image_path)
    detector = FakeDetector(
        _single_result(
            [
                [[10, 10], [10, 10], [10, 20]],
                [[-20, 10], [-10, 10], [-10, 20], [-20, 20]],
            ],
            [0.8, 0.7],
        )
    )
    recognizer = FakeRecognizer()
    adapter = _build_adapter(monkeypatch, model_root, detector, recognizer)

    assert adapter.extract("document-1", str(image_path)) == []
    assert recognizer.crop_sizes == []


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_confidence_fails_explicitly(
    tmp_path: Path,
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    confidence: float,
) -> None:
    image_path = tmp_path / "input.png"
    _write_image(image_path)
    detector = FakeDetector(
        _single_result(
            [[[10, 10], [20, 10], [20, 20], [10, 20]]],
            [confidence],
        )
    )
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        detector,
        FakeRecognizer(),
    )

    with pytest.raises(OCRProcessingError, match="confidence"):
        adapter.extract("document-1", str(image_path))


@pytest.mark.parametrize(
    "polygon",
    [
        [[10, 10], [20, 10]],
        [[10, 10], [20, 10], [float("nan"), 20]],
        [[10, 10], [20, 10], [20]],
    ],
)
def test_malformed_or_non_finite_polygon_fails_explicitly(
    tmp_path: Path,
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    polygon: object,
) -> None:
    image_path = tmp_path / "input.png"
    _write_image(image_path)
    detector = FakeDetector(_single_result([polygon], [0.8]))
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        detector,
        FakeRecognizer(),
    )

    with pytest.raises(OCRProcessingError, match="Malformed detector response"):
        adapter.extract("document-1", str(image_path))


def test_empty_detection_returns_empty_without_recognition(
    tmp_path: Path,
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "input.png"
    _write_image(image_path)
    detector = FakeDetector(_single_result([], []))
    recognizer = FakeRecognizer()
    adapter = _build_adapter(monkeypatch, model_root, detector, recognizer)

    assert adapter.extract("document-1", str(image_path)) == []
    assert recognizer.crop_sizes == []


def test_mismatched_polygon_and_score_counts_fail(
    tmp_path: Path,
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "input.png"
    _write_image(image_path)
    detector = FakeDetector(
        _single_result(
            [[[10, 10], [20, 10], [20, 20], [10, 20]]],
            [],
        )
    )
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        detector,
        FakeRecognizer(),
    )

    with pytest.raises(OCRProcessingError, match="different lengths"):
        adapter.extract("document-1", str(image_path))


def test_detector_failure_includes_page_context(
    tmp_path: Path,
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "input.png"
    _write_image(image_path)
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        FakeDetector(error=RuntimeError("detector failed")),
        FakeRecognizer(),
    )

    with pytest.raises(OCRProcessingError, match="detection failed on page 1"):
        adapter.extract("document-1", str(image_path))


def test_recognizer_failure_includes_page_and_region_context(
    tmp_path: Path,
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "input.png"
    _write_image(image_path)
    detector = FakeDetector(
        _single_result(
            [[[10, 10], [20, 10], [20, 20], [10, 20]]],
            [0.8],
        )
    )
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        detector,
        FakeRecognizer(error=RuntimeError("recognizer failed")),
    )

    with pytest.raises(
        OCRProcessingError,
        match="recognition failed on page 1, region 1",
    ):
        adapter.extract("document-1", str(image_path))


def test_pdf_pages_are_processed_in_one_based_order(
    tmp_path: Path,
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(b"fake-pdf-for-monkeypatched-boundary")
    detector = FakeDetector(
        _single_result(
            [[[1, 1], [9, 1], [9, 9], [1, 9]]],
            [0.8],
        )
    )
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        detector,
        FakeRecognizer(),
    )

    def fake_pdf_pages(_: Path) -> Iterator[tuple[int, Image.Image]]:
        yield 1, Image.new("RGB", (10, 10), "white")
        yield 2, Image.new("RGB", (20, 20), "white")

    monkeypatch.setattr(ocr, "_iter_pdf_pages", fake_pdf_pages)

    blocks = adapter.extract("document-1", str(pdf_path))

    assert [block.page_number for block in blocks] == [1, 2]
    assert [block.bbox_width for block in blocks] == pytest.approx([0.8, 0.4])


def test_missing_input_file_fails(
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        FakeDetector(),
        FakeRecognizer(),
    )

    with pytest.raises(OCRInputError, match="does not exist"):
        adapter.extract("document-1", str(tmp_path / "missing.png"))


def test_corrupt_image_fails(
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "corrupt.png"
    image_path.write_bytes(b"not-an-image")
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        FakeDetector(),
        FakeRecognizer(),
    )

    with pytest.raises(OCRInputError, match="corrupt image"):
        adapter.extract("document-1", str(image_path))


def test_unsupported_input_fails(
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    text_path = tmp_path / "notes.txt"
    text_path.write_text("not an OCR input", encoding="utf-8")
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        FakeDetector(),
        FakeRecognizer(),
    )

    with pytest.raises(UnsupportedOCRInputError, match="Unsupported"):
        adapter.extract("document-1", str(text_path))


def test_corrupt_pdf_fails(
    model_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"not-a-pdf")
    adapter = _build_adapter(
        monkeypatch,
        model_root,
        FakeDetector(),
        FakeRecognizer(),
    )

    with pytest.raises(OCRInputError, match="corrupt PDF"):
        adapter.extract("document-1", str(pdf_path))
