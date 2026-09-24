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
        throw "Audit/patch anchor missing: $Description"
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

Write-Host '===== TASK-ENFORCE-PAYWALL v8 AUDIT =====' -ForegroundColor Cyan
Write-Host "Repository: $RepoRoot"
Write-Host 'AUDIT PASS: required backend and frontend files exist.' -ForegroundColor Green

$enrollmentsText = Read-Utf8 $enrollmentsPath
$tracksText = Read-Utf8 $tracksPath
$checkoutText = Read-Utf8 $checkoutPath
$trackDetailText = Read-Utf8 $trackDetailPath

# ------------------------------------------------------------
# 1. BACKEND: enrollment status hardening
# ------------------------------------------------------------
Require-Text $enrollmentsText 'def create_enrollment' 'create_enrollment endpoint'
Require-Text $enrollmentsText 'enrollment_in' 'EnrollmentCreate input in create_enrollment'

if ($enrollmentsText -notmatch '(?m)^from fastapi import .*HTTPException') {
    throw 'enrollments.py does not expose HTTPException from FastAPI; refusing to synthesize a different error strategy.'
}
if ($enrollmentsText -notmatch '(?m)^from app\.models\.track import\s') {
    $enrollmentsText = "from app.models.track import Track`r`n" + $enrollmentsText
} elseif ($enrollmentsText -notmatch '(?ms)^from app\.models\.track import(?:\([^)]*\)|[^\r\n]*)\bTrack\b') {
    $enrollmentsText = "from app.models.track import Track`r`n" + $enrollmentsText
}

$createMatch = [regex]::Match(
    $enrollmentsText,
    '(?ms)(?<signature>^(?:async\s+)?def\s+create_enrollment\s*\(.*?\)\s*(?:->\s*[^:\r\n]+)?\s*:\s*\r?\n)(?<body>.*?)(?=^\s*@router\.|^(?:async\s+)?def\s+|^class\s+|\z)'
)
if (-not $createMatch.Success) {
    throw 'Could not isolate create_enrollment safely; no write performed.'
}

$createSignature = $createMatch.Groups['signature'].Value
$createBody = $createMatch.Groups['body'].Value
if ($createBody -notmatch '\benrollment_in\b') {
    throw 'create_enrollment body does not reference enrollment_in; no write performed.'
}

$sessionName = 'session'
$sessionMatch = [regex]::Match($createSignature, '(?m)(?<name>\w+)\s*:\s*SessionDep')
if ($sessionMatch.Success) {
    $sessionName = $sessionMatch.Groups['name'].Value
}

$createBody = [regex]::Replace($createBody, '\benrollment_in\b', 'enrollment_payload')
$hardeningBlock = @"
    track = $sessionName.get(Track, enrollment_in.track_id)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found.",
        )

    target_status = "pending_payment" if track.is_premium else "active"
    enrollment_payload = enrollment_in.model_copy(
        update={"status": target_status},
    )
"@
$createBody = [regex]::Replace($createBody, '^', $hardeningBlock, 1)

$enrollmentsText = $enrollmentsText.Remove(
    $createMatch.Groups['body'].Index,
    $createMatch.Groups['body'].Length
).Insert(
    $createMatch.Groups['body'].Index,
    $createBody
)

Require-Text $enrollmentsText 'target_status = "pending_payment" if track.is_premium else "active"' 'premium/free target status override'
Require-Text $enrollmentsText 'enrollment_payload = enrollment_in.model_copy' 'server-controlled enrollment payload'

# ------------------------------------------------------------
# 2. BACKEND: curriculum authorization lock
# ------------------------------------------------------------
Require-Text $tracksText '/{track_id}/curriculum' 'track curriculum route'
if ($tracksText -notmatch '(?m)^from sqlalchemy import .*\bselect\b') {
    if ($tracksText -match '(?m)^from sqlalchemy import\s+(?<rest>[^\r\n]+)$') {
        $sqlImport = [regex]::Match($tracksText, '(?m)^from sqlalchemy import\s+(?<rest>[^\r\n]+)$')
        $tracksText = $tracksText.Replace($sqlImport.Value, "from sqlalchemy import select, $($sqlImport.Groups['rest'].Value)")
    } else {
        $tracksText = "from sqlalchemy import select`r`n" + $tracksText
    }
}
if ($tracksText -notmatch '(?ms)^from app\.models\.enrollment import(?:\([^)]*\)|[^\r\n]*)\bEnrollment\b') {
    $tracksText = "from app.models.enrollment import Enrollment`r`n" + $tracksText
}

$curriculumMatch = [regex]::Match(
    $tracksText,
    '(?ms)(?<block>^@router\.get\(\s*["'']/{track_id}/curriculum["''].*?^def\s+\w+\s*\(.*?^\s*return\s+\w+\s*$)'
)
if (-not $curriculumMatch.Success) {
    throw 'Could not isolate GET /{track_id}/curriculum safely; no write performed.'
}

$curriculumBlock = $curriculumMatch.Groups['block'].Value
if ($curriculumBlock -notmatch '(?m)^\s*track\s*=') {
    throw 'Curriculum route does not expose a track variable; no write performed.'
}

# The existing dependency alias is CurrentUserDep. Enforce authentication at the route
# boundary rather than assuming the route already receives a concrete current_user name.
if ($curriculumBlock -notmatch '\bcurrent_user\s*:\s*CurrentUserDep') {
    $sessionCrLf = "    session: SessionDep,`r`n"
    $sessionLf = "    session: SessionDep,`n"
    $userCrLf = "    session: SessionDep,`r`n    current_user: CurrentUserDep,`r`n"
    $userLf = "    session: SessionDep,`n    current_user: CurrentUserDep,`n"

    if ($curriculumBlock.Contains($sessionCrLf)) {
        $curriculumBlock = $curriculumBlock.Replace($sessionCrLf, $userCrLf)
    } elseif ($curriculumBlock.Contains($sessionLf)) {
        $curriculumBlock = $curriculumBlock.Replace($sessionLf, $userLf)
    } else {
        throw 'Could not add CurrentUserDep to curriculum route signature; no write performed.'
    }
}

if ($curriculumBlock -notmatch '\bcurrent_user\s*:\s*CurrentUserDep') {
    throw 'Curriculum route does not expose CurrentUserDep after patch preparation; no write performed.'
}

$curriculumSession = 'session'
$curriculumSigMatch = [regex]::Match($curriculumBlock, '(?m)(?<name>\w+)\s*:\s*SessionDep')
if ($curriculumSigMatch.Success) {
    $curriculumSession = $curriculumSigMatch.Groups['name'].Value
}

if ($curriculumBlock -notmatch 'Enrollment\.user_id == current_user\.id') {
    $lockBlock = @"
    enrollment = $curriculumSession.scalar(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.track_id == track_id,
        )
    )
    if not current_user.is_superuser and (
        enrollment is None or enrollment.status != "active"
    ):
        track.modules = []

"@
    $returnMatches = [regex]::Matches($curriculumBlock, '(?m)^\s*return\s+')
    if ($returnMatches.Count -eq 0) {
        throw 'Curriculum route has no return statement; no write performed.'
    }
    $lastReturn = $returnMatches[$returnMatches.Count - 1]
    $curriculumBlock = $curriculumBlock.Insert($lastReturn.Index, $lockBlock)
}

Require-Text $curriculumBlock 'Enrollment.user_id == current_user.id' 'current-user enrollment lookup'
Require-Text $curriculumBlock 'Enrollment.track_id == track_id' 'requested-track enrollment lookup'
Require-Text $curriculumBlock 'current_user.is_superuser' 'superuser curriculum bypass'
Require-Text $curriculumBlock 'track.modules = []' 'locked curriculum payload'

$tracksText = $tracksText.Remove(
    $curriculumMatch.Groups['block'].Index,
    $curriculumMatch.Groups['block'].Length
).Insert(
    $curriculumMatch.Groups['block'].Index,
    $curriculumBlock
)

# ------------------------------------------------------------
# 3. FRONTEND: PaymentCheckout — no enrollment API call
# ------------------------------------------------------------
Require-Text $checkoutText 'paymentService.submitPayment(track.id, method, receiptFile)' 'payment receipt submission'

$checkoutText = [regex]::Replace($checkoutText, '(?m)^import \{ enrollmentService \} from "@/services/enrollment.service";\r?\n', '')
$checkoutText = [regex]::Replace($checkoutText, '(?m)^\s*onEnrollmentCreated:\s*\(enrollment:\s*Enrollment\)\s*=>\s*void;\r?\n', '')
$checkoutText = [regex]::Replace($checkoutText, '(?m)^\s*const \[isEnrollmentSubmitting, setIsEnrollmentSubmitting\] = useState\(false\);\r?\n', '')
$checkoutText = [regex]::Replace($checkoutText, '([ \t]*enrollment,\r?\n)[ \t]*onEnrollmentCreated,\r?\n', '$1')

# Remove the obsolete enrollment-start handler by function boundaries, not exact whitespace.
$startHandlerPattern = '(?ms)^\s*async\s+function\s+handleStartCheckout\s*\(\)\s*\{.*?^\s*\}\s*(?=^\s*(?:async\s+)?function\s+|^\s*return\s*\()'
$checkoutText = [regex]::Replace($checkoutText, $startHandlerPattern, '')

# Remove any remaining enrollmentService import/call lines defensively.
$checkoutText = [regex]::Replace($checkoutText, '(?m)^\s*import[^\r\n]*\benrollmentService\b[^\r\n]*\r?\n', '')
$checkoutText = [regex]::Replace($checkoutText, '(?m)^.*\benrollmentService\.enroll\b.*(?:\r?\n|$)', '')
$checkoutText = [regex]::Replace($checkoutText, '(?m)^\s*(?:onEnrollmentCreated|setIsEnrollmentSubmitting|isEnrollmentSubmitting)\b.*(?:\r?\n|$)', '')

$oldFallbackButton = @'
        <Button
          type="button"
          disabled={isEnrollmentSubmitting}
          onClick={() => void handleStartCheckout()}
          className="w-full gap-2 bg-blue-600 text-white hover:bg-blue-700"
        >
          {isEnrollmentSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Starting checkout...
            </>
          ) : (
            <>
              <CreditCard className="h-4 w-4" />
              Enroll & pay
            </>
          )}
        </Button>
'@
$newFallbackButton = @'
        <Button
          type="button"
          onClick={() => {
            setError(null);
            setSuccess(false);
            setIsCheckoutOpen(true);
          }}
          className="w-full gap-2 bg-blue-600 text-white hover:bg-blue-700"
        >
          <CreditCard className="h-4 w-4" />
          Continue to payment
        </Button>
'@
$oldButtonCrLf = $oldFallbackButton -replace "`n", "`r`n"
$newButtonCrLf = $newFallbackButton -replace "`n", "`r`n"
if ($checkoutText.Contains($oldButtonCrLf)) {
    $checkoutText = $checkoutText.Replace($oldButtonCrLf, $newButtonCrLf)
} elseif ($checkoutText.Contains($oldFallbackButton)) {
    $checkoutText = $checkoutText.Replace($oldFallbackButton, $newFallbackButton)
} else {
    $legacyButtonPattern = '(?ms)^\s*<Button[^>]*>.*?onClick=\{\(\) => void handleStartCheckout\(\)\}.*?</Button>'
    $checkoutText = [regex]::Replace($checkoutText, $legacyButtonPattern, $newFallbackButton.Trim(), 1)
}

if ($checkoutText -notmatch 'Payment Pending Admin Approval') {
    $pendingNeedle = '        <CardContent className="space-y-6">'
    $pendingReplacement = @'
        <CardContent className="space-y-6">
          {hasPendingPayment && (
            <div className="rounded-xl border border-amber-200 bg-amber-100/60 px-4 py-3 text-sm font-semibold text-amber-900">
              Payment Pending Admin Approval
            </div>
          )}
'@
    $pendingReplacementCrLf = $pendingReplacement -replace "`n", "`r`n"
    if (-not $checkoutText.Contains($pendingNeedle)) {
        throw 'PaymentCheckout CardContent anchor not found for pending-status message.'
    }
    $checkoutText = $checkoutText.Replace($pendingNeedle, $pendingReplacementCrLf)
}

if ($checkoutText -match '\benrollmentService\.') {
    throw 'PaymentCheckout still contains an enrollmentService call after hardening; no write performed.'
}
Require-Text $checkoutText 'Payment Pending Admin Approval' 'exact pending approval message'
Require-Text $checkoutText 'paymentService.submitPayment(track.id, method, receiptFile)' 'exclusive payment submission call'
if ($checkoutText -match '\benrollmentService\b|handleStartCheckout|isEnrollmentSubmitting|onEnrollmentCreated') {
    throw 'PaymentCheckout still contains obsolete enrollment flow symbols after hardening; no write performed.'
}

# ------------------------------------------------------------
# 4. FRONTEND: TrackDetail — strict active access and sales funnel
# ------------------------------------------------------------
Require-Text $trackDetailText 'import EnrollmentPanel from "@/components/EnrollmentPanel";' 'existing enrollment panel import'
if ($trackDetailText -notmatch 'PaymentCheckout') {
    $newImport = 'import EnrollmentPanel from "@/components/EnrollmentPanel";' + "`r`n" + 'import PaymentCheckout from "@/components/PaymentCheckout";'
    $trackDetailText = $trackDetailText.Replace(
        'import EnrollmentPanel from "@/components/EnrollmentPanel";',
        $newImport
    )
}

if ($trackDetailText -notmatch 'const hasCurriculumAccess = currentEnrollment\?\.status === "active";') {
    $accessAnchor = @'
  const currentEnrollment = useMemo(
    () =>
      enrollments.find(
        (enrollment) => enrollment.track_id === numericTrackId,
      ),
    [enrollments, numericTrackId],
  );
'@
    $accessAnchorCrLf = $accessAnchor -replace "`n", "`r`n"
    $accessLine = '  const hasCurriculumAccess = currentEnrollment?.status === "active";'
    if ($trackDetailText.Contains($accessAnchorCrLf)) {
        $trackDetailText = $trackDetailText.Replace($accessAnchorCrLf, $accessAnchorCrLf + "`r`n$accessLine`r`n")
    } elseif ($trackDetailText.Contains($accessAnchor)) {
        $trackDetailText = $trackDetailText.Replace($accessAnchor, $accessAnchor + "`n$accessLine`n")
    } else {
        throw 'TrackDetail currentEnrollment anchor not found.'
    }
}

# Strengthen the assignments guard to active enrollment only.
$assignmentGuardOld = '      currentEnrollment.status === "cancelled"'
$assignmentGuardNew = '      currentEnrollment.status !== "active"'
if ($trackDetailText.Contains($assignmentGuardOld)) {
    $trackDetailText = $trackDetailText.Replace($assignmentGuardOld, $assignmentGuardNew)
} else {
    throw 'TrackDetail assignment access guard anchor not found.'
}

# The progress summary must render only for active enrollment.
$progressDisplayOld = @'
        {!isEnrollmentLoading &&
          currentEnrollment &&
          currentEnrollment.status !== "cancelled" && (
'@
$progressDisplayNew = @'
        {!isEnrollmentLoading &&
          currentEnrollment &&
          currentEnrollment.status === "active" && (
'@
$progressDisplayOldCrLf = $progressDisplayOld -replace "`n", "`r`n"
$progressDisplayNewCrLf = $progressDisplayNew -replace "`n", "`r`n"
if ($trackDetailText.Contains($progressDisplayOldCrLf)) {
    $trackDetailText = $trackDetailText.Replace($progressDisplayOldCrLf, $progressDisplayNewCrLf)
} elseif ($trackDetailText.Contains($progressDisplayOld)) {
    $trackDetailText = $trackDetailText.Replace($progressDisplayOld, $progressDisplayNew)
} else {
    throw 'TrackDetail progress display guard anchor not found.'
}

$oldEffect = @'
  useEffect(() => {
    if (
      currentEnrollment &&
      currentEnrollment.status !== "cancelled"
    ) {
      void loadProgress(currentEnrollment.id);
      void loadAssignments();
    } else {
      setProgress([]);
      setProgressError(null);
      setAssignments([]);
      setAssignmentsError(null);
    }
  }, [currentEnrollment, loadAssignments, loadProgress]);
'@
$newEffect = @'
  useEffect(() => {
    if (hasCurriculumAccess && currentEnrollment) {
      void loadProgress(currentEnrollment.id);
      void loadAssignments();
    } else {
      setProgress([]);
      setProgressError(null);
      setAssignments([]);
      setAssignmentsError(null);
    }
  }, [currentEnrollment, hasCurriculumAccess, loadAssignments, loadProgress]);
'@
$oldEffectCrLf = $oldEffect -replace "`n", "`r`n"
$newEffectCrLf = $newEffect -replace "`n", "`r`n"
if ($trackDetailText.Contains($oldEffectCrLf)) {
    $trackDetailText = $trackDetailText.Replace($oldEffectCrLf, $newEffectCrLf)
} elseif ($trackDetailText.Contains($oldEffect)) {
    $trackDetailText = $trackDetailText.Replace($oldEffect, $newEffect)
} else {
    throw 'TrackDetail enrollment-dependent effect anchor not found; no write performed.'
}

$oldProgressGuard = @'
  const handleProgressAction = async (lessonId: number) => {
    if (!currentEnrollment) {
      return;
    }
'@
$newProgressGuard = @'
  const handleProgressAction = async (lessonId: number) => {
    if (!currentEnrollment || currentEnrollment.status !== "active") {
      return;
    }
'@
$oldProgressGuardCrLf = $oldProgressGuard -replace "`n", "`r`n"
$newProgressGuardCrLf = $newProgressGuard -replace "`n", "`r`n"
if ($trackDetailText.Contains($oldProgressGuardCrLf)) {
    $trackDetailText = $trackDetailText.Replace($oldProgressGuardCrLf, $newProgressGuardCrLf)
} elseif ($trackDetailText.Contains($oldProgressGuard)) {
    $trackDetailText = $trackDetailText.Replace($oldProgressGuard, $newProgressGuard)
} else {
    throw 'TrackDetail progress-action guard anchor not found.'
}

# Render the paywall as an early-return sales page when curriculum access is not active.
# This avoids brittle JSX block matching while ensuring quizzes/assignments/curriculum are
# never rendered for locked/pending users.
$progressHandlerMarker = '  const handleProgressAction = async (lessonId: number) => {'
$mainReturnMarker = '  return ('
$progressHandlerIndex = $trackDetailText.IndexOf($progressHandlerMarker)
if ($progressHandlerIndex -lt 0) {
    throw 'TrackDetail progress handler anchor not found; no write performed.'
}
$mainReturnIndex = $trackDetailText.IndexOf($mainReturnMarker, $progressHandlerIndex)
if ($mainReturnIndex -lt 0) {
    throw 'TrackDetail main return anchor not found after progress handler; no write performed.'
}

$existingSalesGuard = '  if (track && !isEnrollmentLoading && !hasCurriculumAccess) {'
if ($trackDetailText.Contains($existingSalesGuard)) {
    throw 'TrackDetail already contains the generated sales-page guard; refusing duplicate insertion.'
}

$salesReturn = @'
  if (track && !isEnrollmentLoading && !hasCurriculumAccess) {
    return (
      <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <section className="space-y-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-600">
              Track preview
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
              {track.name}
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-gray-600">
              {track.description || "Build practical skills through a structured technical learning path."}
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-gray-50 p-6">
            <h2 className="text-xl font-semibold text-slate-900">What you will learn</h2>
            <ul className="mt-4 grid gap-3 text-sm leading-6 text-gray-600 md:grid-cols-2">
              <li>Structured modules with practical technical lessons.</li>
              <li>Hands-on exercises and track-specific problem solving.</li>
              <li>Projects, assessments, and measurable learning progress.</li>
              <li>Production-minded engineering skills aligned to the track.</li>
            </ul>
          </div>

          {track.is_premium ? (
            <PaymentCheckout
              track={track}
              enrollment={currentEnrollment}
            />
          ) : (
            <EnrollmentPanel
              trackId={numericTrackId}
              enrollment={currentEnrollment}
              onEnrollmentCreated={handleEnrollmentCreated}
            />
          )}
        </section>
      </div>
    );
  }
'@

$trackDetailText = $trackDetailText.Insert($mainReturnIndex, $salesReturn + "`r`n")

Require-Text $trackDetailText 'const hasCurriculumAccess = currentEnrollment?.status === "active";' 'strict active curriculum access guard'
Require-Text $trackDetailText '<PaymentCheckout' 'sales-funnel payment checkout'
Require-Text $trackDetailText 'What you will learn' 'sales-page learning outcomes'
Require-Text $trackDetailText 'if (track && !isEnrollmentLoading && !hasCurriculumAccess)' 'early-return locked sales page'
Require-Text $trackDetailText 'currentEnrollment.status !== "active"' 'active-only data-loading guard'

# ------------------------------------------------------------
# 5. WRITE ONLY AFTER ALL AUDITS/PATCHES PASS
# ------------------------------------------------------------
Write-Host ''
Write-Host '===== WRITING TASK-ENFORCE-PAYWALL CHANGES =====' -ForegroundColor Cyan
Write-Utf8NoBom $enrollmentsPath $enrollmentsText
Write-Utf8NoBom $tracksPath $tracksText
Write-Utf8NoBom $checkoutPath $checkoutText
Write-Utf8NoBom $trackDetailPath $trackDetailText

Write-Host 'Patched: backend/app/api/v1/enrollments.py' -ForegroundColor Green
Write-Host 'Patched: backend/app/api/v1/tracks.py' -ForegroundColor Green
Write-Host 'Patched: frontend/src/components/PaymentCheckout.tsx' -ForegroundColor Green
Write-Host 'Patched: frontend/src/pages/TrackDetail.tsx' -ForegroundColor Green
Write-Host 'No git commands executed. No commit created.' -ForegroundColor Yellow

# ------------------------------------------------------------
# 6. POST-WRITE SECURITY ASSERTIONS
# ------------------------------------------------------------
$enrollmentsVerify = Read-Utf8 $enrollmentsPath
$tracksVerify = Read-Utf8 $tracksPath
$checkoutVerify = Read-Utf8 $checkoutPath
$trackDetailVerify = Read-Utf8 $trackDetailPath

Require-Text $enrollmentsVerify 'target_status = "pending_payment" if track.is_premium else "active"' 'post-write enrollment status override'
Require-Text $enrollmentsVerify 'enrollment_payload = enrollment_in.model_copy' 'post-write enrollment payload'
Require-Text $tracksVerify 'Enrollment.user_id == current_user.id' 'post-write curriculum user enrollment lookup'
Require-Text $tracksVerify 'current_user: CurrentUserDep' 'post-write authenticated curriculum route'
Require-Text $tracksVerify 'track.modules = []' 'post-write locked curriculum'
Require-Text $checkoutVerify 'Payment Pending Admin Approval' 'post-write pending approval message'
Require-Text $checkoutVerify 'paymentService.submitPayment(track.id, method, receiptFile)' 'post-write payment call'
if ($checkoutVerify -match '\benrollmentService\.') {
    throw 'SECURITY ASSERTION FAILED: PaymentCheckout still references enrollmentService.'
}
Require-Text $trackDetailVerify 'const hasCurriculumAccess = currentEnrollment?.status === "active";' 'post-write strict access guard'
Require-Text $trackDetailVerify '<PaymentCheckout' 'post-write sales funnel'
Write-Host 'Static security assertions: PASS' -ForegroundColor Green

# ------------------------------------------------------------
# 7. VERIFICATION GATES
# ------------------------------------------------------------
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
}
finally {
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
}
finally {
    Pop-Location
}

Write-Host ''
Write-Host 'TASK-ENFORCE-PAYWALL v8 VERIFICATION PASSED.' -ForegroundColor Green
Write-Host 'No git commands executed. No commit created.' -ForegroundColor Yellow
