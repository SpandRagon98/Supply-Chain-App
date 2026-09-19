$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot 'backend'
$python = Join-Path $backendRoot '.venv/Scripts/python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Backend virtual environment not found. Run: cd backend; python -m venv .venv; .venv/Scripts/python -m pip install -e ".[dev]"'
}

Push-Location $backendRoot
try {
    & $python -m ruff check .
    & $python -m ruff format --check .
    & $python -m mypy app
    & $python -m pytest
    & $python -m alembic heads
}
finally {
    Pop-Location
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Push-Location $repoRoot
    try {
        docker compose --env-file .env.example config --quiet
        if ($LASTEXITCODE -ne 0) {
            throw 'Docker Compose configuration validation failed.'
        }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Warning 'Docker is not installed or not on PATH; skipped Compose validation.'
}

Write-Host 'Backend foundation verification passed.'
