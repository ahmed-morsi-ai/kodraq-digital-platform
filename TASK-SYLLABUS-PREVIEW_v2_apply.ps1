param(
    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$backendRoot = Join-Path $RepoRoot "backend"
$frontendRoot = Join-Path $RepoRoot "frontend"

$tracksPath = Join-Path $RepoRoot "backend\app\api\v1\tracks.py"
$trackDetailPath = Join-Path $RepoRoot "frontend\src\pages\TrackDetail.tsx"
$testPath = Join-Path $RepoRoot "backend\tests\integration\test_api_tracks_enrollments.py"

$lockedContent = "هذا المحتوى مقفل. يرجى الاشتراك في المسار لتتمكن من عرض تفاصيل الدرس."
$lockPrompt = "يرجى الدفع وتفعيل الحساب للوصول لهذا الدرس"
$paymentTitle = "Unlock the full learning experience"

function Read-Utf8([string]$Path) {
    return Get-Content -Raw -Encoding UTF8 $Path
}

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    [System.IO.File]::WriteAllText(
        $Path,
        $Text,
        (New-Object System.Text.UTF8Encoding($false))
    )
}

function Require-Text([string]$Text, [string]$Needle, [string]$Label) {
    if ($Text.IndexOf($Needle, [System.StringComparison]::Ordinal) -lt 0) {
        throw "Missing required source contract: $Label"
    }
}

Write-Host "===== TASK-SYLLABUS-PREVIEW v2 AUDIT ====="
Write-Host "Repository: $RepoRoot"

foreach ($path in @($tracksPath, $trackDetailPath, $testPath)) {
    if (-not (Test-Path $path)) {
        throw "Required file missing: $path"
    }
}
Write-Host "AUDIT PASS: required backend, frontend, and test files exist."

$tracks = Read-Utf8 $tracksPath
$trackDetail = Read-Utf8 $trackDetailPath
$testText = Read-Utf8 $testPath

Write-Host "===== AUDIT BACKEND PREVIEW CONTRACT ====="
Require-Text $tracks 'def read_track_curriculum(' 'curriculum route'
Require-Text $tracks 'current_user: CurrentUserDep' 'authenticated curriculum route'
Require-Text $tracks 'Enrollment.user_id == current_user.id' 'current-user enrollment lookup'
Require-Text $tracks 'TrackCurriculum.model_validate(track, from_attributes=True)' 'safe curriculum response projection'
Require-Text $tracks 'track_payload = track_payload.model_copy(update={"modules": []})' 'existing locked-curriculum projection'

Write-Host "===== AUDIT FRONTEND CURRENT CONTRACT ====="
Require-Text $trackDetail 'const hasCurriculumAccess = currentEnrollment?.status === "active";' 'strict active access guard'
Require-Text $trackDetail '<PaymentCheckout' 'existing payment checkout'
Require-Text $trackDetail 'track.description' 'hero description'
Require-Text $trackDetail 'track.modules.map' 'syllabus renderer'
Require-Text $trackDetail 'module.lessons.map' 'lesson syllabus renderer'

Write-Host "===== PATCH BACKEND: SYLLABUS PREVIEW + CONTENT MASK ====="
$lockedProjection = @'
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
                                    update={
                                        "content": "هذا المحتوى مقفل. يرجى الاشتراك في المسار لتتمكن من عرض تفاصيل الدرس."
                                    }
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
'@

$unsafeProjection = @'
    if not current_user.is_superuser and (
        enrollment is None or enrollment.status != "active"
    ):
        track_payload = track_payload.model_copy(update={"modules": []})

    return track_payload
'@

if ($tracks.Contains($lockedProjection)) {
    Write-Host "Backend content-mask projection already present."
} elseif ($tracks.Contains($unsafeProjection)) {
    $tracks = $tracks.Replace($unsafeProjection, ($lockedProjection -replace "`n", "`r`n").TrimEnd())
    if ($tracks -match [regex]::Escape('track_payload = track_payload.model_copy(update={"modules": []})')) {
        throw "Backend locked curriculum projection was not fully replaced."
    }
    Write-Host "Patched: backend/app/api/v1/tracks.py"
} else {
    throw "Current curriculum projection does not match the audited v15 source contract; no write performed."
}

Write-Host "===== PATCH BACKEND TEST CONTRACT ====="
if ($testText.Contains('assert locked_data["modules"] == []')) {
    $old = @'
    assert locked_data["id"] == track_id
    assert locked_data["modules"] == []
'@
    $new = @'
    assert locked_data["id"] == track_id
    assert len(locked_data["modules"]) == 1
    assert locked_data["modules"][0]["title"] == "FastAPI"
    assert len(locked_data["modules"][0]["lessons"]) == 1
    assert locked_data["modules"][0]["lessons"][0]["title"] == "Dependencies"
    assert (
        locked_data["modules"][0]["lessons"][0]["content"]
        == "هذا المحتوى مقفل. يرجى الاشتراك في المسار لتتمكن من عرض تفاصيل الدرس."
    )
'@
    $oldCrLf = $old -replace "`n", "`r`n"
    $newCrLf = $new -replace "`n", "`r`n"
    if ($testText.Contains($oldCrLf)) {
        $testText = $testText.Replace($oldCrLf, $newCrLf)
    } elseif ($testText.Contains($old)) {
        $testText = $testText.Replace($old, $new)
    } else {
        throw "Locked curriculum assertion block not found in integration test."
    }
    Write-Host "Patched: backend/tests/integration/test_api_tracks_enrollments.py"
} else {
    Require-Text $testText 'locked_data["modules"][0]["lessons"][0]["content"]' 'syllabus preview test contract'
    Write-Host "Syllabus preview test contract already present."
}

Write-Host "===== PATCH FRONTEND: ALWAYS SHOW SYLLABUS, LOCK CONTENT ====="

# Remove only the old full sales-page early return. The normal page already contains
# the syllabus renderer and lesson/module outline.
$earlySalesPattern = '(?s)\r?\n  if \(track && !isEnrollmentLoading && !hasCurriculumAccess\) \{\r?\n.*?\r?\n  \}\r?\n\r?\n  return \('
if ($trackDetail -match $earlySalesPattern) {
    $trackDetail = [regex]::Replace(
        $trackDetail,
        $earlySalesPattern,
        "`r`n  return (",
        1
    )
    Write-Host "Removed locked-user early sales return so syllabus can render for everyone."
} else {
    Write-Host "No old early sales return found."
}

# Gate quizzes/enrollment controls while leaving syllabus visible.
$quizEnrollmentPattern = '(?s)\r?\n        \{!isEnrollmentLoading &&\r?\n          <>\r?\n            \{trackId \? <QuizList trackId=\{Number\(trackId\)\} /> : null\}\r?\n\r?\n            <EnrollmentPanel\r?\n              trackId=\{numericTrackId\}\r?\n              enrollment=\{currentEnrollment\}\r?\n              onEnrollmentCreated=\{handleEnrollmentCreated\}\}\r?\n            />\r?\n          </>\r?\n        \}'
$quizEnrollmentReplacement = @'
        {!isEnrollmentLoading && hasCurriculumAccess && (
          <>
            {trackId ? <QuizList trackId={Number(trackId)} /> : null}

            <EnrollmentPanel
              trackId={numericTrackId}
              enrollment={currentEnrollment}
              onEnrollmentCreated={handleEnrollmentCreated}
            />
          </>
        )}
'@ -replace "`n", "`r`n"
if ($trackDetail -match $quizEnrollmentPattern) {
    $trackDetail = [regex]::Replace($trackDetail, $quizEnrollmentPattern, "`r`n$quizEnrollmentReplacement", 1)
    Write-Host "Gated quizzes and learning enrollment controls behind active access."
} else {
    Write-Host "Quiz/enrollment control block already differs; continuing with safe lesson/content locks."
}

# Replace the current lesson-action visibility with active-access-only behavior.
$buttonAnchor = '{currentEnrollment && ('
if ($trackDetail.Contains($buttonAnchor)) {
    $trackDetail = $trackDetail.Replace(
        $buttonAnchor,
        '{currentEnrollment && hasCurriculumAccess && ('
    )
}

# Add lesson-level lock styling and click prompt to the lesson container.
$lessonContainerOld = @'
                            <div
                              key={lesson.id}
                              className={`rounded-xl border p-4 transition-colors ${
'@
$lessonContainerNew = @'
                            <div
                              key={lesson.id}
                              role={!hasCurriculumAccess ? "button" : undefined}
                              tabIndex={!hasCurriculumAccess ? 0 : undefined}
                              aria-disabled={!hasCurriculumAccess}
                              title={!hasCurriculumAccess ? "يرجى الدفع وتفعيل الحساب للوصول لهذا الدرس" : undefined}
                              onClick={
                                !hasCurriculumAccess
                                  ? () => window.alert("يرجى الدفع وتفعيل الحساب للوصول لهذا الدرس")
                                  : undefined
                              }
                              className={`rounded-xl border p-4 transition-colors ${
'@
$lessonOldCrLf = $lessonContainerOld -replace "`n", "`r`n"
$lessonNewCrLf = $lessonContainerNew -replace "`n", "`r`n"
if ($trackDetail.Contains($lessonOldCrLf)) {
    $trackDetail = $trackDetail.Replace($lessonOldCrLf, $lessonNewCrLf)
} elseif ($trackDetail.Contains($lessonContainerOld)) {
    $trackDetail = $trackDetail.Replace($lessonContainerOld, $lessonContainerNew)
}

# Lock video links.
$videoOld = '{lesson.video_url && ('
$videoNew = '{hasCurriculumAccess && lesson.video_url && ('
$trackDetail = $trackDetail.Replace($videoOld, $videoNew)

# Replace lesson content display with explicit locked copy on the frontend as defense in depth.
$contentOld = '{lesson.content ||'
$contentNew = '{
                                        hasCurriculumAccess
                                          ? (lesson.content ||'
if ($trackDetail.Contains($contentOld)) {
    $trackDetail = $trackDetail.Replace($contentOld, $contentNew, 1)
    $needleEnd = '"No lesson content available."}'
    $replacementEnd = '"No lesson content available.")'
    $idx = $trackDetail.IndexOf($replacementEnd)
    if ($idx -lt 0) {
        # Try the exact existing tail form and close the ternary there.
        $idx = $trackDetail.IndexOf($needleEnd)
        if ($idx -ge 0) {
            $trackDetail = $trackDetail.Remove($idx, $needleEnd.Length).Insert($idx, $needleEnd + "`r`n                                          : ""$lockPrompt""")
        }
    }
}

# The content replacement above is intentionally guarded; if its resulting JSX is not
# valid, the TypeScript gate below will catch it before completion.
# Hide assignment data for locked users.
$assignmentOld = @'
                  <AssignmentList
                    assignments={assignmentsByModule.get(module.id) ?? []}
                    lessons={module.lessons}
                    isLoading={isAssignmentsLoading}
                    error={assignmentsError}
                  />
'@
$assignmentNew = @'
                  {hasCurriculumAccess ? (
                    <AssignmentList
                      assignments={assignmentsByModule.get(module.id) ?? []}
                      lessons={module.lessons}
                      isLoading={isAssignmentsLoading}
                      error={assignmentsError}
                    />
                  ) : (
                    <div className="rounded-lg border border-dashed border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-800">
                      يرجى الدفع وتفعيل الحساب للوصول إلى الواجبات والتقييمات الخاصة بهذا المسار.
                    </div>
                  )}
'@
$assignmentOldCrLf = $assignmentOld -replace "`n", "`r`n"
$assignmentNewCrLf = $assignmentNew -replace "`n", "`r`n"
if ($trackDetail.Contains($assignmentOldCrLf)) {
    $trackDetail = $trackDetail.Replace($assignmentOldCrLf, $assignmentNewCrLf)
} elseif ($trackDetail.Contains($assignmentOld)) {
    $trackDetail = $trackDetail.Replace($assignmentOld, $assignmentNew)
}

# Hide resource links for locked users while retaining the resource section as a sales-safe outline.
$resourcesMapStart = $trackDetail.IndexOf('{module.resources.map((resource) => (')
if ($resourcesMapStart -ge 0) {
    # Replace only the map body conditionally using a narrow known anchor.
    $resourceLinkOld = @'
                        {module.resources.map((resource) => (
                          <a
                            key={resource.id}
                            href={resource.file_url}
'@
    $resourceLinkNew = @'
                        {hasCurriculumAccess ? (
                          module.resources.map((resource) => (
                            <a
                              key={resource.id}
                              href={resource.file_url}
'@
    $resourceOldCrLf = $resourceLinkOld -replace "`n", "`r`n"
    $resourceNewCrLf = $resourceLinkNew -replace "`n", "`r`n"
    if ($trackDetail.Contains($resourceOldCrLf)) {
        $trackDetail = $trackDetail.Replace($resourceOldCrLf, $resourceNewCrLf)
        $resourceCloseOld = @'
                            </div>
                          </a>
                        ))}
'@
        $resourceCloseNew = @'
                            </div>
                          </a>
                          ))
                        ) : (
                          <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-4 py-4 text-sm text-gray-600">
                            Resources are available after you pay and activate the track.
                          </div>
                        )}
'@
        $resourceCloseOldCrLf = $resourceCloseOld -replace "`n", "`r`n"
        $resourceCloseNewCrLf = $resourceCloseNew -replace "`n", "`r`n"
        if ($trackDetail.Contains($resourceCloseOldCrLf)) {
            $trackDetail = $trackDetail.Replace($resourceCloseOldCrLf, $resourceCloseNewCrLf)
        }
    }
}

# Add visible payment gateway after the syllabus section, immediately before the page closes.
$paymentAnchor = @'
        </section>
      </div>
    </div>
  );
}
'@
$paymentSection = @'
        </section>

        {!isEnrollmentLoading && !hasCurriculumAccess && (
          <section
            id="payment-gateway"
            className="rounded-2xl border border-blue-200 bg-blue-50/50 p-5 shadow-sm md:p-7"
          >
            <div className="mb-5">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
                Unlock the full learning experience
              </p>
              <h2 className="mt-2 text-2xl font-bold text-slate-900">
                Unlock {track.name}
              </h2>
              <p className="mt-2 text-sm leading-6 text-gray-600">
                {track.description ||
                  "Complete the payment and activation steps to access full lesson content, quizzes, assignments, and resources."}
              </p>
            </div>

            {track.is_premium ? (
              <div className="space-y-4">
                {!currentEnrollment ? (
                  <EnrollmentPanel
                    trackId={numericTrackId}
                    enrollment={currentEnrollment}
                    onEnrollmentCreated={handleEnrollmentCreated}
                  />
                ) : null}

                <PaymentCheckout
                  track={track}
                  enrollment={currentEnrollment}
                />
              </div>
            ) : (
              <EnrollmentPanel
                trackId={numericTrackId}
                enrollment={currentEnrollment}
                onEnrollmentCreated={handleEnrollmentCreated}
              />
            )}
          </section>
        )}
      </div>
    </div>
  );
}
'@
$paymentAnchorCrLf = $paymentAnchor -replace "`n", "`r`n"
$paymentSectionCrLf = $paymentSection -replace "`n", "`r`n"
if ($trackDetail.Contains($paymentAnchorCrLf)) {
    $trackDetail = $trackDetail.Replace($paymentAnchorCrLf, $paymentSectionCrLf)
} elseif ($trackDetail.Contains($paymentAnchor)) {
    $trackDetail = $trackDetail.Replace($paymentAnchor, $paymentSection)
} else {
    throw "Could not locate TrackDetail page closing anchor for payment gateway."
}

Write-Host "===== STATIC SECURITY ASSERTIONS ====="
Require-Text $tracks 'هذا المحتوى مقفل. يرجى الاشتراك في المسار لتتمكن من عرض تفاصيل الدرس.' 'backend locked lesson content'
if ($tracks -match [regex]::Escape('track_payload = track_payload.model_copy(update={"modules": []})')) {
    throw "Locked users are still receiving modules=[]; preview contract not applied."
}
Require-Text $tracks 'for module in track_payload.modules' 'all modules retained for preview'
Require-Text $trackDetail 'const hasCurriculumAccess = currentEnrollment?.status === "active";' 'frontend active access guard'
Require-Text $trackDetail 'track.modules.map' 'syllabus remains rendered'
Require-Text $trackDetail 'module.lessons.map' 'lesson syllabus remains rendered'
Require-Text $trackDetail 'window.alert("يرجى الدفع وتفعيل الحساب للوصول لهذا الدرس")' 'lesson click lock'
Require-Text $trackDetail 'id="payment-gateway"' 'visible payment gateway'
Require-Text $trackDetail 'PaymentCheckout' 'payment checkout'
if ($trackDetail -match '(?s)if \(track && !isEnrollmentLoading && !hasCurriculumAccess\)') {
    throw "Old locked-user early return still exists."
}
Write-Host "PASS"

Write-Host "===== WRITE ====="
Write-Utf8NoBom $tracksPath $tracks
Write-Utf8NoBom $trackDetailPath $trackDetail
Write-Utf8NoBom $testPath $testText
Write-Host "Patched: backend/app/api/v1/tracks.py"
Write-Host "Patched: frontend/src/pages/TrackDetail.tsx"
Write-Host "Patched: backend/tests/integration/test_api_tracks_enrollments.py"
Write-Host "No git commands executed. No commit created."

$env:DATABASE_URL = "postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_db"
$env:ADMIN_DATABASE_URL = "postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/postgres"
$env:TEST_DATABASE_URL = "postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_test_db"

Write-Host "===== POST-WRITE ASSERTIONS ====="
$tracksAfter = Read-Utf8 $tracksPath
$trackDetailAfter = Read-Utf8 $trackDetailPath
Require-Text $tracksAfter 'TrackCurriculum.model_validate(track, from_attributes=True)' 'projected response'
Require-Text $tracksAfter 'هذا المحتوى مقفل. يرجى الاشتراك في المسار لتتمكن من عرض تفاصيل الدرس.' 'masked content'
if ($tracksAfter -match [regex]::Escape('track_payload = track_payload.model_copy(update={"modules": []})')) {
    throw "POST-WRITE FAILURE: modules=[] still present."
}
Require-Text $trackDetailAfter 'track.modules.map' 'syllabus rendering'
Require-Text $trackDetailAfter 'module.lessons.map' 'lesson rendering'
Require-Text $trackDetailAfter 'id="payment-gateway"' 'payment gateway'
Require-Text $trackDetailAfter 'window.alert("يرجى الدفع وتفعيل الحساب للوصول لهذا الدرس")' 'click lock'
Write-Host "PASS"

Push-Location $backendRoot
try {
    Write-Host "===== ALEMBIC CURRENT ====="
    python -m alembic current
    if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }

    Write-Host "===== RUFF CHECK ====="
    python -m ruff check app
    if ($LASTEXITCODE -ne 0) { throw "Ruff check failed." }

    Write-Host "===== TARGETED PYTEST ====="
    python -m pytest tests/integration/test_api_tracks_enrollments.py -ra -q
    if ($LASTEXITCODE -ne 0) { throw "Targeted pytest failed." }

    Write-Host "===== FULL PYTEST ====="
    python -m pytest -ra -q
    if ($LASTEXITCODE -ne 0) { throw "Full pytest failed." }
}
finally {
    Pop-Location
}

Push-Location $frontendRoot
try {
    Write-Host "===== TYPESCRIPT ====="
    npx.cmd tsc --noEmit
    if ($LASTEXITCODE -ne 0) { throw "TypeScript check failed." }

    Write-Host "===== OXLINT ====="
    npx.cmd oxlint
    if ($LASTEXITCODE -ne 0) { throw "Oxlint failed." }

    Write-Host "===== PRODUCTION BUILD ====="
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Production build failed." }
}
finally {
    Pop-Location
}

Write-Host "===== TASK-SYLLABUS-PREVIEW v2 VERIFICATION PASSED =====" -ForegroundColor Green
Write-Host "Syllabus preview + content lock implementation and all requested verification gates passed."
Write-Host "No git commands executed. No commit created."
