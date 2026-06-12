# Run Alembic migrations for all services on Windows
# Requires: uv installed and available in PATH, Postgres running,
#           env vars (or .env) loaded with DB credentials.

$services = @(
    "auth",
    "gateway",
    "description-enricher",
    "sprint-summary",
    "test-case-generator"
)

$root = Get-Location

foreach ($service in $services) {
    $serviceDir = Join-Path $root "services" $service
    Write-Host "`n==> Running migrations for $service..." -ForegroundColor Cyan
    Set-Location $serviceDir
    uv run alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Migration failed for $service" -ForegroundColor Red
        Set-Location $root
        exit 1
    }
}

Set-Location $root
Write-Host "`nAll migrations applied." -ForegroundColor Green
