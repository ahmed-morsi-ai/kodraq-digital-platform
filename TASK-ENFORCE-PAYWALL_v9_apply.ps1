$ErrorActionPreference = 'Stop'

function Read-Utf8([string]$Path) {
    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
}

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    [System.IO.File]::WriteAllText(
        $Path,
        $Content.TrimEnd() + "`r`n",
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Require-Text([string]$Text, [string]$Needle, [string]$Description) {
    if (-not $Text.Contains($Needle)) {
        throw "Required assertion missing: $Description"
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path (Join-Path $ScriptDir 'backend')) {
    $RepoRoot = $ScriptDir
} elseif (Test-Path (Join-Path (Get-Location).Path 'backend')) {
    $RepoRoot = (Get-Location).Path
} else {
    throw 'Run this script from the Kodraq repository root, or place this script beside the backend and frontend folders.'
}

$BackendRoot = Join-Path $RepoRoot 'backend'
$FrontendRoot = Join-Path $RepoRoot 'frontend'
$enrollmentsPath = Join-Path $BackendRoot 'app\api\v1\enrollments.py'
$tracksPath = Join-Path $BackendRoot 'app\api\v1\tracks.py'
$checkoutPath = Join-Path $FrontendRoot 'src\components\PaymentCheckout.tsx'
$trackDetailPath = Join-Path $FrontendRoot 'src\pages\TrackDetail.tsx'

foreach ($path in @($enrollmentsPath, $tracksPath, $checkoutPath, $trackDetailPath)) {
    if (-not (Test-Path $path)) {
        throw "Required file missing: $path"
    }
}

Write-Host '===== TASK-ENFORCE-PAYWALL v9 REPAIR AUDIT =====' -ForegroundColor Cyan
Write-Host "Repository: $RepoRoot"
Write-Host 'AUDIT PASS: required backend and frontend files exist.' -ForegroundColor Green

$enrollmentsText = Read-Utf8 $enrollmentsPath
$tracksText = Read-Utf8 $tracksPath
$checkoutText = Read-Utf8 $checkoutPath
$trackDetailText = Read-Utf8 $trackDetailPath

# -----------------------------------------------------------------
# 1. Repair only the malformed source produced by v8.
# -----------------------------------------------------------------
if ($enrollmentsText -notmatch '(?m)\)\s+track\s*=\s*crud_track\.get\(') {
    throw 'Expected v8 malformed enrollment source was not found; refusing an unrelated rewrite.'
}

$originalEnrollmentsText = $enrollmentsText
$enrollmentsText = $enrollmentsText.Replace(
    ')    track = crud_track.get(',
    ")`r`n    track = crud_track.get("
)
if ($enrollmentsText -eq $originalEnrollmentsText) {
    throw 'Enrollment syntax repair did not change the expected malformed line.'
}

# Keep future imports first, then let Ruff normalize the ordinary import block.
$futurePattern = '(?m)^\s*from __future__ import annotations\s*\r?\n'
$enrollmentsText = [regex]::Replace($enrollmentsText, $futurePattern, '')
$enrollmentsText = "from __future__ import annotations`r`n`r`n" + $enrollmentsText.TrimStart()

$tracksText = [regex]::Replace($tracksText, $futurePattern, '')
$tracksText = "from __future__ import annotations`r`n`r`n" + $tracksText.TrimStart()

# Normalize the Enrollment model import location; keep exactly one import.
$tracksText = [regex]::Replace(
    $tracksText,
    '(?m)^from app\.models\.enrollment import Enrollment\s*\r?\n',
    ''
)
$trackImportMarker = 'from app.models.track import Track'
if ($tracksText.IndexOf($trackImportMarker) -lt 0) {
    throw 'tracks.py no longer contains the expected Track model import; refusing an unrelated rewrite.'
}
$tracksText = $tracksText.Replace(
    $trackImportMarker,
    "from app.models.enrollment import Enrollment`r`n" + $trackImportMarker
)

# Persist only the repair above before linting; no application logic is changed here.
Write-Host ''
Write-Host '===== REPAIRING v8 SOURCE DEFECTS =====' -ForegroundColor Cyan
Write-Utf8NoBom $enrollmentsPath $enrollmentsText
Write-Utf8NoBom $tracksPath $tracksText
Write-Host 'Repaired: backend/app/api/v1/enrollments.py syntax/import placement' -ForegroundColor Green
Write-Host 'Repaired: backend/app/api/v1/tracks.py future/import placement' -ForegroundColor Green
Write-Host 'No git commands executed. No commit created.' -ForegroundColor Yellow

# -----------------------------------------------------------------
# 2. Let Ruff normalize imports only, then verify the paywall invariants.
# -----------------------------------------------------------------
Push-Location $BackendRoot
try {
    Write-Host ''
    Write-Host '===== RUFF IMPORT NORMALIZATION =====' -ForegroundColor Cyan
    python -m ruff check --fix app\api\v1\enrollments.py app\api\v1\tracks.py
    if ($LASTEXITCODE -ne 0) { throw 'Ruff normalization failed.' }
} finally {
    Pop-Location
}

$enrollmentsVerify = Read-Utf8 $enrollmentsPath
$tracksVerify = Read-Utf8 $tracksPath
$checkoutVerify = Read-Utf8 $checkoutPath
$trackDetailVerify = Read-Utf8 $trackDetailPath

Require-Text $enrollmentsVerify 'target_status = "pending_payment" if track.is_premium else "active"' 'server-controlled premium/free status'
Require-Text $enrollmentsVerify 'enrollment_payload = enrollment_in.model_copy' 'server-controlled enrollment payload'
Require-Text $tracksVerify 'current_user: CurrentUserDep' 'authenticated curriculum route'
Require-Text $tracksVerify 'Enrollment.user_id == current_user.id' 'user-specific enrollment lookup'
Require-Text $tracksVerify 'Enrollment.track_id == track_id' 'track-specific enrollment lookup'
Require-Text $tracksVerify 'current_user.is_superuser' 'superuser curriculum bypass'
Require-Text $tracksVerify 'track.modules = []' 'locked curriculum response'
Require-Text $checkoutVerify 'Payment Pending Admin Approval' 'pending payment approval message'
Require-Text $checkoutVerify 'paymentService.submitPayment(track.id, method, receiptFile)' 'premium payment submission'
if ($checkoutVerify -match '\benrollmentService\.') {
    throw 'SECURITY ASSERTION FAILED: PaymentCheckout still references enrollmentService.'
}
if ($checkoutVerify -match 'onEnrollmentCreated') {
    throw 'SECURITY ASSERTION FAILED: PaymentCheckout still exposes onEnrollmentCreated.'
}
Require-Text $trackDetailVerify 'const hasCurriculumAccess = currentEnrollment?.status === "active";' 'strict active curriculum access'
Require-Text $trackDetailVerify 'if (track && !isEnrollmentLoading && !hasCurriculumAccess)' 'sales-page early return'
Require-Text $trackDetailVerify '<PaymentCheckout' 'sales-page payment checkout'
Require-Text $trackDetailVerify 'What you will learn' 'sales-page learning outcomes'

Write-Host 'Static security assertions: PASS' -ForegroundColor Green

# -----------------------------------------------------------------
# 3. Full verification gates.
# -----------------------------------------------------------------
$env:DATABASE_URL = 'postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_db'
$env:ADMIN_DATABASE_URL = 'postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/postgres'
$env:TEST_DATABASE_URL = 'postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_test_db'

Push-Location $BackendRoot
try {
    Write-Host ''
    Write-Host '===== ALEMBIC CURRENT =====' -ForegroundColor Cyan
    python -m alembic current
    if ($LASTEXITCODE -ne 0) { throw 'Alembic current failed.' }

    Write-Host ''
    Write-Host '===== RUFF CHECK =====' -ForegroundColor Cyan
    python -m ruff check app
    if ($LASTEXITCODE -ne 0) { throw 'Ruff check failed.' }

    Write-Host ''
    Write-Host '===== PYTEST =====' -ForegroundColor Cyan
    python -m pytest -ra -q
    if ($LASTEXITCODE -ne 0) { throw 'Pytest failed.' }
} finally {
    Pop-Location
}

Push-Location $FrontendRoot
try {
    Write-Host ''
    Write-Host '===== TYPESCRIPT CHECK =====' -ForegroundColor Cyan
    npx.cmd tsc --noEmit
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript check failed.' }

    Write-Host ''
    Write-Host '===== OXLINT =====' -ForegroundColor Cyan
    npx.cmd oxlint
    if ($LASTEXITCODE -ne 0) { throw 'oxlint failed.' }

    Write-Host ''
    Write-Host '===== PRODUCTION BUILD =====' -ForegroundColor Cyan
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Production build failed.' }
} finally {
    Pop-Location
}

Write-Host ''
Write-Host 'TASK-ENFORCE-PAYWALL v9 VERIFICATION PASSED.' -ForegroundColor Green
Write-Host 'No git commands executed. No commit created.' -ForegroundColor Yellow
