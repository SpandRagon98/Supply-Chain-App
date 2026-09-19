$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    docker compose run --rm api alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw 'Database migration failed; demo data was not changed.'
    }

    docker compose run --rm api python -m app.seed
    if ($LASTEXITCODE -ne 0) {
        throw 'Nova Electronics demo-data seed failed.'
    }
}
finally {
    Pop-Location
}

Write-Host 'Nova Electronics demo data is ready.'
