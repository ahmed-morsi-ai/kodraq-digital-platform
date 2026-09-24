Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\morsi\Desktop\kodraq-digital-platform"
$BackendRoot = Join-Path $RepoRoot "backend"
$ApiPath = Join-Path $BackendRoot "app\api\v1\api.py"

if (-not (Test-Path $ApiPath)) {
    throw "Missing API aggregation module: $ApiPath"
}

$apiText = Get-Content $ApiPath -Raw

# Detect the router variable used by this repository.
$routerMatches = [regex]::Matches($apiText, '(?m)^(?<indent>\s*)(?<router>[A-Za-z_]\w*)\s*=\s*APIRouter\s*\(')
$routerName = $null
if ($routerMatches.Count -gt 0) {
    $routerName = $routerMatches[0].Groups['router'].Value
}

# Fallback: infer it from an existing include_router call.
if (-not $routerName) {
    $includeMatches = [regex]::Matches($apiText, '(?m)^(?<router>[A-Za-z_]\w*)\.include_router\s*\(')
    if ($includeMatches.Count -gt 0) {
        $routerName = $includeMatches[0].Groups['router'].Value
    }
}

if (-not $routerName) {
    throw "Could not detect the APIRouter variable in app/api/v1/api.py."
}

# Add the certificates import without breaking a future import.
if ($apiText -notmatch '(?m)^from app\.api\.v1 import certificates\s*$') {
    $futureMatches = [regex]::Matches($apiText, '(?m)^from __future__ import [^\r\n]+')
    if ($futureMatches.Count -gt 0) {
        $lastFuture = $futureMatches[$futureMatches.Count - 1]
        $insertAt = $lastFuture.Index + $lastFuture.Length
        $apiText = $apiText.Insert($insertAt, "`r`nfrom app.api.v1 import certificates`r`n")
    } else {
        $apiText = "from app.api.v1 import certificates`r`n" + $apiText
    }
}

# Register exactly once.
$registration = "$routerName.include_router(certificates.router)"
if ($apiText -notmatch '(?m)^\s*' + [regex]::Escape($registration) + '\s*$') {
    if (-not $apiText.EndsWith("`r`n")) { $apiText += "`r`n" }
    $apiText += "`r`n$registration`r`n"
}

[System.IO.File]::WriteAllText(
    $ApiPath,
    $apiText,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "TASK-5.5.1 router registration repaired using '$routerName'."
Write-Host "API file: $ApiPath"
