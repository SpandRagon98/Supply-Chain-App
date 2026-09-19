$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot 'backend'
$python = Join-Path $backendRoot '.venv/Scripts/python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Backend virtual environment not found. Run: cd backend; python -m venv .venv; .venv/Scripts/python -m pip install -e ".[dev]"'
}

function Invoke-BackendPython {
    param([Parameter(Mandatory)][string[]]$Arguments)

    & $python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Backend command failed: python $($Arguments -join ' ')"
    }
}

Push-Location $backendRoot
try {
    Invoke-BackendPython -Arguments @('-m', 'ruff', 'check', '.')
    Invoke-BackendPython -Arguments @('-m', 'ruff', 'format', '--check', '.')
    Invoke-BackendPython -Arguments @('-m', 'mypy', 'app')
    Invoke-BackendPython -Arguments @('-m', 'pytest')
    Invoke-BackendPython -Arguments @('-m', 'alembic', 'heads')
    & $python -m alembic upgrade head --sql | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'PostgreSQL offline migration compilation failed.'
    }
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
