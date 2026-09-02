import os
import socket
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn
from uuid import UUID

import pytest

from app.infra.ocr.local_ocr_adapter import LocalOCRAdapter

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_vietnamese_print.png"


def _configured_model_root() -> Path:
    configured_path = os.getenv("OCR_MODEL_PATH")
    if configured_path is None:
        pytest.skip("OCR_MODEL_PATH is required for the real-model OCR test.")
    model_root = Path(configured_path).expanduser().resolve()
    if not model_root.is_dir():
        pytest.fail(f"OCR_MODEL_PATH is not a directory: {model_root}")
    return model_root


def _deny_network(
    attempts: list[str],
) -> Callable[..., NoReturn]:
    def deny(*args: object, **kwargs: object) -> NoReturn:
        del args, kwargs
        attempts.append("network access")
        raise AssertionError("Network access is forbidden during offline OCR test.")

    return deny


def test_real_local_ocr_adapter_processes_static_fixture_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_root = _configured_model_root()
    paddle_config = model_root / "paddle_detection" / "inference.yml"
    vietocr_config = model_root / "vietocr" / "config.yml"
    assert "model_name: PP-OCRv6_medium_det" in paddle_config.read_text(
        encoding="utf-8"
    )
    vietocr_config_text = vietocr_config.read_text(encoding="utf-8")
    assert "seq_modeling: transformer" in vietocr_config_text
    assert "backbone: vgg19_bn" in vietocr_config_text

    network_attempts: list[str] = []
    deny_network = _deny_network(network_attempts)
    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket, "getaddrinfo", deny_network)
    monkeypatch.setattr("requests.sessions.Session.request", deny_network)

    adapter = LocalOCRAdapter(model_root)
    blocks = adapter.extract("synthetic-document", str(FIXTURE_PATH))

    assert type(adapter._detector).__module__.startswith("paddleocr.")
    assert type(adapter._recognizer).__module__.startswith("vietocr.")
    assert blocks
    assert network_attempts == []
    for block in blocks:
        assert UUID(block.id).version == 4
        assert block.document_id == "synthetic-document"
        assert block.page_number == 1
        assert block.text.strip()
        assert 0.0 <= block.bbox_x <= 1.0
        assert 0.0 <= block.bbox_y <= 1.0
        assert 0.0 < block.bbox_width <= 1.0
        assert 0.0 < block.bbox_height <= 1.0
        assert block.bbox_x + block.bbox_width <= 1.0
        assert block.bbox_y + block.bbox_height <= 1.0
        assert 0.0 <= block.confidence <= 1.0
        assert block.created_at.utcoffset() is not None
