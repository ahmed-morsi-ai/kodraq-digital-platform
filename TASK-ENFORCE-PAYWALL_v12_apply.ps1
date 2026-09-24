param(
    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$tracksPath = Join-Path $RepoRoot "backend\app\api\v1\tracks.py"
$testPath = Join-Path $RepoRoot "backend\tests\integration\test_api_tracks_enrollments.py"

Write-Host "===== TASK-ENFORCE-PAYWALL v12 CURRICULUM PROJECTION REPAIR ====="
Write-Host "Repository: $RepoRoot"

if (-not (Test-Path $tracksPath)) { throw "Missing backend/app/api/v1/tracks.py" }
if (-not (Test-Path $testPath)) { throw "Missing backend/tests/integration/test_api_tracks_enrollments.py" }

$tracks = Get-Content -Raw -Encoding UTF8 $tracksPath

Write-Host "===== AUDIT CURRENT CURRICULUM ROUTE ====="
if ($tracks -notmatch '(?ms)def\s+read_track_curriculum\s*\(.*?current_user:\s*CurrentUserDep') {
    throw "CurrentUserDep missing from curriculum route; no write performed."
}
if ($tracks -notmatch [regex]::Escape('Enrollment.user_id == current_user.id') -or
    $tracks -notmatch [regex]::Escape('Enrollment.track_id == track_id')) {
    throw "Enrollment lookup guard missing from curriculum route; no write performed."
}
if ($tracks -notmatch [regex]::Escape('current_user.is_superuser')) {
    throw "Superuser curriculum bypass missing; no write performed."
}

$unsafePattern = '(?ms)^\s*if\s+not\s+current_user\.is_superuser\s+and\s*\(\s*enrollment\s+is\s+None\s+or\s+enrollment\.status\s+!=\s+"active"\s*\):\s*\r?\n\s*track\.modules\s*=\s*\[\]\s*\r?\n\s*return\s+track\s*$'

$safePattern = '(?ms)^\s*(if\s+not\s+current_user\.is_superuser\s+and\s*\(\s*enrollment\s+is\s+None\s+or\s+enrollment\.status\s+!=\s+"active"\s*\):\s*\r?\n\s*track_payload\s*=\s*TrackCurriculum\.model_validate\(track,\s*from_attributes=True\)\s*\r?\n\s*track_payload\s*=\s*track_payload\.model_copy\(update=\{"modules":\s*\[\]\}\)\s*\r?\n\s*return\s+track_payload|track_payload\s*=\s*TrackCurriculum\.model_validate\(track,\s*from_attributes=True\)\s*\r?\n\s*if\s+not\s+current_user\.is_superuser\s+and)'

$projectionAlreadyPresent = $tracks -match [regex]::Escape('TrackCurriculum.model_validate(track, from_attributes=True)') -and
    $tracks -match [regex]::Escape('track_payload = track_payload.model_copy(update={"modules": []})') -and
    $tracks -notmatch [regex]::Escape('track.modules = []')

if ($projectionAlreadyPresent) {
    Write-Host "Safe response projection already present."
} elseif ($tracks -match $unsafePattern) {
    Copy-Item $tracksPath "$tracksPath.v12.bak" -Force
    $replacement = @"
    track_payload = TrackCurriculum.model_validate(track, from_attributes=True)
    if not current_user.is_superuser and (
        enrollment is None or enrollment.status != "active"
    ):
        track_payload = track_payload.model_copy(update={"modules": []})

    return track_payload
"@
    $patched = [regex]::Replace($tracks, $unsafePattern, $replacement, 1)
    if ($patched -eq $tracks) {
        throw "Curriculum guard replacement did not change source; no write performed."
    }
    [System.IO.File]::WriteAllText($tracksPath, $patched, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Patched: backend/app/api/v1/tracks.py"
} else {
    throw "Current curriculum guard does not match the audited source shape; no write performed."
}

$updated = Get-Content -Raw -Encoding UTF8 $tracksPath

Write-Host "===== STATIC SECURITY ASSERTIONS ====="
$assertions = @(
    'current_user: CurrentUserDep',
    'Enrollment.user_id == current_user.id',
    'Enrollment.track_id == track_id',
    'current_user.is_superuser',
    'TrackCurriculum.model_validate(track, from_attributes=True)',
    'track_payload = track_payload.model_copy(update={"modules": []})'
)
foreach ($needle in $assertions) {
    if ($updated -notmatch [regex]::Escape($needle)) {
        throw "Missing curriculum security assertion: $needle"
    }
}
if ($updated -match [regex]::Escape('track.modules = []')) {
    throw "Unsafe ORM relationship mutation remains; verification stopped."
}
if ($updated -notmatch '(?ms)return\s+track_payload\s*$') {
    throw "Curriculum route does not return the projected response; verification stopped."
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

Write-Host "===== TASK-ENFORCE-PAYWALL v12 VERIFICATION PASSED ====="
Write-Host "No git commands executed. No commit created."
