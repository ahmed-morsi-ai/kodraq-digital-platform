$ErrorActionPreference = "Stop"

$backend = "C:\Users\morsi\Desktop\kodraq-digital-platform\backend"

$graduation = Join-Path $backend "app\services\graduation.py"
$text = [System.IO.File]::ReadAllText($graduation, [System.Text.Encoding]::UTF8)

# Put all certificate-related imports in the normal module import section.
if ($text -notmatch '(?m)^from datetime import UTC, datetime$') {
    $text = $text -replace '(?m)^from __future__ import annotations\r?\n', "from __future__ import annotations`r`n`r`nfrom datetime import UTC, datetime`r`n"
}
if ($text -notmatch '(?m)^from uuid import uuid4$') {
    $text = $text -replace '(?m)^from datetime import UTC, datetime\r?\n', "from datetime import UTC, datetime`r`nfrom uuid import uuid4`r`n"
}
if ($text -notmatch '(?m)^from app\.models\.certificate import Certificate, GraduationResult$') {
    $text = $text -replace '(?m)^from app\.models\.track import Lesson, TrackModule\r?\n', "from app.models.track import Lesson, TrackModule`r`nfrom app.models.certificate import Certificate, GraduationResult`r`n"
}

# Remove any duplicate certificate imports that were appended near the bottom.
$text = [regex]::Replace(
    $text,
    '(?ms)\r?\nfrom datetime import datetime, timezone\r?\nfrom uuid import uuid4\r?\n\r?\nfrom sqlalchemy import select\r?\nfrom sqlalchemy\.orm import Session\r?\n\r?\nfrom app\.models\.certificate import Certificate, GraduationResult\r?\n?',
    "`r`n"
)

# Remove standalone duplicate imports anywhere except the top-level intended section.
$lines = $text -split "\r?\n"
$seenDate = $false
$seenUuid = $false
$seenCert = $false
$out = New-Object System.Collections.Generic.List[string]

foreach ($line in $lines) {
    if ($line -eq "from datetime import UTC, datetime") {
        if ($seenDate) { continue }
        $seenDate = $true
    }
    if ($line -eq "from uuid import uuid4") {
        if ($seenUuid) { continue }
        $seenUuid = $true
    }
    if ($line -eq "from app.models.certificate import Certificate, GraduationResult") {
        if ($seenCert) { continue }
        $seenCert = $true
    }
    $out.Add($line)
}

$text = ($out -join "`r`n").TrimEnd() + "`r`n"
[System.IO.File]::WriteAllText($graduation, $text, [System.Text.UTF8Encoding]::new($false))

# Make the certificate model imports explicit re-exports in models/__init__.py.
# This satisfies Ruff F401 while preserving the requested registration.
$modelsInit = Join-Path $backend "app\models\__init__.py"
$m = [System.IO.File]::ReadAllText($modelsInit, [System.Text.Encoding]::UTF8)

$m = $m -replace 'from app\.models\.certificate import Certificate, GraduationCheck, GraduationResult, GraduationRule', @'
from app.models.certificate import (
    Certificate as Certificate,
    GraduationCheck as GraduationCheck,
    GraduationResult as GraduationResult,
    GraduationRule as GraduationRule,
)
'@

# If the formatter previously split these imports into a parenthesized block,
# convert each name to an explicit re-export alias.
$m = $m -replace 'from app\.models\.certificate import \(\r?\n\s*Certificate,\r?\n\s*GraduationCheck,\r?\n\s*GraduationResult,\r?\n\s*GraduationRule,\r?\n\s*\)', @'
from app.models.certificate import (
    Certificate as Certificate,
    GraduationCheck as GraduationCheck,
    GraduationResult as GraduationResult,
    GraduationRule as GraduationRule,
)
'@

[System.IO.File]::WriteAllText($modelsInit, $m.TrimEnd() + "`r`n", [System.Text.UTF8Encoding]::new($false))

Push-Location $backend
try {
    python -m ruff check app\api\v1\api.py app\api\v1\certificates.py app\models\__init__.py app\models\certificate.py app\services\graduation.py tests\unit\test_graduation.py --fix
    python -m ruff format app\api\v1\api.py app\api\v1\certificates.py app\models\__init__.py app\models\certificate.py app\services\graduation.py tests\unit\test_graduation.py
}
finally {
    Pop-Location
}

Write-Host "TASK-5.5.1 final Ruff/import repair completed."
