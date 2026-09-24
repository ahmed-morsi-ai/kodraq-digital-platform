$ErrorActionPreference = "Stop"

Write-Host "TASK-API-PREFIX-FIX v2 starting..." -ForegroundColor Cyan

$serviceFiles = @(
    ".\frontend\src\services\track.service.ts",
    ".\frontend\src\services\enrollment.service.ts",
    ".\frontend\src\services\certificate.service.ts",
    ".\frontend\src\services\payment.service.ts",
    ".\frontend\src\services\assignment.service.ts",
    ".\frontend\src\services\quiz.service.ts",
    ".\frontend\src\services\finalProject.service.ts"
)

$prefixMap = [ordered]@{
    "/api/v1/tracks"          = "/tracks"
    "/api/v1/enrollments"     = "/enrollments"
    "/api/v1/certificates"    = "/certificates"
    "/api/v1/payments"        = "/payments"
    "/api/v1/assignments"     = "/assignments"
    "/api/v1/quizzes"         = "/quizzes"
    "/api/v1/quiz-attempts"   = "/quiz-attempts"
    "/api/v1/final-projects"  = "/final-projects"
    "/api/v1/graduation"      = "/graduation"
}

foreach ($file in $serviceFiles) {
    if (-not (Test-Path $file)) {
        throw "Service file not found: $file"
    }

    $text = Get-Content $file -Raw

    # Normalize already-prefixed routes first, then add exactly one /api/v1 prefix.
    foreach ($entry in $prefixMap.GetEnumerator()) {
        $prefixed = $entry.Key
        $root = $entry.Value
        $text = $text.Replace($prefixed, $root)
        $text = $text.Replace("`"$root", "`"$prefixed")
        $text = $text.Replace("`$root", "`$prefixed")
        $text = $text.Replace("`/$root", "`/$prefixed")
    }

    # The replacements above handle quoted strings. These explicit replacements cover
    # template literals used by the services and keep the operation idempotent.
    $templateRoutes = @(
        @("/tracks", "/api/v1/tracks"),
        @("/enrollments", "/api/v1/enrollments"),
        @("/certificates", "/api/v1/certificates"),
        @("/payments", "/api/v1/payments"),
        @("/assignments", "/api/v1/assignments"),
        @("/quizzes", "/api/v1/quizzes"),
        @("/quiz-attempts", "/api/v1/quiz-attempts"),
        @("/final-projects", "/api/v1/final-projects"),
        @("/graduation", "/api/v1/graduation")
    )

    foreach ($pair in $templateRoutes) {
        $root = $pair[0]
        $prefixed = $pair[1]
        $text = [regex]::Replace(
            $text,
            "(?<!/api/v1)$([regex]::Escape($root))",
            $prefixed
        )
    }

    [System.IO.File]::WriteAllText(
        (Resolve-Path $file),
        $text,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "Updated: $file" -ForegroundColor Green
}

Write-Host ""
Write-Host "===== FINAL SERVICE ROUTE CHECK =====" -ForegroundColor Cyan

$unprefixedPatterns = @(
    'api\.get<.*>\("/tracks',
    'api\.post<.*>\("/tracks',
    'api\.patch<.*>\("/tracks',
    'api\.get<.*>\(`?/tracks',
    'api\.post<.*>\(`?/tracks',
    'api\.patch<.*>\(`?/tracks',
    'api\.get<.*>\("/enrollments',
    'api\.post<.*>\("/enrollments',
    'api\.patch<.*>\("/enrollments',
    'api\.get<.*>\(`?/enrollments',
    'api\.post<.*>\(`?/enrollments',
    'api\.patch<.*>\(`?/enrollments',
    'api\.get<.*>\("/certificates',
    'api\.post<.*>\("/certificates',
    'api\.get<.*>\(`?/certificates',
    'api\.get<.*>\("/payments',
    'api\.post<.*>\("/payments',
    'api\.patch<.*>\("/payments',
    'api\.get<.*>\("/assignments',
    'api\.get<.*>\("/quizzes',
    'api\.post<.*>\(`?/quizzes',
    'api\.get<.*>\(`?/quizzes',
    'api\.post<.*>\(`?/quiz-attempts',
    'api\.get<.*>\(`?/quiz-attempts',
    'api\.post<.*>\(`?/final-projects',
    'api\.get<.*>\(`?/final-projects',
    'api\.patch<.*>\(`?/final-projects',
    'api\.post<.*>\("/graduation'
)

$remaining = foreach ($file in $serviceFiles) {
    foreach ($pattern in $unprefixedPatterns) {
        Select-String -Path $file -Pattern $pattern
    }
}

if ($remaining) {
    $remaining | ForEach-Object { $_ }
    throw "Unprefixed backend routes remain. Fix was not applied completely."
}

Write-Host ""
Write-Host "All audited frontend service routes now use /api/v1." -ForegroundColor Green
Write-Host "No git commands executed." -ForegroundColor DarkGray
