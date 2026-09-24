param(
    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$tracksPath = Join-Path $RepoRoot "backend\app\api\v1\tracks.py"
$testPath = Join-Path $RepoRoot "backend\tests\integration\test_api_tracks_enrollments.py"

Write-Host "===== TASK-ENFORCE-PAYWALL v11 ORM-SAFETY REPAIR ====="
Write-Host "Repository: $RepoRoot"

if (-not (Test-Path $tracksPath)) { throw "Missing backend/app/api/v1/tracks.py" }
if (-not (Test-Path $testPath)) { throw "Missing backend/tests/integration/test_api_tracks_enrollments.py" }

$tracks = Get-Content -Raw -Encoding UTF8 $tracksPath

$unsafe = @'
    if not current_user.is_superuser and (
        enrollment is None or enrollment.status != "active"
    ):
        track.modules = []

    return track
'@

$safe = @'
    track_payload = TrackCurriculum.model_validate(track)
    if not current_user.is_superuser and (
        enrollment is None or enrollment.status != "active"
    ):
        track_payload = track_payload.model_copy(update={"modules": []})

    return track_payload
'@

Write-Host "===== AUDIT CURRENT CURRICULUM GUARD ====="
if ($tracks -notmatch [regex]::Escape('current_user: CurrentUserDep')) {
    throw "CurrentUserDep guard missing; no write performed."
}
if ($tracks -notmatch [regex]::Escape($unsafe)) {
    if ($tracks -match [regex]::Escape('track_payload = TrackCurriculum.model_validate(track)')) {
        Write-Host "Safe curriculum response projection already present."
    } else {
        throw "Expected ORM mutation guard not found; no write performed."
    }
}

if ($tracks -match [regex]::Escape($unsafe)) {
    Copy-Item $tracksPath "$tracksPath.v11.bak" -Force
    $tracks = $tracks.Replace($unsafe, $safe)
    [System.IO.File]::WriteAllText($tracksPath, $tracks, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Patched: backend/app/api/v1/tracks.py"
} else {
    Write-Host "No source patch required."
}

$updated = Get-Content -Raw -Encoding UTF8 $tracksPath

Write-Host "===== STATIC SECURITY ASSERTIONS ====="
$assertions = @(
    'current_user: CurrentUserDep',
    'Enrollment.user_id == current_user.id',
    'Enrollment.track_id == track_id',
    'enrollment is None or enrollment.status != "active"',
    'track_payload = TrackCurriculum.model_validate(track)',
    'track_payload = track_payload.model_copy(update={"modules": []})',
    'current_user.is_superuser'
)
foreach ($needle in $assertions) {
    if ($updated -notmatch [regex]::Escape($needle)) {
        throw "Missing curriculum security assertion: $needle"
    }
}
if ($updated -match [regex]::Escape($unsafe)) {
    throw "Unsafe ORM relationship mutation remains; no verification pass."
}
Write-Host "PASS"

Write-Host "===== ALEMBIC CURRENT ====="
python -m alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

Write-Host "===== RUFF CHECK ====="
python -m ruff check app
if ($LASTEXITCODE -ne 0) { throw "Ruff check failed." }

Write-Host "===== TARGETED PYTEST ====="
python -m pytest tests/integration/test_api_tracks_enrollments.py::test_track_curriculum_endpoints_and_rbac -q
if ($LASTEXITCODE -ne 0) { throw "Targeted curriculum pytest failed." }

Write-Host "===== FULL PYTEST ====="
python -m pytest -ra -q
if ($LASTEXITCODE -ne 0) { throw "Full pytest failed." }

Write-Host "===== TYPESCRIPT ====="
Push-Location (Join-Path $RepoRoot "frontend")
npx.cmd tsc --noEmit
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "TypeScript check failed." }

Write-Host "===== OXLINT ====="
npx.cmd oxlint
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Oxlint failed." }

Write-Host "===== PRODUCTION BUILD ====="
npm.cmd run build
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Production build failed." }
Pop-Location

Write-Host "===== TASK-ENFORCE-PAYWALL v11 VERIFICATION PASSED ====="
Write-Host "No git commands executed. No commit created."
