$ErrorActionPreference = 'Stop'

$repo = (Get-Location).Path
$trackDetailPath = Join-Path $repo 'frontend\src\pages\TrackDetail.tsx'

Write-Host '===== TASK-ENFORCE-PAYWALL v15 FRONTEND CALLBACK REPAIR ====='
Write-Host "Repository: $repo"

if (-not (Test-Path $trackDetailPath)) {
    throw 'Missing frontend/src/pages/TrackDetail.tsx; no write performed.'
}

$trackDetail = Get-Content -Raw -Encoding UTF8 $trackDetailPath

Write-Host '===== AUDIT CURRENT TRACKDETAIL CALLBACK CONTRACT ====='

if ($trackDetail -notmatch 'const\s+handleEnrollmentCreated\s*=\s*\(\s*enrollment:\s*Enrollment\s*\)') {
    throw 'handleEnrollmentCreated callback is missing; no write performed.'
}

$enrollmentPanelMatches = [regex]::Matches(
    $trackDetail,
    '(?ms)<EnrollmentPanel\b.*?/>'
)

if ($enrollmentPanelMatches.Count -ne 2) {
    throw "Expected exactly 2 self-closing EnrollmentPanel usages, found $($enrollmentPanelMatches.Count); no write performed."
}

$paymentCheckoutMatches = [regex]::Matches(
    $trackDetail,
    '(?ms)<PaymentCheckout\b.*?/>'
)

if ($paymentCheckoutMatches.Count -lt 1) {
    throw 'PaymentCheckout usage not found; no write performed.'
}

foreach ($match in $paymentCheckoutMatches) {
    if ($match.Value -match 'onEnrollmentCreated\s*=') {
        throw 'PaymentCheckout still receives onEnrollmentCreated; no write performed.'
    }
}

foreach ($match in $enrollmentPanelMatches) {
    if ($match.Value -notmatch 'onEnrollmentCreated\s*=\s*\{\s*handleEnrollmentCreated\s*\}') {
        $originalBlock = $match.Value
        $patchedBlock = [regex]::Replace(
            $originalBlock,
            '\s*/>$',
            "`r`n              onEnrollmentCreated={handleEnrollmentCreated}`r`n            />"
        )

        if ($patchedBlock -eq $originalBlock) {
            throw 'Could not patch an EnrollmentPanel callback; no write performed.'
        }

        $trackDetail = $trackDetail.Replace($originalBlock, $patchedBlock)
    }
}

if ($trackDetail -notmatch 'onEnrollmentCreated\s*=\s*\{\s*handleEnrollmentCreated\s*\}') {
    throw 'EnrollmentPanel callback insertion did not occur; no write performed.'
}

[System.IO.File]::WriteAllText(
    $trackDetailPath,
    $trackDetail,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host 'Patched: frontend/src/pages/TrackDetail.tsx'
Write-Host 'No git commands executed. No commit created.'

Write-Host '===== STATIC SECURITY ASSERTIONS ====='
$trackDetailAfter = Get-Content -Raw -Encoding UTF8 $trackDetailPath

$finalEnrollmentPanels = [regex]::Matches(
    $trackDetailAfter,
    '(?ms)<EnrollmentPanel\b.*?/>'
)
if ($finalEnrollmentPanels.Count -ne 2) {
    throw 'Post-write EnrollmentPanel count is not exactly 2.'
}
foreach ($match in $finalEnrollmentPanels) {
    if ($match.Value -notmatch 'onEnrollmentCreated\s*=\s*\{\s*handleEnrollmentCreated\s*\}') {
        throw 'An EnrollmentPanel is missing onEnrollmentCreated after patch.'
    }
}

$finalPaymentCheckouts = [regex]::Matches(
    $trackDetailAfter,
    '(?ms)<PaymentCheckout\b.*?/>'
)
if ($finalPaymentCheckouts.Count -lt 1) {
    throw 'PaymentCheckout is missing after patch.'
}
foreach ($match in $finalPaymentCheckouts) {
    if ($match.Value -match 'onEnrollmentCreated\s*=') {
        throw 'PaymentCheckout incorrectly contains onEnrollmentCreated after patch.'
    }
}

if ($trackDetailAfter -notmatch 'const\s+hasCurriculumAccess\s*=\s*currentEnrollment\?\.status\s*===\s*"active"') {
    throw 'TrackDetail hasCurriculumAccess guard missing.'
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

Write-Host '===== TASK-ENFORCE-PAYWALL v15 VERIFICATION PASSED ====='
Write-Host 'Paywall source contract and all requested verification gates passed.'
Write-Host 'No git commands executed. No commit created.'
