# TASK-7.1.1 — Monetization Models & Manual Paywall Logic
# Clean runner v4. No git commit/push.
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $repoRoot "backend"

if (-not (Test-Path $backendRoot)) {
    throw "Missing backend directory: $backendRoot"
}

Set-Location $repoRoot

function Read-Lf([string]$Path) {
    if (-not (Test-Path $Path)) {
        throw "Missing file: $Path"
    }
    return ([System.IO.File]::ReadAllText($Path)).Replace("`r`n", "`n").Replace("`r", "`n")
}

function Write-Lf([string]$Path, [string]$Text) {
    $normalized = $Text.Replace("`r`n", "`n").Replace("`r", "`n")
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $normalized.Replace("`n", [Environment]::NewLine), $enc)
}

function Require-Text([string]$Text, [string]$Needle, [string]$Description) {
    if (-not $Text.Contains($Needle)) {
        throw "Audit failed: '$Needle' not found in $Description"
    }
}

function Replace-Exact([string]$Text, [string]$Old, [string]$New, [string]$Label) {
    $count = ([regex]::Matches($Text, [regex]::Escape($Old))).Count
    if ($count -eq 0) {
        throw "Anchor not found: $Label"
    }
    if ($count -gt 1) {
        throw "Anchor not unique: $Label ($count matches)"
    }
    return $Text.Replace($Old, $New)
}

function Run-Step([string]$Label, [scriptblock]$Command) {
    Write-Host "`n===== $Label =====" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

# ---------------------------------------------------------------------------
# 0) Audit before write.
# ---------------------------------------------------------------------------
Write-Host "===== TASK-7.1.1 AUDIT =====" -ForegroundColor Cyan

$trackPath = Join-Path $backendRoot "app\models\track.py"
$enrollmentPath = Join-Path $backendRoot "app\models\enrollment.py"
$crudEnrollmentPath = Join-Path $backendRoot "app\crud\crud_enrollment.py"
$enrollmentApiPath = Join-Path $backendRoot "app\api\v1\enrollments.py"
$apiPath = Join-Path $backendRoot "app\api\v1\api.py"
$modelsInitPath = Join-Path $backendRoot "app\models\__init__.py"
$userModelPath = Join-Path $backendRoot "app\models\user.py"
$paymentPath = Join-Path $backendRoot "app\models\payment.py"
$paymentsApiPath = Join-Path $backendRoot "app\api\v1\payments.py"
$targetTestPath = Join-Path $backendRoot "tests\unit\test_payment_models.py"

$track = Read-Lf $trackPath
$enrollment = Read-Lf $enrollmentPath
$crudEnrollment = Read-Lf $crudEnrollmentPath
$enrollmentApi = Read-Lf $enrollmentApiPath
$api = Read-Lf $apiPath
$modelsInit = Read-Lf $modelsInitPath
$userModel = Read-Lf $userModelPath

Require-Text $track 'class Track(Base, TimestampMixin):' 'Track model'
Require-Text $enrollment 'class Enrollment(Base, TimestampMixin):' 'Enrollment model'
Require-Text $crudEnrollment 'def create_for_user(' 'enrollment CRUD'
Require-Text $enrollmentApi 'def update_enrollment(' 'enrollment API'
Require-Text $api 'enrollments.router' 'enrollment router registration'
Require-Text $modelsInit 'from app.models.track import' 'model registry'
Require-Text $userModel 'class User(Base, TimestampMixin):' 'User model'

$headBefore = (git rev-parse HEAD).Trim()
Write-Host "Git HEAD before: $headBefore"
Write-Host "Audit PASS." -ForegroundColor Green

# ---------------------------------------------------------------------------
# 1) Track pricing fields.
# ---------------------------------------------------------------------------
if (-not $track.Contains('price = Column(Numeric(12, 2)')) {
    $track = Replace-Exact `
        $track `
        'from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text' `
        'from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text' `
        'Track SQLAlchemy imports'

    $track = Replace-Exact `
        $track `
        '    ordering = Column(Integer, default=0, nullable=False)' `
        @'
    ordering = Column(Integer, default=0, nullable=False)

    # TASK-7.1.1 monetization
    price = Column(Numeric(12, 2), default=0.0, nullable=False)
    currency = Column(String(3), default="EGP", nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
'@ `
        'Track pricing fields'
}

if (-not $track.Contains('payments = relationship(')) {
    $track = Replace-Exact `
        $track `
        '    modules = relationship(' `
        @'
    payments = relationship(
        "Payment",
        back_populates="track",
        cascade="all, delete-orphan",
    )
    modules = relationship(
'@ `
        'Track Payment relationship'
}

Write-Lf $trackPath $track

# ---------------------------------------------------------------------------
# 2) Payment model.
# ---------------------------------------------------------------------------
if (Test-Path $paymentPath) {
    $existingPayment = Read-Lf $paymentPath
    if ($existingPayment.Trim()) {
        throw "app/models/payment.py already exists and is non-empty. Refusing overwrite."
    }
}

$paymentModel = @'
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING_VERIFICATION', 'VERIFIED', 'REJECTED')",
            name="ck_payments_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
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
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="EGP", nullable=False)
    status = Column(
        String(32),
        default="PENDING_VERIFICATION",
        nullable=False,
    )
    payment_method = Column(String(32), nullable=False)
    receipt_url = Column(String(1024), nullable=False)
    rejection_reason = Column(String(512), nullable=True)

    user = relationship("User", back_populates="payments")
    track = relationship("Track", back_populates="payments")
'@

Write-Lf $paymentPath $paymentModel

# ---------------------------------------------------------------------------
# 3) User relationship.
# ---------------------------------------------------------------------------
$userModel = Read-Lf $userModelPath

if (-not $userModel.Contains('from app.models.payment import Payment')) {
    $userModel = Replace-Exact `
        $userModel `
        '    from app.models.ai import AIRequestLog' `
        @'
    from app.models.ai import AIRequestLog
    from app.models.payment import Payment
'@ `
        'User Payment TYPE_CHECKING import'
}

if (-not $userModel.Contains('payments: Mapped[list[Payment]]')) {
    $userModel = Replace-Exact `
        $userModel `
        '    enrollments: Mapped[list[Enrollment]] = relationship(' `
        @'
    payments: Mapped[list[Payment]] = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    enrollments: Mapped[list[Enrollment]] = relationship(
'@ `
        'User Payment relationship'
}

Write-Lf $userModelPath $userModel

# ---------------------------------------------------------------------------
# 4) Register Payment model.
# ---------------------------------------------------------------------------
$modelsInit = Read-Lf $modelsInitPath

if (-not $modelsInit.Contains('from app.models.payment import Payment')) {
    $modelsInit = Replace-Exact `
        $modelsInit `
        'from app.models.knowledge import KnowledgeChunk, KnowledgeDocument' `
        @'
from app.models.payment import Payment
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
'@ `
        'models package Payment import'
}

if (-not $modelsInit.Contains('    "Payment",')) {
    $modelsInit = Replace-Exact `
        $modelsInit `
        '    "KnowledgeDocument",' `
        @'
    "Payment",
    "KnowledgeDocument",
'@ `
        'models package __all__'
}

Write-Lf $modelsInitPath $modelsInit

# ---------------------------------------------------------------------------
# 5) Premium enrollment creation gate.
# ---------------------------------------------------------------------------
$crudEnrollment = Read-Lf $crudEnrollmentPath

if (-not $crudEnrollment.Contains('from app.models.track import Track')) {
    $crudEnrollment = Replace-Exact `
        $crudEnrollment `
        'from app.models.enrollment import Enrollment, StudentProgress' `
        @'
from app.models.enrollment import Enrollment, StudentProgress
from app.models.track import Track
'@ `
        'CRUD Track import'
}

if (-not $crudEnrollment.Contains('enrollment_status = (')) {
    $oldCreate = @'
        db_obj = Enrollment(
            user_id=user_id,
            track_id=obj_in.track_id,
            status=obj_in.status,
        )
'@
    $newCreate = @'
        track = db.get(Track, obj_in.track_id)
        enrollment_status = (
            "pending_payment"
            if track is not None and track.is_premium
            else obj_in.status
        )

        db_obj = Enrollment(
            user_id=user_id,
            track_id=obj_in.track_id,
            status=enrollment_status,
        )
'@
    $crudEnrollment = Replace-Exact $crudEnrollment $oldCreate $newCreate 'premium enrollment creation'
}

Write-Lf $crudEnrollmentPath $crudEnrollment

# ---------------------------------------------------------------------------
# 6) Prevent premium enrollment activation without VERIFIED payment.
# ---------------------------------------------------------------------------
$enrollmentApi = Read-Lf $enrollmentApiPath

if (-not $enrollmentApi.Contains('from app.models.payment import Payment')) {
    $enrollmentApi = Replace-Exact `
        $enrollmentApi `
        'from app.models.enrollment import Enrollment' `
        @'
from app.models.enrollment import Enrollment
from app.models.payment import Payment
'@ `
        'Enrollment API Payment import'
}

if (-not $enrollmentApi.Contains('Premium enrollment cannot be activated')) {
    $needle = @'
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    updated = crud_enrollment.update(
'@
    $replacement = @'
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    if enrollment_in.status == "active":
        track = crud_track.get(session, id=enrollment.track_id)
        if track and track.is_premium:
            verified_payment = session.execute(
                select(Payment.id)
                .where(
                    Payment.user_id == enrollment.user_id,
                    Payment.track_id == enrollment.track_id,
                    Payment.status == "VERIFIED",
                )
                .limit(1)
            ).scalar_one_or_none()

            if verified_payment is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Premium enrollment cannot be activated until "
                        "a related payment is verified."
                    ),
                )

    updated = crud_enrollment.update(
'@
    $enrollmentApi = Replace-Exact $enrollmentApi $needle $replacement 'premium enrollment activation guard'
}

Write-Lf $enrollmentApiPath $enrollmentApi

# ---------------------------------------------------------------------------
# 7) Static payment instructions endpoint.
# ---------------------------------------------------------------------------
if (Test-Path $paymentsApiPath) {
    $existingPaymentsApi = Read-Lf $paymentsApiPath
    if ($existingPaymentsApi.Trim()) {
        if (-not $existingPaymentsApi.Contains('PAYMENT_INSTRUCTIONS')) {
            throw "app/api/v1/payments.py already exists and is not empty. Refusing overwrite."
        }
    }
}

$paymentsApi = @'
from fastapi import APIRouter

router = APIRouter()

PAYMENT_INSTRUCTIONS = {
    "vodafone_cash": "01140225360",
    "instapay": "ahmed_morsi2672@instapay",
}


@router.get("/instructions")
def get_payment_instructions() -> dict[str, str]:
    return PAYMENT_INSTRUCTIONS.copy()
'@

Write-Lf $paymentsApiPath $paymentsApi

# ---------------------------------------------------------------------------
# 8) Register payment router.
# ---------------------------------------------------------------------------
$api = Read-Lf $apiPath

if (-not $api.Contains('    payments,')) {
    $api = Replace-Exact `
        $api `
        '    login,' `
        @'
    login,
    payments,
'@ `
        'API router Payment import'
}

if (-not $api.Contains('payments.router')) {
    $api += @'

api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["payments"],
)
'@
}

Write-Lf $apiPath $api

# ---------------------------------------------------------------------------
# 9) Targeted tests.
# ---------------------------------------------------------------------------
if (Test-Path $targetTestPath) {
    $existingTests = Read-Lf $targetTestPath
    if ($existingTests.Trim()) {
        throw "tests/unit/test_payment_models.py already exists and is non-empty. Refusing overwrite."
    }
}

$tests = @'
from decimal import Decimal

from app.crud.crud_enrollment import enrollment as crud_enrollment
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.track import Track
from app.models.user import User
from app.schemas.enrollment import EnrollmentCreate


def _create_user(db_session, suffix: str) -> User:
    user = User(
        email=f"payment-test-{suffix}@example.com",
        hashed_password="test-hash",
        full_name="Payment Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_track(db_session, *, premium: bool, suffix: str) -> Track:
    track = Track(
        name=f"Payment Test Track {suffix}",
        slug=f"payment-test-track-{suffix}",
        description="TASK-7.1.1 test track",
        is_active=True,
        ordering=0,
        price=Decimal("1500.00"),
        currency="EGP",
        is_premium=premium,
    )
    db_session.add(track)
    db_session.flush()
    return track


def test_payment_record_creation(db_session):
    user = _create_user(db_session, "record")
    track = _create_track(db_session, premium=True, suffix="record")

    payment = Payment(
        user_id=user.id,
        track_id=track.id,
        amount=Decimal("1500.00"),
        currency="EGP",
        payment_method="INSTAPAY",
        receipt_url="/uploads/receipts/payment-test.png",
    )
    db_session.add(payment)
    db_session.flush()

    assert payment.id is not None
    assert payment.status == "PENDING_VERIFICATION"
    assert payment.amount == Decimal("1500.00")
    assert payment.currency == "EGP"
    assert payment.receipt_url.endswith("payment-test.png")


def test_premium_track_creates_blocked_enrollment(db_session):
    user = _create_user(db_session, "premium")
    track = _create_track(db_session, premium=True, suffix="premium")

    enrollment = crud_enrollment.create_for_user(
        db_session,
        user_id=user.id,
        obj_in=EnrollmentCreate(track_id=track.id, status="active"),
    )

    assert isinstance(enrollment, Enrollment)
    assert enrollment.status == "pending_payment"


def test_free_track_remains_active(db_session):
    user = _create_user(db_session, "free")
    track = _create_track(db_session, premium=False, suffix="free")

    enrollment = crud_enrollment.create_for_user(
        db_session,
        user_id=user.id,
        obj_in=EnrollmentCreate(track_id=track.id, status="active"),
    )

    assert enrollment.status == "active"


def test_payment_instructions_endpoint(client):
    response = client.get("/api/v1/payments/instructions")

    assert response.status_code == 200
    assert response.json() == {
        "vodafone_cash": "01140225360",
        "instapay": "ahmed_morsi2672@instapay",
    }
'@

Write-Lf $targetTestPath $tests

Write-Host "`n===== IMPLEMENTATION WRITE COMPLETE =====" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 10) Migration + required evidence.
# ---------------------------------------------------------------------------
Set-Location $backendRoot

Run-Step "ALEMBIC AUTOGENERATE" {
    python -m alembic revision --autogenerate -m "add track pricing and manual payments"
}

Run-Step "ALEMBIC UPGRADE HEAD" {
    python -m alembic upgrade head
}

Run-Step "TARGETED PYTEST" {
    python -m pytest tests/unit/test_payment_models.py -ra -q
}

Run-Step "FULL PYTEST REGRESSION" {
    python -m pytest -ra -q
}

Run-Step "RUFF" {
    python -m ruff check app tests
}

Set-Location $repoRoot

$headAfter = (git rev-parse HEAD).Trim()

Write-Host "`n===== TASK-7.1.1 FINAL EVIDENCE =====" -ForegroundColor Cyan
Write-Host "ALEMBIC upgrade head: PASS" -ForegroundColor Green
Write-Host "Targeted pytest: PASS" -ForegroundColor Green
Write-Host "Full pytest regression: PASS" -ForegroundColor Green
Write-Host "Ruff: PASS" -ForegroundColor Green
Write-Host "Git HEAD before: $headBefore"
Write-Host "Git HEAD after : $headAfter"

if ($headBefore -ne $headAfter) {
    throw "Git HEAD changed unexpectedly. No commit was authorized."
}

Write-Host "Git HEAD unchanged: PASS (no commit created)." -ForegroundColor Green
Write-Host "TASK-7.1.1 finished; working tree remains uncommitted." -ForegroundColor Green
