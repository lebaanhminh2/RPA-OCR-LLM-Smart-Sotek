[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExecutable
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$requirementsPath = Join-Path $backendRoot "requirements.txt"

function Invoke-CheckedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $PythonExecutable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

function Invoke-CheckedPythonInput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Code
    )

    $Code | & $PythonExecutable -
    if ($LASTEXITCODE -ne 0) {
        throw "Python stdin command failed with exit code ${LASTEXITCODE}."
    }
}

Invoke-CheckedPython -Arguments @("--version")
Invoke-CheckedPython -Arguments @(
    "-m", "pip", "install", "-r", $requirementsPath
)
Invoke-CheckedPython -Arguments @(
    "-m", "pip", "install", "setuptools==81.0.0"
)
Invoke-CheckedPython -Arguments @(
    "-m", "pip", "install",
    "paddleocr==3.7.0",
    "paddlepaddle==3.3.1",
    "paddlex==3.7.2",
    "pypdfium2==5.13.0",
    "numpy==1.26.4",
    "Pillow==10.2.0"
)
Invoke-CheckedPython -Arguments @(
    "-m", "pip", "install",
    "--no-cache-dir",
    "--no-binary=imgaug",
    "--no-build-isolation",
    "imgaug==0.4.0"
)
Invoke-CheckedPython -Arguments @(
    "-m", "pip", "install",
    "vietocr==0.3.12",
    "torch==2.2.1",
    "torchvision==0.17.1",
    "numpy==1.26.4",
    "Pillow==10.2.0"
)
Invoke-CheckedPython -Arguments @("-m", "pip", "check")

$verificationCode = @'
import importlib.metadata as metadata
import re

expected_versions = {
    "setuptools": "81.0.0",
    "paddleocr": "3.7.0",
    "paddlepaddle": "3.3.1",
    "paddlex": "3.7.2",
    "vietocr": "0.3.12",
    "torch": "2.2.1",
    "torchvision": "0.17.1",
    "numpy": "1.26.4",
    "Pillow": "10.2.0",
    "imgaug": "0.4.0",
    "pypdfium2": "5.13.0",
}

for distribution_name, expected_version in expected_versions.items():
    actual_version = metadata.version(distribution_name)
    if actual_version != expected_version:
        raise RuntimeError(
            f"{distribution_name}=={actual_version} installed; "
            f"expected {expected_version}."
        )

opencv_distributions = sorted(
    (
        re.sub(r"[-_.]+", "-", distribution.metadata["Name"].lower()),
        distribution.version,
    )
    for distribution in metadata.distributions()
    if distribution.metadata["Name"]
    and re.sub(r"[-_.]+", "-", distribution.metadata["Name"].lower()).startswith(
        "opencv-"
    )
)
expected_opencv = [("opencv-contrib-python", "4.10.0.84")]
if opencv_distributions != expected_opencv:
    raise RuntimeError(
        f"Unexpected OpenCV distributions: {opencv_distributions!r}; "
        f"expected {expected_opencv!r}."
    )

imgaug_requirements = metadata.requires("imgaug") or []
imgaug_opencv_requirements = [
    requirement
    for requirement in imgaug_requirements
    if "opencv" in requirement.lower()
]
if imgaug_opencv_requirements != ["opencv-contrib-python"]:
    raise RuntimeError(
        "Unexpected imgaug OpenCV Requires-Dist metadata: "
        f"{imgaug_opencv_requirements!r}."
    )

import cv2
import imgaug
import numpy
import paddle
import paddleocr
import pypdfium2
import torch
import torchvision
from paddleocr import TextDetection
from PIL import Image
from vietocr.tool.config import Cfg
from vietocr.tool.predictor import Predictor

print("OCR dependency verification passed.")
print(f"OpenCV distributions: {opencv_distributions!r}")
print(f"imgaug OpenCV Requires-Dist: {imgaug_opencv_requirements!r}")
'@

Invoke-CheckedPythonInput -Code $verificationCode
