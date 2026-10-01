$ErrorActionPreference = 'Stop'

$RepoRoot = (Get-Location).Path
$BackendRoot = Join-Path $RepoRoot 'backend'
$FrontendRoot = Join-Path $RepoRoot 'frontend'
$TracksPath = Join-Path $BackendRoot 'app\api\v1\tracks.py'
$TrackDetailPath = Join-Path $FrontendRoot 'src\pages\TrackDetail.tsx'
$TestPath = Join-Path $BackendRoot 'tests\integration\test_api_tracks_enrollments.py'

function Read-Utf8([string]$Path) {
    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
}

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding($false)))
}

function Require-Text([string]$Text, [string]$Needle, [string]$Label) {
    if ($Text -notmatch [regex]::Escape($Needle)) {
        throw "Missing required source contract: $Label"
    }
}

Write-Host '===== TASK-SYLLABUS-PREVIEW v1 AUDIT ====='
Write-Host "Repository: $RepoRoot"

foreach ($path in @($TracksPath, $TrackDetailPath, $TestPath)) {
    if (-not (Test-Path $path)) {
        throw "Missing required file: $path; no write performed."
    }
}
Write-Host 'AUDIT PASS: required backend, frontend, and test files exist.'

$tracks = Read-Utf8 $TracksPath
$trackDetail = Read-Utf8 $TrackDetailPath
$testText = Read-Utf8 $TestPath

# -----------------------------------------------------------------------------
# BACKEND AUDIT
# -----------------------------------------------------------------------------
Write-Host '===== AUDIT BACKEND CURRICULUM CONTRACT ====='
Require-Text $tracks 'def read_track_curriculum(' 'curriculum route'
Require-Text $tracks 'current_user: CurrentUserDep' 'authenticated curriculum route'
Require-Text $tracks 'Enrollment.user_id == current_user.id' 'user enrollment lookup'
Require-Text $tracks 'Enrollment.track_id == track_id' 'track enrollment lookup'
Require-Text $tracks 'current_user.is_superuser' 'superuser bypass'
Require-Text $tracks 'track.modules = []' 'existing locked-curriculum mutation'

$lockedMessage = 'هذا المحتوى مقفل. يرجى الاشتراك في المسار لتتمكن من عرض تفاصيل الدرس.'

$backendGuardPattern = '(?ms)    enrollment = session\.scalar\(\s*select\(Enrollment\)\.where\(\s*Enrollment\.user_id == current_user\.id,\s*Enrollment\.track_id == track_id,\s*\)\s*\)\s*if not current_user\.is_superuser and \(\s*enrollment is None or enrollment\.status != "active"\s*\):\s*track\.modules = \[\]\s*return track'

if ($tracks -notmatch $backendGuardPattern) {
    throw 'Current curriculum guard does not match the audited ORM-mutation shape; no write performed.'
}

# -----------------------------------------------------------------------------
# FRONTEND AUDIT
# -----------------------------------------------------------------------------
Write-Host '===== AUDIT FRONTEND SYLLABUS/PAYMENT CONTRACT ====='
Require-Text $trackDetail 'const hasCurriculumAccess = currentEnrollment?.status === "active";' 'strict active access guard'
Require-Text $trackDetail '<PaymentCheckout' 'payment checkout integration'
Require-Text $trackDetail 'track.modules.map((module, moduleIndex) =>' 'syllabus module rendering'
Require-Text $trackDetail 'module.lessons.map((lesson, lessonIndex) =>' 'syllabus lesson rendering'
Require-Text $trackDetail '{track.description ||' 'hero description rendering'
Require-Text $trackDetail 'handleProgressAction' 'lesson interaction handler'

$earlySalesGuardPattern = '(?ms)^  if \(track && !isEnrollmentLoading && !hasCurriculumAccess\) \{.*?^  \}\r?\n\r?\n(?=  return \()'
$hasEarlySalesGuard = $trackDetail -match $earlySalesGuardPattern
if (-not $hasEarlySalesGuard) {
    Write-Host 'INFO: standalone early sales-page guard not present; continuing with current main render.'
}

# -----------------------------------------------------------------------------
# TEST AUDIT
# -----------------------------------------------------------------------------
Require-Text $testText 'locked_curriculum = client.get(' 'locked curriculum test'
Require-Text $testText 'curriculum = client.get(' 'superuser curriculum test'

Write-Host 'Static audit: PASS'

# -----------------------------------------------------------------------------
# BUILD NEW BACKEND ROUTE TAIL
# -----------------------------------------------------------------------------
$backendReplacement = @"
    enrollment = session.scalar(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.track_id == track_id,
        )
    )

    track_payload = TrackCurriculum.model_validate(
        track,
        from_attributes=True,
    )

    if not current_user.is_superuser and (
        enrollment is None or enrollment.status != "active"
    ):
        track_payload = track_payload.model_copy(
            update={
                "modules": [
                    module.model_copy(
                        update={
                            "lessons": [
                                lesson.model_copy(
                                    update={"content": "PLACEHOLDER_LOCKED_CONTENT"}
                                )
                                for lesson in module.lessons
                            ]
                        }
                    )
                    for module in track_payload.modules
                ]
            }
        )

    return track_payload
"@
$backendReplacement = $backendReplacement.Replace('PLACEHOLDER_LOCKED_CONTENT', $lockedMessage)
$backendReplacement = $backendReplacement -replace "`n", "`r`n"

$tracksPatched = [regex]::Replace(
    $tracks,
    $backendGuardPattern,
    [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $backendReplacement },
    1
)
if ($tracksPatched -eq $tracks) {
    throw 'Backend patch produced no change; no write performed.'
}

# -----------------------------------------------------------------------------
# FRONTEND PATCHES
# -----------------------------------------------------------------------------
$trackDetailPatched = $trackDetail

# Remove the previous paywall early-return so the syllabus always renders.
if ($hasEarlySalesGuard) {
    $trackDetailPatched = [regex]::Replace(
        $trackDetailPatched,
        $earlySalesGuardPattern,
        '',
        1
    )
}

# Restrict quizzes to active learners but keep the enrollment panel available for checkout/enrollment flows.
$quizPattern = '(?m)^\s*\{trackId \? <QuizList trackId=\{Number\(trackId\)\} /> : null\}'
$quizReplacement = @'
            {hasCurriculumAccess && trackId ? (
              <QuizList trackId={Number(trackId)} />
            ) : null}
'@
$quizReplacement = $quizReplacement -replace "`n", "`r`n"
if ($trackDetailPatched -notmatch $quizPattern) {
    throw 'Could not locate QuizList render contract; no write performed.'
}
$trackDetailPatched = [regex]::Replace($trackDetailPatched, $quizPattern, $quizReplacement, 1)

# Prevent unauthorised lesson actions; keep the syllabus outline visible.
$buttonDisabledPattern = 'disabled=\{isActionLoading\}'
if ($trackDetailPatched -notmatch $buttonDisabledPattern) {
    throw 'Lesson action button disabled anchor not found; no write performed.'
}
$disabledReplacement = @'
disabled={isActionLoading || !hasCurriculumAccess}
                                          title={
                                            !hasCurriculumAccess
                                              ? "يرجى الدفع وتفعيل الحساب للوصول لهذا الدرس"
                                              : undefined
                                          }
'@
$disabledReplacement = $disabledReplacement -replace "`n", "`r`n"
$trackDetailPatched = $trackDetailPatched.Replace(
    'disabled={isActionLoading}',
    $disabledReplacement.TrimEnd()
)

# Video is a learning asset; keep only the syllabus title visible while locked.
$videoPattern = '\{lesson\.video_url && \('
if ($trackDetailPatched -notmatch $videoPattern) {
    throw 'Lesson video anchor not found; no write performed.'
}
$trackDetailPatched = $trackDetailPatched.Replace(
    '{lesson.video_url && (',
    '{hasCurriculumAccess && lesson.video_url && ('
)

# Format the track description as paragraphs without adding a markdown dependency.
$descriptionPattern = '(?ms)<p className="mt-4 text-sm leading-7 text-gray-600 md:text-base">\s*\{track\.description \|\|\s*"Explore the complete curriculum for this learning track\."\s*\}\s*</p>'
$descriptionReplacement = @'
<div className="mt-4 space-y-3 text-sm leading-7 text-gray-600 md:text-base">
                  {(track.description || "Explore the complete curriculum for this learning track.")
                    .split(/\r?\n\r?\n/)
                    .filter((paragraph) => paragraph.trim())
                    .map((paragraph, index) => (
                      <p key={`${track.id}-description-${index}`}>{paragraph.trim()}</p>
                    ))}
                </div>
'@
$descriptionReplacement = $descriptionReplacement -replace "`n", "`r`n"
if ($trackDetailPatched -match $descriptionPattern) {
    $trackDetailPatched = [regex]::Replace($trackDetailPatched, $descriptionPattern, $descriptionReplacement, 1)
}

# Hide protected assignments while keeping the syllabus itself visible.
$assignmentBlockPattern = '(?ms)\s*<AssignmentList\s+assignments=\{assignmentsByModule\.get\(module\.id\) \?\? \[\]\}\s+lessons=\{module\.lessons\}\s+isLoading=\{isAssignmentsLoading\}\s+error=\{assignmentsError\}\s*/>'
$assignmentReplacement = @'
                  {hasCurriculumAccess ? (
                    <AssignmentList
                      assignments={assignmentsByModule.get(module.id) ?? []}
                      lessons={module.lessons}
                      isLoading={isAssignmentsLoading}
                      error={assignmentsError}
                    />
                  ) : (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                      Assignments unlock after payment and enrollment activation.
                    </div>
                  )}
'@
$assignmentReplacement = $assignmentReplacement -replace "`n", "`r`n"
if ($trackDetailPatched -notmatch $assignmentBlockPattern) {
    throw 'AssignmentList block anchor not found; no write performed.'
}
$trackDetailPatched = [regex]::Replace($trackDetailPatched, $assignmentBlockPattern, $assignmentReplacement, 1)

# Add an explicit payment gateway below the syllabus for premium locked users.
$paymentSectionPattern = '(?ms)(        </section>\r?\n      </div>\r?\n    </div>\r?\n  \);\r?\n\})$'
$paymentSection = @'
        </section>

        {!isEnrollmentLoading && track.is_premium && !hasCurriculumAccess ? (
          <section id="payment-gateway" className="scroll-mt-24 rounded-2xl border border-blue-200 bg-white shadow-sm">
            <div className="border-b border-blue-100 bg-blue-50/60 px-6 py-5 md:px-8">
              <p className="text-sm font-semibold uppercase tracking-[0.12em] text-blue-700">
                Secure your access
              </p>
              <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
                Unlock the full curriculum
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                You can preview the full syllabus above. Submit your payment receipt below to unlock lesson content, videos, assignments, and resources after approval.
              </p>
            </div>
            <div className="p-6 md:p-8">
              <PaymentCheckout
                track={track}
                enrollment={currentEnrollment}
              />
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
'@
$paymentSection = $paymentSection -replace "`n", "`r`n"
if ($trackDetailPatched -notmatch $paymentSectionPattern) {
    throw 'TrackDetail final layout anchor not found; no write performed.'
}
$trackDetailPatched = [regex]::Replace($trackDetailPatched, $paymentSectionPattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $paymentSection }, 1)

# -----------------------------------------------------------------------------
# TEST PATCH: assert syllabus remains visible but lesson payload is locked.
# -----------------------------------------------------------------------------
$lockedTestPattern = '(?ms)(        locked_data = locked_curriculum\.json\(\)\r?\n        assert locked_data\["id"\] == track_id\r?\n        assert locked_data\["modules"\] == \[\]\r?\n)'
$lockedTestReplacement = @'
        locked_data = locked_curriculum.json()
        assert locked_data["id"] == track_id
        assert len(locked_data["modules"]) == 1
        assert locked_data["modules"][0]["title"] == "FastAPI"
        assert locked_data["modules"][0]["lessons"][0]["title"] == "Dependencies"
        assert locked_data["modules"][0]["lessons"][0]["content"] == "PLACEHOLDER_LOCKED_CONTENT"
'@
$lockedTestReplacement = $lockedTestReplacement.Replace('PLACEHOLDER_LOCKED_CONTENT', $lockedMessage)
$lockedTestReplacement = $lockedTestReplacement -replace "`n", "`r`n"
if ($testText -notmatch $lockedTestPattern) {
    throw 'Locked curriculum test contract anchor not found; no write performed.'
}
$testPatched = [regex]::Replace($testText, $lockedTestPattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $lockedTestReplacement }, 1)

$adminContentPattern = '(?ms)(        assert data\["id"\] == track_id\r?\n        assert len\(data\["modules"\]\) == 1\r?\n        assert len\(data\["modules"\]\[0\]\["lessons"\]\) == 1\r?\n        assert len\(data\["modules"\]\[0\]\["resources"\]\) == 1\r?\n)'
$adminContentReplacement = @'
        assert data["id"] == track_id
        assert len(data["modules"]) == 1
        assert len(data["modules"][0]["lessons"]) == 1
        assert data["modules"][0]["lessons"][0]["content"] == "Dependency injection"
        assert len(data["modules"][0]["resources"]) == 1
'@
$adminContentReplacement = $adminContentReplacement -replace "`n", "`r`n"
if ($testPatched -notmatch $adminContentPattern) {
    throw 'Admin curriculum test contract anchor not found; no write performed.'
}
$testPatched = [regex]::Replace($testPatched, $adminContentPattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $adminContentReplacement }, 1)

# -----------------------------------------------------------------------------
# PRE-WRITE STATIC ASSERTIONS
# -----------------------------------------------------------------------------
Require-Text $tracksPatched 'TrackCurriculum.model_validate(' 'full curriculum response projection'
Require-Text $tracksPatched 'lesson.model_copy(' 'lesson content masking'
Require-Text $tracksPatched $lockedMessage 'exact locked lesson message'
if ($tracksPatched -match [regex]::Escape('track.modules = []')) {
    throw 'Unsafe track.modules mutation still present in candidate backend source; no write performed.'
}

Require-Text $trackDetailPatched 'const hasCurriculumAccess = currentEnrollment?.status === "active";' 'active access guard'
Require-Text $trackDetailPatched 'track.modules.map((module, moduleIndex) =>' 'syllabus remains rendered'
Require-Text $trackDetailPatched 'module.lessons.map((lesson, lessonIndex) =>' 'lesson syllabus remains rendered'
Require-Text $trackDetailPatched '<PaymentCheckout' 'payment checkout in main learning page'
Require-Text $trackDetailPatched 'id="payment-gateway"' 'visible payment gateway section'
Require-Text $trackDetailPatched 'disabled={isActionLoading || !hasCurriculumAccess}' 'click lock on lesson action'
Require-Text $trackDetailPatched 'title={' 'locked lesson tooltip'
Require-Text $trackDetailPatched 'hasCurriculumAccess && lesson.video_url' 'video content lock'
Require-Text $trackDetailPatched 'Assignments unlock after payment and enrollment activation.' 'assignment lock notice'

# -----------------------------------------------------------------------------
# WRITE
# -----------------------------------------------------------------------------
Write-Host ''
Write-Host '===== WRITING TASK-SYLLABUS-PREVIEW CHANGES ====='
Write-Utf8NoBom $TracksPath $tracksPatched
Write-Utf8NoBom $TrackDetailPath $trackDetailPatched
Write-Utf8NoBom $TestPath $testPatched
Write-Host 'Patched: backend/app/api/v1/tracks.py'
Write-Host 'Patched: frontend/src/pages/TrackDetail.tsx'
Write-Host 'Patched: backend/tests/integration/test_api_tracks_enrollments.py'
Write-Host 'No git commands executed. No commit created.'

# -----------------------------------------------------------------------------
# POST-WRITE ASSERTIONS
# -----------------------------------------------------------------------------
$tracksVerify = Read-Utf8 $TracksPath
$trackDetailVerify = Read-Utf8 $TrackDetailPath
$testVerify = Read-Utf8 $TestPath
Require-Text $tracksVerify 'TrackCurriculum.model_validate(' 'post-write full curriculum projection'
Require-Text $tracksVerify $lockedMessage 'post-write locked lesson message'
if ($tracksVerify -match [regex]::Escape('track.modules = []')) {
    throw 'Unsafe ORM mutation remains after write.'
}
Require-Text $trackDetailVerify 'track.modules.map((module, moduleIndex) =>' 'post-write syllabus modules'
Require-Text $trackDetailVerify 'module.lessons.map((lesson, lessonIndex) =>' 'post-write syllabus lessons'
Require-Text $trackDetailVerify 'id="payment-gateway"' 'post-write payment gateway'
if ($trackDetailVerify -match [regex]::Escape('if (track && !isEnrollmentLoading && !hasCurriculumAccess)')) {
    throw 'Legacy early sales return still exists; syllabus would remain hidden for locked users.'
}
Require-Text $trackDetailVerify 'disabled={isActionLoading || !hasCurriculumAccess}' 'post-write click lock'
Require-Text $testVerify $lockedMessage 'post-write lock coverage test'
Write-Host 'Static security assertions: PASS'

# -----------------------------------------------------------------------------
# VERIFICATION
# -----------------------------------------------------------------------------
$env:DATABASE_URL = 'postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_db'
$env:ADMIN_DATABASE_URL = 'postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/postgres'
$env:TEST_DATABASE_URL = 'postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_test_db'

Push-Location $BackendRoot
try {
    Write-Host ''
    Write-Host '===== ALEMBIC CURRENT (backend) ====='
    python -m alembic current
    if ($LASTEXITCODE -ne 0) { throw 'Alembic current failed.' }

    Write-Host '===== RUFF CHECK (backend) ====='
    python -m ruff check app
    if ($LASTEXITCODE -ne 0) { throw 'Ruff check failed.' }

    Write-Host '===== TARGETED SYLLABUS PYTEST ====='
    python -m pytest -q tests/integration/test_api_tracks_enrollments.py -k test_track_curriculum_endpoints_and_rbac
    if ($LASTEXITCODE -ne 0) { throw 'Targeted syllabus pytest failed.' }

    Write-Host '===== FULL PYTEST (backend) ====='
    python -m pytest -ra -q
    if ($LASTEXITCODE -ne 0) { throw 'Full pytest failed.' }
}
finally {
    Pop-Location
}

Push-Location $FrontendRoot
try {
    Write-Host ''
    Write-Host '===== TYPESCRIPT ====='
    npx.cmd tsc --noEmit
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript check failed.' }

    Write-Host '===== OXLINT ====='
    npx.cmd oxlint
    if ($LASTEXITCODE -ne 0) { throw 'oxlint failed.' }

    Write-Host '===== PRODUCTION BUILD ====='
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Production build failed.' }
}
finally {
    Pop-Location
}

Write-Host ''
Write-Host '===== TASK-SYLLABUS-PREVIEW v1 VERIFICATION PASSED ====='
Write-Host 'Syllabus preview + content lock + payment gateway contract passed.'
Write-Host 'No git commands executed. No commit created.'
