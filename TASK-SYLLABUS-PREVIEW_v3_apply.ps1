param(
    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$tracksPath = Join-Path $RepoRoot "backend\app\api\v1\tracks.py"
$testPath = Join-Path $RepoRoot "backend\tests\integration\test_api_tracks_enrollments.py"
$trackDetailPath = Join-Path $RepoRoot "frontend\src\pages\TrackDetail.tsx"

Write-Host "===== TASK-SYLLABUS-PREVIEW v3 ====="
Write-Host "Repository: $RepoRoot"

foreach ($path in @($tracksPath, $testPath, $trackDetailPath)) {
    if (-not (Test-Path $path)) {
        throw "Missing required file: $path"
    }
}

function Require-Text {
    param(
        [string]$Text,
        [string]$Needle,
        [string]$Label
    )
    if (-not $Text.Contains($Needle)) {
        throw "Missing required source contract: $Label"
    }
}

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Text
    )
    [System.IO.File]::WriteAllText(
        $Path,
        $Text,
        (New-Object System.Text.UTF8Encoding($false))
    )
}

function From-CodePoints {
    param([int[]]$CodePoints)
    return -join ($CodePoints | ForEach-Object { [char]$_ })
}

$lockedContent = From-CodePoints @(
    0x0647,0x0630,0x0627,0x0020,
    0x0627,0x0644,0x0645,0x062d,0x062a,0x0648,0x0649,
    0x0020,
    0x0645,0x0642,0x0641,0x0644,0x002e,
    0x0020,
    0x064a,0x0631,0x062c,0x0649,
    0x0020,
    0x0627,0x0644,0x0627,0x0634,0x062a,0x0631,0x0627,0x0643,
    0x0020,
    0x0641,0x064a,
    0x0020,
    0x0627,0x0644,0x0645,0x0633,0x0627,0x0631,
    0x0020,
    0x0644,0x062a,0x062a,0x0645,0x0643,0x0646,
    0x0020,
    0x0645,0x0646,
    0x0020,
    0x0639,0x0631,0x0636,
    0x0020,
    0x062a,0x0641,0x0627,0x0635,0x064a,0x0644,
    0x0020,
    0x0627,0x0644,0x062f,0x0631,0x0633,
    0x002e
)

$lockAlert = From-CodePoints @(
    0x064a,0x0631,0x062c,0x0649,0x0020,
    0x0627,0x0644,0x062f,0x0641,0x0639,
    0x0020,
    0x0648,0x062a,0x0641,0x0639,0x064a,0x0644,
    0x0020,
    0x0627,0x0644,0x062d,0x0633,0x0627,0x0628,
    0x0020,
    0x0644,0x0644,0x0648,0x0635,0x0648,0x0644,
    0x0020,
    0x0625,0x0644,0x0649,
    0x0020,
    0x0647,0x0630,0x0627,
    0x0020,
    0x0627,0x0644,0x062f,0x0631,0x0633
)

Write-Host "===== AUDIT CURRENT CONTRACTS ====="

$tracks = Get-Content -Raw -Encoding UTF8 $tracksPath
$test = Get-Content -Raw -Encoding UTF8 $testPath
$trackDetail = Get-Content -Raw -Encoding UTF8 $trackDetailPath

Require-Text $tracks 'TrackCurriculum.model_validate(track, from_attributes=True)' 'current TrackCurriculum projection'
Require-Text $tracks 'track_payload = track_payload.model_copy(update={"modules": []})' 'existing locked-curriculum projection'
Require-Text $tracks 'Enrollment.user_id == current_user.id' 'current enrollment lookup'
Require-Text $tracks 'current_user.is_superuser' 'superuser bypass'
Require-Text $trackDetail 'const hasCurriculumAccess = currentEnrollment?.status === "active";' 'strict active curriculum access'
Require-Text $trackDetail '<QuizList' 'quiz component'
Require-Text $trackDetail '<AssignmentList' 'assignment component'
Require-Text $trackDetail 'module.resources.map' 'resource rendering'
Require-Text $test 'locked_data["modules"] == []' 'old locked-module test contract'

Write-Host "AUDIT PASS"

Write-Host "===== PATCH BACKEND: SYLLABUS PREVIEW + MASKED CONTENT ====="

$oldGuard = @'
    track_payload = TrackCurriculum.model_validate(track, from_attributes=True)
    if not current_user.is_superuser and (
        enrollment is None or enrollment.status != "active"
    ):
        track_payload = track_payload.model_copy(update={"modules": []})

    return track_payload
'@

$newGuard = @"
    track_payload = TrackCurriculum.model_validate(track, from_attributes=True)
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
                                    update={"content": "$lockedContent"}
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

if (-not $tracks.Contains($oldGuard.Trim())) {
    throw "Current backend curriculum projection does not match the audited source; refusing blind replacement."
}

$tracks = $tracks.Replace($oldGuard.Trim(), $newGuard.Trim())

Write-Host "===== PATCH FRONTEND: ALWAYS SHOW SYLLABUS ====="

# Remove the old sales-page early return inserted by the prior paywall implementation.
$salesGuardPattern = '(?ms)\r?\n  if \(track && !isEnrollmentLoading && !hasCurriculumAccess\) \{\r?\n.*?\r?\n  \}\r?\n\r?\n(?=  return \()'
$patchedTrackDetail = [regex]::Replace(
    $trackDetail,
    $salesGuardPattern,
    "`r`n",
    1
)

if ($patchedTrackDetail -eq $trackDetail) {
    throw "TrackDetail sales-page early-return guard was not found."
}
$trackDetail = $patchedTrackDetail

# Ensure PaymentCheckout import exists.
if (-not $trackDetail.Contains('import PaymentCheckout from "@/components/PaymentCheckout";')) {
    Require-Text $trackDetail 'import EnrollmentPanel from "@/components/EnrollmentPanel";' 'EnrollmentPanel import anchor'
    $trackDetail = $trackDetail.Replace(
        'import EnrollmentPanel from "@/components/EnrollmentPanel";',
        'import EnrollmentPanel from "@/components/EnrollmentPanel";' + "`r`n" +
        'import PaymentCheckout from "@/components/PaymentCheckout";'
    )
}

# Hero description: preserve paragraph/newline formatting.
$heroParagraph = '<p className="mt-4 text-sm leading-7 text-gray-600 md:text-base">'
if ($trackDetail.Contains($heroParagraph) -and -not $trackDetail.Contains('className="mt-4 whitespace-pre-wrap text-sm leading-7 text-gray-600 md:text-base"')) {
    $trackDetail = $trackDetail.Replace(
        $heroParagraph,
        '<p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-gray-600 md:text-base">'
    )
}

# Quiz content is locked until active enrollment.
$quizLine = '{trackId ? <QuizList trackId={Number(trackId)} /> : null}'
if ($trackDetail.Contains($quizLine)) {
    $trackDetail = $trackDetail.Replace(
        $quizLine,
        '{hasCurriculumAccess && trackId ? <QuizList trackId={Number(trackId)} /> : null}'
    )
}

# Assignment content is locked; the module and lesson syllabus stays visible.
$assignmentBlock = @'
                  <AssignmentList
                    assignments={assignmentsByModule.get(module.id) ?? []}
                    lessons={module.lessons}
                    isLoading={isAssignmentsLoading}
                    error={assignmentsError}
                  />
'@
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
                      Content assignments unlock after payment and activation.
                    </div>
                  )}
'@
if ($trackDetail.Contains($assignmentBlock.Trim())) {
    $trackDetail = $trackDetail.Replace(
        $assignmentBlock.Trim(),
        $assignmentReplacement.Trim()
    )
} else {
    throw "AssignmentList block was not found in the current TrackDetail source."
}

# Video content is part of the locked lesson payload.
$trackDetail = $trackDetail.Replace(
    '{lesson.video_url && (',
    '{hasCurriculumAccess && lesson.video_url && ('
)

# Lesson action: disable and alert for locked lessons.
$oldButtonDisabled = 'disabled={isActionLoading}'
if ($trackDetail.Contains($oldButtonDisabled)) {
    $trackDetail = $trackDetail.Replace(
        $oldButtonDisabled,
        'disabled={isActionLoading || !hasCurriculumAccess}'
    )
}

$oldOnClick = @'
                                          onClick={() =>
                                            void handleProgressAction(
                                              lesson.id,
                                            )
                                          }
'@
$newOnClick = @"
                                          onClick={() => {
                                            if (!hasCurriculumAccess) {
                                              window.alert("$lockAlert");
                                              return;
                                            }
                                            void handleProgressAction(lesson.id);
                                          }}
"@
if ($trackDetail.Contains($oldOnClick.Trim())) {
    $trackDetail = $trackDetail.Replace(
        $oldOnClick.Trim(),
        $newOnClick.Trim()
    )
} else {
    throw "Lesson progress onClick block was not found."
}

# Resources remain part of the syllabus preview but files are hidden until activation.
$resourceGridStart = '<div className="grid grid-cols-1 gap-3 md:grid-cols-2">'
$resourceStart = $trackDetail.IndexOf($resourceGridStart)
if ($resourceStart -ge 0) {
    $resourceEndMarker = '                      </div>'
    $resourceEnd = $trackDetail.IndexOf($resourceEndMarker, $resourceStart)
    if ($resourceEnd -lt 0) {
        throw "Resource grid end marker not found."
    }
    $resourceEnd += $resourceEndMarker.Length
    $resourceGrid = $trackDetail.Substring($resourceStart, $resourceEnd - $resourceStart)
    if ($resourceGrid.Contains('resource.file_url')) {
        $lockedResourceGrid = @'
                      {hasCurriculumAccess ? (
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                          {module.resources.map((resource) => (
                            <a
                              key={resource.id}
                              href={resource.file_url}
                              target="_blank"
                              rel="noreferrer"
                              className="group rounded-xl border border-gray-200 bg-white p-4 transition-all hover:border-emerald-200 hover:bg-emerald-50/30"
                            >
                              <div className="flex items-start gap-3">
                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                                  <FileText className="h-4 w-4" />
                                </div>
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-start justify-between gap-3">
                                    <div>
                                      <p className="font-medium text-slate-900 group-hover:text-emerald-700">
                                        {resource.title}
                                      </p>
                                      <p className="mt-1 text-xs uppercase tracking-wide text-gray-400">
                                        {resource.resource_type}
                                      </p>
                                    </div>
                                    <ExternalLink className="h-4 w-4 shrink-0 text-gray-400 group-hover:text-emerald-600" />
                                  </div>
                                </div>
                              </div>
                            </a>
                          ))}
                        </div>
                      ) : (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                          Resource files unlock after payment and activation.
                        </div>
                      )}
'@
        $trackDetail = $trackDetail.Remove($resourceStart, $resourceEnd - $resourceStart).Insert($resourceStart, $lockedResourceGrid.TrimEnd())
    }
}

# Add a prominent payment CTA below the syllabus for premium tracks without active access.
$finalMarker = @'
        </section>
      </div>
    </div>
  );
}
'@
if (-not $trackDetail.Contains($finalMarker.Trim())) {
    throw "TrackDetail final render marker not found."
}

$paymentSection = @'
        {!isEnrollmentLoading &&
          track.is_premium &&
          !hasCurriculumAccess && (
            <section id="payment-gateway" className="scroll-mt-24">
              <Card className="border-blue-200 bg-gradient-to-br from-blue-50 via-white to-white shadow-sm">
                <CardHeader>
                  <CardTitle className="text-2xl text-slate-900">
                    Unlock the full learning experience
                  </CardTitle>
                  <CardDescription className="max-w-2xl leading-6">
                    Review the syllabus above, then submit your payment receipt to unlock full lesson content, quizzes, assignments, and resources.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <PaymentCheckout
                    track={track}
                    enrollment={currentEnrollment}
                  />
                </CardContent>
              </Card>
            </section>
          )}
'@
$trackDetail = $trackDetail.Replace(
    $finalMarker.Trim(),
    ("        </section>`r`n" + $paymentSection.TrimEnd() + "`r`n      </div>`r`n    </div>`r`n  );`r`n}")
)

Write-Host "===== PATCH TEST CONTRACT ====="

$oldTest = @'
    assert locked_data["id"] == track_id
    assert locked_data["modules"] == []

    curriculum = client.get(
'@
$newTest = @"
    assert locked_data["id"] == track_id
    assert len(locked_data["modules"]) == 1
    assert locked_data["modules"][0]["title"] == "FastAPI"
    assert len(locked_data["modules"][0]["lessons"]) == 1
    assert locked_data["modules"][0]["lessons"][0]["title"] == "Dependencies"
    assert locked_data["modules"][0]["lessons"][0]["content"] == "$lockedContent"

    curriculum = client.get(
"@
if ($test.Contains($oldTest.Trim())) {
    $test = $test.Replace($oldTest.Trim(), $newTest.Trim())
} else {
    throw "Existing locked curriculum assertions were not found in the test."
}

Write-Host "===== POST-PATCH STATIC ASSERTIONS ====="

if ($tracks -match [regex]::Escape('track.modules = []')) {
    throw "Unsafe ORM module mutation remains in tracks.py."
}
Require-Text $tracks 'lesson.model_copy(' 'lesson masking'
Require-Text $tracks $lockedContent 'masked lesson content'
Require-Text $tracks 'return track_payload' 'projected curriculum response'

if ($trackDetail.Contains('track && !isEnrollmentLoading && !hasCurriculumAccess')) {
    throw "Old sales-page early return still blocks the syllabus."
}
Require-Text $trackDetail 'const hasCurriculumAccess = currentEnrollment?.status === "active";' 'strict active guard'
Require-Text $trackDetail 'track.modules.map' 'syllabus rendering'
Require-Text $trackDetail '<PaymentCheckout' 'payment checkout'
Require-Text $trackDetail 'id="payment-gateway"' 'visible payment gateway section'
Require-Text $trackDetail '!hasCurriculumAccess' 'content lock guard'
Require-Text $trackDetail 'window.alert' 'lesson click lock'
Require-Text $trackDetail $lockAlert 'Arabic lesson lock message'

Require-Text $test 'locked_data["modules"][0]["title"] == "FastAPI"' 'module preview assertion'
Require-Text $test 'locked_data["modules"][0]["lessons"][0]["title"] == "Dependencies"' 'lesson title preview assertion'
Require-Text $test $lockedContent 'masked content assertion'

Write-Utf8NoBom $tracksPath $tracks
Write-Utf8NoBom $testPath $test
Write-Utf8NoBom $trackDetailPath $trackDetail

Write-Host "Patched: backend/app/api/v1/tracks.py"
Write-Host "Patched: backend/tests/integration/test_api_tracks_enrollments.py"
Write-Host "Patched: frontend/src/pages/TrackDetail.tsx"
Write-Host "No git commands executed. No commit created."

$env:DATABASE_URL = "postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_db"
$env:ADMIN_DATABASE_URL = "postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/postgres"
$env:TEST_DATABASE_URL = "postgresql://kodraq_user:kodraq_secure_password@127.0.0.1:5433/kodraq_test_db"

$backendRoot = Join-Path $RepoRoot "backend"
$frontendRoot = Join-Path $RepoRoot "frontend"

Push-Location $backendRoot
try {
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
    if ($LASTEXITCODE -ne 0) { throw "Pytest failed." }
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
    if ($LASTEXITCODE -ne 0) { throw "oxlint failed." }

    Write-Host "===== PRODUCTION BUILD ====="
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Production build failed." }
}
finally {
    Pop-Location
}

Write-Host "===== TASK-SYLLABUS-PREVIEW v3 VERIFICATION PASSED ====="
Write-Host "Syllabus is public, lesson payload is masked for unauthorized users, and premium payment CTA is visible below the syllabus."
Write-Host "No git commands executed. No commit created."
