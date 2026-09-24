Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\morsi\Desktop\kodraq-digital-platform"
$BackendRoot = Join-Path $RepoRoot "backend"

if (-not (Test-Path $BackendRoot)) {
    throw "Backend checkout not found: $BackendRoot"
}

Set-Location $BackendRoot

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $parent = Split-Path $Path -Parent
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    [System.IO.File]::WriteAllText(
        $Path,
        $Content.TrimStart(),
        [System.Text.UTF8Encoding]::new($false)
    )
}

# ------------------------------------------------------------
# Audit: TASK-5.5.1 base head + required integration anchors.
# ------------------------------------------------------------
$headOutput = python -m alembic heads 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Alembic heads failed.`n$headOutput"
}
if (-not ($headOutput -match "e8b1c4d7a2f6")) {
    throw "Expected TASK-5.4 Alembic head e8b1c4d7a2f6 was not found. Refusing to apply TASK-5.5.1."
}

$apiDepsPath = Join-Path $BackendRoot "app\api\deps.py"
$apiPath = Join-Path $BackendRoot "app\api\v1\api.py"
$modelsInitPath = Join-Path $BackendRoot "app\models\__init__.py"

foreach ($requiredPath in @($apiDepsPath, $apiPath, $modelsInitPath)) {
    if (-not (Test-Path $requiredPath)) {
        throw "Required architecture file missing: $requiredPath"
    }
}

$depsText = Get-Content $apiDepsPath -Raw

$studentDependencyCandidates = @(
    "get_current_active_user",
    "get_current_user"
)

$staffDependencyCandidates = @(
    "get_current_active_assignment_manager"
)

$StudentDependency = $null
foreach ($candidate in $studentDependencyCandidates) {
    if ($depsText -match "(?m)^def\s+$candidate\(") {
        $StudentDependency = $candidate
        break
    }
}

if (-not $StudentDependency) {
    throw "Could not locate a current-user dependency in app/api/deps.py."
}

$StaffDependency = $null
foreach ($candidate in $staffDependencyCandidates) {
    if ($depsText -match "(?m)^def\s+$candidate\(") {
        $StaffDependency = $candidate
        break
    }
}

# ------------------------------------------------------------
# app/models/certificate.py
# Graduation rules/checks/results + certificate entity.
# ------------------------------------------------------------
$certificateModel = @'
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class GraduationRule(Base, TimestampMixin):
    __tablename__ = "graduation_rules"
    __table_args__ = (
        UniqueConstraint(
            "track_id",
            "code",
            name="uq_graduation_rules_track_code",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(64), nullable=False)
    threshold = Column(Integer, nullable=True)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    ordering = Column(Integer, default=0, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    track = relationship("Track")
    checks = relationship(
        "GraduationCheck",
        back_populates="rule",
        cascade="all, delete-orphan",
    )


class GraduationResult(Base, TimestampMixin):
    __tablename__ = "graduation_results"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "track_id",
            name="uq_graduation_results_student_track",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_score = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    eligible = Column(Boolean, nullable=False, default=False)
    evaluated_at = Column(String(64), nullable=True)

    student = relationship("User")
    track = relationship("Track")
    checks = relationship(
        "GraduationCheck",
        back_populates="result",
        cascade="all, delete-orphan",
        order_by="GraduationCheck.id",
    )
    certificate = relationship(
        "Certificate",
        back_populates="graduation_result",
        uselist=False,
    )


class GraduationCheck(Base, TimestampMixin):
    __tablename__ = "graduation_checks"
    __table_args__ = (
        UniqueConstraint(
            "result_id",
            "rule_id",
            name="uq_graduation_checks_result_rule",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(
        Integer,
        ForeignKey("graduation_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(
        Integer,
        ForeignKey("graduation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    passed = Column(Boolean, nullable=False, default=False)
    score = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)

    result = relationship("GraduationResult", back_populates="checks")
    rule = relationship("GraduationRule", back_populates="checks")


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificates"
    __table_args__ = (
        UniqueConstraint(
            "graduation_result_id",
            name="uq_certificates_graduation_result",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    graduation_result_id = Column(
        Integer,
        ForeignKey("graduation_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    certificate_number = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    final_score = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="ISSUED")
    file_url = Column(Text, nullable=True)

    student = relationship("User")
    track = relationship("Track")
    graduation_result = relationship(
        "GraduationResult",
        back_populates="certificate",
    )
'@
Write-Utf8NoBom (Join-Path $BackendRoot "app\models\certificate.py") $certificateModel

# Register models for SQLAlchemy metadata discovery.
$modelsInit = Get-Content $modelsInitPath -Raw
if ($modelsInit -notmatch "from app\.models\.certificate import") {
    Add-Content -Path $modelsInitPath -Value "`r`nfrom app.models.certificate import Certificate, GraduationCheck, GraduationResult, GraduationRule"
}

# ------------------------------------------------------------
# app/services/graduation.py
# TASK-5.5.1 service boundary: certificate issuance only.
# Eligibility/gate calculation remains TASK-5.5.2/5.5.3.
# ------------------------------------------------------------
$graduationService = @'
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, GraduationResult


def generate_certificate_number() -> str:
    return f"KODRAQ-{datetime.now(timezone.utc):%Y}-{uuid4().hex[:12].upper()}"


def build_certificate(
    graduation_result: GraduationResult,
    *,
    certificate_number: str | None = None,
    file_url: str | None = None,
) -> Certificate:
    if graduation_result.status != "GRADUATED":
        raise ValueError("Certificate can only be issued for a GRADUATED result.")

    if not graduation_result.student_id or not graduation_result.track_id:
        raise ValueError("Graduation result must identify a student and track.")

    return Certificate(
        student_id=graduation_result.student_id,
        track_id=graduation_result.track_id,
        graduation_result_id=graduation_result.id,
        certificate_number=certificate_number or generate_certificate_number(),
        final_score=graduation_result.overall_score,
        status="ISSUED",
        file_url=file_url,
    )


def issue_certificate(
    db: Session,
    *,
    graduation_result_id: int,
    certificate_number: str | None = None,
    file_url: str | None = None,
) -> Certificate:
    result = db.scalar(
        select(GraduationResult).where(
            GraduationResult.id == graduation_result_id
        )
    )
    if result is None:
        raise ValueError("Graduation result not found.")

    existing = db.scalar(
        select(Certificate).where(
            Certificate.graduation_result_id == graduation_result_id
        )
    )
    if existing is not None:
        return existing

    certificate = build_certificate(
        result,
        certificate_number=certificate_number,
        file_url=file_url,
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


def list_student_certificates(
    db: Session,
    *,
    student_id: int,
) -> list[Certificate]:
    return list(
        db.scalars(
            select(Certificate)
            .where(Certificate.student_id == student_id)
            .order_by(Certificate.id.desc())
        ).all()
    )


def get_certificate(
    db: Session,
    *,
    certificate_id: int,
) -> Certificate | None:
    return db.scalar(
        select(Certificate).where(Certificate.id == certificate_id)
    )
'@
Write-Utf8NoBom (Join-Path $BackendRoot "app\services\graduation.py") $graduationService

# ------------------------------------------------------------
# app/api/v1/certificates.py
# ------------------------------------------------------------
$studentDepBlock = @"
CurrentUserDep = Annotated[
    UserModel,
    Depends($StudentDependency),
]
"@

$staffAccessBlock = if ($StaffDependency) {
@"
CurrentStaffDep = Annotated[
    UserModel,
    Depends($StaffDependency),
]
"@
} else {
@"
CurrentStaffDep = CurrentUserDep
"@
}

$certificateApi = @"
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import SessionDep, $StudentDependency$(if ($StaffDependency) { ", $StaffDependency" } else { "" })
from app.models.certificate import Certificate
from app.models.user import User as UserModel
from app.services.graduation import (
    get_certificate,
    issue_certificate,
    list_student_certificates,
)

router = APIRouter(prefix="/certificates", tags=["certificates"])

$studentDepBlock
$staffAccessBlock

class CertificateIssueRequest(BaseModel):
    file_url: str | None = None


def _is_admin_or_superuser(user: UserModel) -> bool:
    if user.is_superuser:
        return True
    role_name = user.role_rel.name.casefold() if user.role_rel else ""
    return role_name in {"admin", "instructor"}


def _serialize(certificate: Certificate) -> dict:
    return {
        "id": certificate.id,
        "student_id": certificate.student_id,
        "track_id": certificate.track_id,
        "graduation_result_id": certificate.graduation_result_id,
        "certificate_number": certificate.certificate_number,
        "final_score": certificate.final_score,
        "status": certificate.status,
        "file_url": certificate.file_url,
        "created_at": certificate.created_at,
        "updated_at": certificate.updated_at,
    }


@router.get("/me")
def read_my_certificates(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[dict]:
    return [
        _serialize(certificate)
        for certificate in list_student_certificates(
            session,
            student_id=current_user.id,
        )
    ]


@router.get("/{certificate_id}")
def read_certificate(
    certificate_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> dict:
    certificate = get_certificate(
        session,
        certificate_id=certificate_id,
    )
    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found.",
        )

    if certificate.student_id != current_user.id and not _is_admin_or_superuser(
        current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to view this certificate.",
        )

    return _serialize(certificate)


@router.post(
    "/graduation-results/{graduation_result_id}/issue",
    status_code=status.HTTP_201_CREATED,
)
def issue_graduation_certificate(
    graduation_result_id: int,
    payload: CertificateIssueRequest,
    session: SessionDep,
    current_user: CurrentStaffDep,
) -> dict:
    if not _is_admin_or_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or instructor users can issue certificates.",
        )

    try:
        certificate = issue_certificate(
            session,
            graduation_result_id=graduation_result_id,
            file_url=payload.file_url,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _serialize(certificate)
"@
Write-Utf8NoBom (Join-Path $BackendRoot "app\api\v1\certificates.py") $certificateApi

# ------------------------------------------------------------
# Router registration.
# The generated router owns its /certificates prefix, so the
# aggregation layer registers it without another prefix.
# ------------------------------------------------------------
$apiText = Get-Content $apiPath -Raw

if ($apiText -notmatch "from app\.api\.v1 import certificates") {
    $apiText = "from app.api.v1 import certificates`r`n" + $apiText
}

if ($apiText -notmatch "api_router\.include_router\(certificates\.router\)") {
    $matches = [regex]::Matches($apiText, '(?m)^api_router\.include_router\([^\r\n]+\)')
    if ($matches.Count -eq 0) {
        throw "Could not find api_router.include_router(...) anchors in app/api/v1/api.py."
    }

    $last = $matches[$matches.Count - 1]
    $insertAt = $last.Index + $last.Length
    $apiText = $apiText.Insert(
        $insertAt,
        "`r`napi_router.include_router(certificates.router)`r`n"
    )
}

[System.IO.File]::WriteAllText(
    $apiPath,
    $apiText,
    [System.Text.UTF8Encoding]::new($false)
)

# ------------------------------------------------------------
# Alembic migration. This migration is intentionally explicit:
# it must create only the TASK-5.5.1 tables and nothing discovered
# accidentally from unrelated working-tree changes.
# ------------------------------------------------------------
$migrationPath = Join-Path $BackendRoot "alembic\versions\f2a5c7d9e1b3_add_graduation_rules_and_certificates.py"

if (-not (Test-Path $migrationPath)) {
$migration = @'
"""add graduation rules and certificates

Revision ID: f2a5c7d9e1b3
Revises: e8b1c4d7a2f6
Create Date: 2026-09-24 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a5c7d9e1b3"
down_revision = "e8b1c4d7a2f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graduation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_type", sa.String(length=64), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ordering", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "track_id",
            "code",
            name="uq_graduation_rules_track_code",
        ),
    )
    op.create_index(
        "ix_graduation_rules_track_id",
        "graduation_rules",
        ["track_id"],
    )
    op.create_index(
        "ix_graduation_rules_ordering",
        "graduation_rules",
        ["ordering"],
    )

    op.create_table(
        "graduation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("evaluated_at", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "student_id",
            "track_id",
            name="uq_graduation_results_student_track",
        ),
    )
    op.create_index(
        "ix_graduation_results_student_id",
        "graduation_results",
        ["student_id"],
    )
    op.create_index(
        "ix_graduation_results_track_id",
        "graduation_results",
        ["track_id"],
    )
    op.create_index(
        "ix_graduation_results_status",
        "graduation_results",
        ["status"],
    )

    op.create_table(
        "graduation_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["graduation_results.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["graduation_rules.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "result_id",
            "rule_id",
            name="uq_graduation_checks_result_rule",
        ),
    )
    op.create_index(
        "ix_graduation_checks_result_id",
        "graduation_checks",
        ["result_id"],
    )
    op.create_index(
        "ix_graduation_checks_rule_id",
        "graduation_checks",
        ["rule_id"],
    )

    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("graduation_result_id", sa.Integer(), nullable=False),
        sa.Column("certificate_number", sa.String(length=128), nullable=False),
        sa.Column("final_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ISSUED"),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["graduation_result_id"],
            ["graduation_results.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "graduation_result_id",
            name="uq_certificates_graduation_result",
        ),
        sa.UniqueConstraint(
            "certificate_number",
            name="uq_certificates_certificate_number",
        ),
    )
    op.create_index(
        "ix_certificates_student_id",
        "certificates",
        ["student_id"],
    )
    op.create_index(
        "ix_certificates_track_id",
        "certificates",
        ["track_id"],
    )
    op.create_index(
        "ix_certificates_graduation_result_id",
        "certificates",
        ["graduation_result_id"],
    )
    op.create_index(
        "ix_certificates_certificate_number",
        "certificates",
        ["certificate_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_certificates_certificate_number",
        table_name="certificates",
    )
    op.drop_index(
        "ix_certificates_graduation_result_id",
        table_name="certificates",
    )
    op.drop_index(
        "ix_certificates_track_id",
        table_name="certificates",
    )
    op.drop_index(
        "ix_certificates_student_id",
        table_name="certificates",
    )
    op.drop_table("certificates")

    op.drop_index(
        "ix_graduation_checks_rule_id",
        table_name="graduation_checks",
    )
    op.drop_index(
        "ix_graduation_checks_result_id",
        table_name="graduation_checks",
    )
    op.drop_table("graduation_checks")

    op.drop_index(
        "ix_graduation_results_status",
        table_name="graduation_results",
    )
    op.drop_index(
        "ix_graduation_results_track_id",
        table_name="graduation_results",
    )
    op.drop_index(
        "ix_graduation_results_student_id",
        table_name="graduation_results",
    )
    op.drop_table("graduation_results")

    op.drop_index(
        "ix_graduation_rules_ordering",
        table_name="graduation_rules",
    )
    op.drop_index(
        "ix_graduation_rules_track_id",
        table_name="graduation_rules",
    )
    op.drop_table("graduation_rules")
'@
    Write-Utf8NoBom $migrationPath $migration
}

# ------------------------------------------------------------
# tests/unit/test_graduation.py
# ------------------------------------------------------------
$testPath = Join-Path $BackendRoot "tests\unit\test_graduation.py"
$tests = @'
from app.models.certificate import (
    Certificate,
    GraduationCheck,
    GraduationResult,
    GraduationRule,
)
from app.services.graduation import build_certificate, generate_certificate_number


def test_graduation_rule_contract():
    rule = GraduationRule(
        track_id=7,
        code="FINAL_PROJECT",
        name="Final Project",
        rule_type="THRESHOLD",
        threshold=75,
        is_mandatory=True,
        ordering=4,
        is_active=True,
    )

    assert rule.track_id == 7
    assert rule.is_mandatory is True
    assert rule.threshold == 75
    assert rule.ordering == 4


def test_graduation_result_and_check_relationship_contract():
    result = GraduationResult(
        student_id=11,
        track_id=7,
        overall_score=82,
        status="GRADUATED",
        eligible=True,
    )
    check = GraduationCheck(
        result=result,
        rule=GraduationRule(
            track_id=7,
            code="FINAL_PROJECT",
            name="Final Project",
            rule_type="THRESHOLD",
            threshold=75,
        ),
        passed=True,
        score=82,
    )

    assert check.result is result
    assert check.passed is True
    assert check.score == 82


def test_certificate_number_is_unique_format():
    number = generate_certificate_number()

    assert number.startswith("KODRAQ-")
    assert len(number) >= 20


def test_build_certificate_requires_graduated_result():
    result = GraduationResult(
        id=9,
        student_id=11,
        track_id=7,
        overall_score=82,
        status="GRADUATED",
        eligible=True,
    )

    certificate = build_certificate(
        result,
        certificate_number="KODRAQ-2026-TEST000001",
    )

    assert isinstance(certificate, Certificate)
    assert certificate.student_id == 11
    assert certificate.track_id == 7
    assert certificate.graduation_result_id == 9
    assert certificate.final_score == 82
    assert certificate.status == "ISSUED"


def test_build_certificate_rejects_non_graduated_result():
    result = GraduationResult(
        id=10,
        student_id=11,
        track_id=7,
        overall_score=64,
        status="NOT_GRADUATED",
        eligible=False,
    )

    try:
        build_certificate(result)
    except ValueError as exc:
        assert "GRADUATED" in str(exc)
    else:
        raise AssertionError("Non-graduated result must not produce a certificate.")
'@
Write-Utf8NoBom $testPath $tests

Write-Host ""
Write-Host "TASK-5.5.1 APPLY SCRIPT COMPLETED." -ForegroundColor Green
Write-Host "No git commit was created."
Write-Host ""
Write-Host "Next verification:"
Write-Host "  python -m pytest tests/unit/test_graduation.py -ra -q"
Write-Host "  python -m ruff check app tests"
Write-Host "  python -m alembic upgrade head"
Write-Host "  python -m alembic current"
Write-Host "  python -m pytest -ra -q"
