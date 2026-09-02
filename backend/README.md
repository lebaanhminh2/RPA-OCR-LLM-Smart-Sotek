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

The default bootstrap installs CPU-only PaddlePaddle and CPU-only PyTorch.
For the validated hybrid mode (Paddle detection on CPU and VietOCR recognition
on an NVIDIA GPU), add the GPU switch:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".\backend\scripts\install_ocr_dependencies.ps1" `
  -PythonExecutable "C:\path\to\venv\Scripts\python.exe" `
  -EnableVietOcrGpu
```

Hybrid mode installs the official PyTorch 2.2.1 CUDA 11.8 wheels while keeping
PaddlePaddle CPU-only. This separation avoids loading incompatible Paddle and
PyTorch cuDNN runtimes in the same backend process. Set
`OCR_RECOGNITION_DEVICE=cuda:0` only in an environment bootstrapped with the GPU
switch. The backend fails during startup if CUDA was requested but is not
available; it does not silently fall back to slow CPU recognition. Leave the
variable unset or set it to `cpu` for the portable CPU mode.

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
