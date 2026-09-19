$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$requiredPaths = @(
    'backend',
    'frontend',
    'docs',
    'docs/decisions',
    'infrastructure',
    '.github/workflows',
    'docker-compose.yml',
    '.env.example',
    'README.md',
    'LICENSE'
)

foreach ($relativePath in $requiredPaths) {
    $fullPath = Join-Path $repoRoot $relativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw "Missing required Phase 0 path: $relativePath"
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Warning 'Docker is not installed or not on PATH; skipped Compose validation.'
}

else {
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

Write-Host 'Phase 0 verification passed.'
