$ErrorActionPreference = "Stop"

Write-Host "TASK-API-PREFIX-FIX starting..." -ForegroundColor Cyan

function Update-ServicePaths {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [hashtable]$Replacements
    )

    $resolved = Resolve-Path $Path
    $text = Get-Content $resolved -Raw
    $original = $text

    foreach ($key in $Replacements.Keys) {
        $text = $text.Replace($key, $Replacements[$key])
    }

    if ($text -eq $original) {
        Write-Host "No path changes needed: $Path" -ForegroundColor DarkYellow
        return
    }

    [System.IO.File]::WriteAllText(
        $resolved,
        $text,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "Updated: $Path" -ForegroundColor Green
}

$servicesRoot = ".\frontend\src\services"

Update-ServicePaths "$servicesRoot\track.service.ts" @{
    '\"/tracks' = '\"/api/v1/tracks'
    '`/tracks' = '`/api/v1/tracks'
}

Update-ServicePaths "$servicesRoot\enrollment.service.ts" @{
    '\"/enrollments' = '\"/api/v1/enrollments'
    '`/enrollments' = '`/api/v1/enrollments'
}

Update-ServicePaths "$servicesRoot\certificate.service.ts" @{
    '\"/certificates' = '\"/api/v1/certificates'
    '`/certificates' = '`/api/v1/certificates'
    '\"/graduation' = '\"/api/v1/graduation'
}

Update-ServicePaths "$servicesRoot\payment.service.ts" @{
    '\"/payments' = '\"/api/v1/payments'
    '`/payments' = '`/api/v1/payments'
}

# Audit other service modules too: api.ts uses the host-only base URL,
# so these routes also need the API prefix to reach FastAPI correctly.
Update-ServicePaths "$servicesRoot\assignment.service.ts" @{
    '\"/assignments' = '\"/api/v1/assignments'
    '`/assignments' = '`/api/v1/assignments'
}

Update-ServicePaths "$servicesRoot\quiz.service.ts" @{
    '\"/quizzes' = '\"/api/v1/quizzes'
    '`/quizzes' = '`/api/v1/quizzes'
    '\"/quiz-attempts' = '\"/api/v1/quiz-attempts'
    '`/quiz-attempts' = '`/api/v1/quiz-attempts'
}

Update-ServicePaths "$servicesRoot\finalProject.service.ts" @{
    '\"/final-projects' = '\"/api/v1/final-projects'
    '`/final-projects' = '`/api/v1/final-projects'
    '\"/tracks' = '\"/api/v1/tracks'
    '`/tracks' = '`/api/v1/tracks'
}

Write-Host "`n===== VERIFY NO ROOT-LEVEL API ROUTES REMAIN =====" -ForegroundColor Cyan

$serviceFiles = Get-ChildItem $servicesRoot -File -Filter "*.ts" |
    Where-Object { $_.Name -ne "api.ts" }

$badMatches = foreach ($file in $serviceFiles) {
    Select-String -Path $file.FullName `
        -Pattern 'api\.(get|post|patch|put|delete).*?[\"'']/(tracks|enrollments|certificates|payments|assignments|quizzes|quiz-attempts|final-projects|graduation)' `
        -AllMatches
}

if ($badMatches) {
    $badMatches | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    throw "Unprefixed backend routes remain in frontend service files."
}

Write-Host "All audited service endpoints use /api/v1 or are handled by auth.service.ts." -ForegroundColor Green
Write-Host "No git commands executed." -ForegroundColor Gray
