$ErrorActionPreference = "Stop"

$repo = (Get-Location).Path
Write-Host "===== TASK-ENFORCE-PAYWALL v10 TEST CONTRACT REPAIR ====="
Write-Host "Repository: $repo"

$testPath = Join-Path $repo "backend\tests\integration\test_api_tracks_enrollments.py"
if (-not (Test-Path $testPath)) {
    throw "Required integration test file not found."
}

$testText = Get-Content $testPath -Raw

$pattern = '(?ms)    curriculum = client\.get\(\r?\n        f"/api/v1/tracks/\{track_id\}/curriculum"\r?\n    \)\r?\n\r?\n    assert curriculum\.status_code == status\.HTTP_200_OK\r?\n    data = curriculum\.json\(\)\r?\n    assert data\["id"\] == track_id\r?\n    assert len\(data\["modules"\]\) == 1\r?\n    assert len\(data\["modules"\]\[0\]\["lessons"\]\) == 1\r?\n    assert len\(data\["modules"\]\[0\]\["resources"\]\) == 1'

$replacement = @"
    unauthenticated_curriculum = client.get(
        f"/api/v1/tracks/{track_id}/curriculum"
    )
    assert unauthenticated_curriculum.status_code == status.HTTP_401_UNAUTHORIZED

    locked_curriculum = client.get(
        f"/api/v1/tracks/{track_id}/curriculum",
        headers=student_headers,
    )
    assert locked_curriculum.status_code == status.HTTP_200_OK
    locked_data = locked_curriculum.json()
    assert locked_data["id"] == track_id
    assert locked_data["modules"] == []

    curriculum = client.get(
        f"/api/v1/tracks/{track_id}/curriculum",
        headers=admin_headers,
    )
    assert curriculum.status_code == status.HTTP_200_OK
    data = curriculum.json()
    assert data["id"] == track_id
    assert len(data["modules"]) == 1
    assert len(data["modules"][0]["lessons"]) == 1
    assert len(data["modules"][0]["resources"]) == 1
"@

$updated = [regex]::Replace($testText, $pattern, $replacement, 1)
if ($updated -eq $testText) {
    throw "Could not locate the legacy unauthenticated curriculum assertions; no write performed."
}

Set-Content -Path $testPath -Value $updated -Encoding UTF8
Write-Host "Patched: $testPath"
Write-Host "No git commands executed. No commit created."

Write-Host ""
Write-Host "===== TEST CONTRACT STATIC ASSERTIONS ====="
$final = Get-Content $testPath -Raw
$required = @(
    'unauthenticated_curriculum.status_code == status.HTTP_401_UNAUTHORIZED',
    'headers=student_headers',
    'locked_data["modules"] == []',
    'headers=admin_headers',
    'len(data["modules"]) == 1'
)
foreach ($needle in $required) {
    if ($final -notmatch [regex]::Escape($needle)) {
        throw "Test contract assertion missing: $needle"
    }
}
Write-Host "PASS"

$backend = Join-Path $repo "backend"
$frontend = Join-Path $repo "frontend"

Push-Location $backend
try {
    Write-Host ""
    Write-Host "===== ALEMBIC CURRENT ====="
    python -m alembic current
    if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

    Write-Host ""
    Write-Host "===== RUFF CHECK ====="
    python -m ruff check app
    if ($LASTEXITCODE -ne 0) { throw "Ruff check failed." }

    Write-Host ""
    Write-Host "===== PYTEST ====="
    python -m pytest -ra -q
    if ($LASTEXITCODE -ne 0) { throw "Pytest failed." }
}
finally {
    Pop-Location
}

Push-Location $frontend
try {
    Write-Host ""
    Write-Host "===== TYPESCRIPT ====="
    npx.cmd tsc --noEmit
    if ($LASTEXITCODE -ne 0) { throw "TypeScript check failed." }

    Write-Host ""
    Write-Host "===== OXLINT ====="
    npx.cmd oxlint
    if ($LASTEXITCODE -ne 0) { throw "Oxlint failed." }

    Write-Host ""
    Write-Host "===== PRODUCTION BUILD ====="
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "===== TASK-ENFORCE-PAYWALL v10 VERIFICATION PASSED ====="
Write-Host "Paywall source changes were preserved from v9."
Write-Host "Curriculum integration test updated to enforce authentication, locked curriculum, and superuser access."
Write-Host "No git commands executed. No commit created."
