[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$modelTarget = Join-Path $repositoryRoot "model_weights"

if (Test-Path -LiteralPath $modelTarget) {
    throw "Model target already exists; refusing to overwrite: $modelTarget"
}
if (-not (Get-Command git-lfs -ErrorAction SilentlyContinue)) {
    throw "Git LFS is required. Install it from https://git-lfs.com/ first."
}

$temporaryRoot = Join-Path (
    [System.IO.Path]::GetTempPath()
) ("smart-sotek-model-assets-" + [guid]::NewGuid().ToString("N"))

try {
    git -C $repositoryRoot lfs install
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to initialize Git LFS."
    }

    git -C $repositoryRoot fetch origin `
        model-assets:refs/remotes/origin/model-assets
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to fetch the model-assets branch."
    }

    git -C $repositoryRoot worktree add --detach $temporaryRoot origin/model-assets
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the temporary model-assets worktree."
    }

    $source = Join-Path $temporaryRoot "model_weights"
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
        throw "The model-assets branch does not contain model_weights."
    }
    Copy-Item -LiteralPath $source -Destination $modelTarget -Recurse
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        git -C $repositoryRoot worktree remove --force $temporaryRoot
    }
}

Write-Output "Restored OCR models to: $modelTarget"
