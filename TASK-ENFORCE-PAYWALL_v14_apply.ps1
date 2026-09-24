$ErrorActionPreference = 'Stop'

$repo = (Get-Location).Path
$trackDetailPath = Join-Path $repo 'frontend\src\pages\TrackDetail.tsx'

Write-Host '===== TASK-ENFORCE-PAYWALL v14 FINAL FRONTEND CONTRACT REPAIR ====='
Write-Host "Repository: $repo"

if (-not (Test-Path $trackDetailPath)) {
    throw "Missing frontend/src/pages/TrackDetail.tsx; no write performed."
}

$trackDetail = Get-Content -Raw -Encoding UTF8 $trackDetailPath

Write-Host '===== AUDIT PAYMENTCHECKOUT CALL ====='
if ($trackDetail -notmatch 'onEnrollmentCreated\s*=\s*\{\s*handleEnrollmentCreated\s*\}') {
    throw 'Expected onEnrollmentCreated prop usage not found; no write performed.'
}

$old = '                onEnrollmentCreated={handleEnrollmentCreated}\r?\n'
if ($trackDetail -notmatch $old) {
    throw 'Expected PaymentCheckout onEnrollmentCreated line not found in expected indentation; no write performed.'
}

$patched = [regex]::Replace(
    $trackDetail,
    '^[ \t]*onEnrollmentCreated\s*=\s*\{\s*handleEnrollmentCreated\s*\}\r?\n',
    '',
    [System.Text.RegularExpressions.RegexOptions]::Multiline
)

if ($patched -eq $trackDetail) {
    throw 'Patch produced no change; no write performed.'
}

[System.IO.File]::WriteAllText($trackDetailPath, $patched, (New-Object System.Text.UTF8Encoding($false)))
Write-Host 'Patched: frontend/src/pages/TrackDetail.tsx'
Write-Host 'No git commands executed. No commit created.'

Write-Host '===== STATIC SECURITY ASSERTIONS ====='
$trackDetailAfter = Get-Content -Raw -Encoding UTF8 $trackDetailPath
if ($trackDetailAfter -match 'onEnrollmentCreated\s*=') {
    throw 'onEnrollmentCreated prop still exists in TrackDetail.tsx.'
}
if ($trackDetailAfter -notmatch 'const\s+hasCurriculumAccess\s*=\s*currentEnrollment\?\.status\s*===\s*"active"') {
    throw 'TrackDetail hasCurriculumAccess guard missing.'
}
if ($trackDetailAfter -notmatch 'PaymentCheckout') {
    throw 'PaymentCheckout missing from TrackDetail.tsx.'
}
Write-Host 'PASS'

$env:DATABASE_URL = 'postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_db'
$env:ADMIN_DATABASE_URL = 'postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/postgres'
$env:TEST_DATABASE_URL = 'postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_test_db'

Write-Host '===== ALEMBIC CURRENT (backend) ====='
Push-Location (Join-Path $repo 'backend')
try {
    python -m alembic current
    if ($LASTEXITCODE -ne 0) { throw 'Alembic current failed.' }

    Write-Host '===== RUFF CHECK (backend) ====='
    python -m ruff check app
    if ($LASTEXITCODE -ne 0) { throw 'Ruff check failed.' }

    Write-Host '===== FULL PYTEST (backend) ====='
    python -m pytest -ra -q
    if ($LASTEXITCODE -ne 0) { throw 'Pytest failed.' }
}
finally {
    Pop-Location
}

Write-Host '===== TYPESCRIPT ====='
Push-Location (Join-Path $repo 'frontend')
try {
    npx.cmd tsc --noEmit
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript check failed.' }

    Write-Host '===== OXLINT ====='
    npx.cmd oxlint
    if ($LASTEXITCODE -ne 0) { throw 'Oxlint failed.' }

    Write-Host '===== PRODUCTION BUILD ====='
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Production build failed.' }
}
finally {
    Pop-Location
}

Write-Host '===== TASK-ENFORCE-PAYWALL v14 VERIFICATION PASSED ====='
Write-Host 'Paywall source contract and all requested verification gates passed.'
Write-Host 'No git commands executed. No commit created.'
