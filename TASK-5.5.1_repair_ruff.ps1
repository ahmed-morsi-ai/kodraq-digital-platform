$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backend = Join-Path $root "backend"

function Read-Utf8($path) {
    return [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
}

function Write-Utf8($path, $content) {
    [System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
}

# 1) Repair graduation.py: keep the original graduation engine and move
# certificate imports to the top-level import section.
$graduation = Join-Path $backend "app\services\graduation.py"
$text = Read-Utf8 $graduation

if ($text -notmatch 'from app\.models\.certificate import Certificate, GraduationResult') {
    $needle = "from app.models.track import Lesson, TrackModule"
    $replacement = @"
from app.models.track import Lesson, TrackModule
from app.models.certificate import Certificate, GraduationResult
"@
    $text = $text.Replace($needle, $replacement.TrimEnd())
}

if ($text -notmatch 'from datetime import UTC, datetime') {
    $needle = "from __future__ import annotations`n"
    $replacement = "from __future__ import annotations`n`nfrom datetime import UTC, datetime`n"
    $text = $text.Replace($needle, $replacement)
}

$text = $text.Replace("from datetime import datetime, timezone`n", "")
$text = $text.Replace("from uuid import uuid4`n`nfrom sqlalchemy import select`nfrom sqlalchemy.orm import Session`n`nfrom app.models.certificate import Certificate, GraduationResult`n", "")
$text = $text.Replace("datetime.now(timezone.utc)", "datetime.now(UTC)")
Write-Utf8 $graduation $text

# 2) Ensure certificate models are intentionally exported so Ruff does not
# treat their registration imports as unused.
$modelsInit = Join-Path $backend "app\models\__init__.py"
$modelsText = Read-Utf8 $modelsInit
$exports = @(
    '    "Certificate",',
    '    "GraduationCheck",',
    '    "GraduationResult",',
    '    "GraduationRule",'
)
foreach ($item in $exports) {
    $name = ($item -replace '[", ]','')
    if ($modelsText -notmatch [regex]::Escape($item.Trim())) {
        $modelsText = $modelsText.Replace("    `"user`",`r`n", "    `"user`",`r`n$item`r`n")
    }
}
Write-Utf8 $modelsInit $modelsText

# 3) Remove the unused Session import from certificates.py and let Ruff format it.
$certApi = Join-Path $backend "app\api\v1\certificates.py"
$certText = Read-Utf8 $certApi
$certText = $certText.Replace("from sqlalchemy.orm import Session`r`n", "")
$certText = $certText.Replace("from sqlalchemy.orm import Session`n", "")
$old = "from app.api.deps import SessionDep, get_current_active_user, get_current_active_assignment_manager"
$new = @"
from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
"@.TrimEnd()
$certText = $certText.Replace($old, $new)
Write-Utf8 $certApi $certText

# 4) Format/sort only the files touched by TASK-5.5.1.
Push-Location $backend
try {
    python -m ruff check `
        app\api\v1\api.py `
        app\api\v1\certificates.py `
        app\models\__init__.py `
        app\models\certificate.py `
        app\services\graduation.py `
        tests\unit\test_graduation.py `
        --fix

    python -m ruff format `
        app\api\v1\api.py `
        app\api\v1\certificates.py `
        app\models\__init__.py `
        app\models\certificate.py `
        app\services\graduation.py `
        tests\unit\test_graduation.py
}
finally {
    Pop-Location
}

Write-Host "TASK-5.5.1 Ruff repair completed."
