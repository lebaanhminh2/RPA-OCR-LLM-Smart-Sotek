# Smart Sotek IDP Backend

## Install base dependencies

```powershell
python -m pip install -r requirements.txt
```

## Windows CPython 3.12 OCR bootstrap

The local PaddleOCR + VietOCR stack has a validated ordered installation for
the Windows CPython 3.12 development environment. Do not install the OCR stack
as one unordered requirements operation: imgaug must be built from its official
source distribution after PaddleX has installed `opencv-contrib-python`.

Create a fresh virtual environment outside the repository, then run the
bootstrap from the repository root with that environment's Python executable:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".\backend\scripts\install_ocr_dependencies.ps1" `
  -PythonExecutable "C:\path\to\venv\Scripts\python.exe"
```

The script installs the base requirements, applies the approved OCR package
order, runs `pip check`, and verifies the exact critical package and OpenCV
state. The execution-policy override applies only to this new PowerShell
process; no permanent policy change is required. The script does not download
OCR model weights.

Provide model files separately and set `OCR_MODEL_PATH` to a directory with
this layout:

```text
OCR_MODEL_PATH/
|-- paddle_detection/
|   |-- inference.yml
|   |-- inference.pdiparams
|   `-- inference.json      # inference.pdmodel is also supported
`-- vietocr/
    |-- config.yml
    `-- weights.pth
```

No other operating system or Python runtime is claimed as validated by this
bootstrap procedure.

## Quality checks

Run these commands from the `backend/` directory:

```powershell
ruff check .
python -m pytest
mypy .
```
