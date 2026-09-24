from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import (
    SessionDep,
    get_current_active_superuser,
    get_current_active_user,
)
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.track import Track
from app.models.user import User as UserModel
from app.services.receipt_storage import delete_receipt, save_receipt

router = APIRouter()

CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]
CurrentSuperuserDep = Annotated[
    UserModel,
    Depends(get_current_active_superuser),
]


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    track_id: int
    amount: Decimal
    currency: str
    status: str
    payment_method: str
    receipt_url: str
    rejection_reason: str | None = None
    created_at: object
    updated_at: object


class PaymentVerificationRequest(BaseModel):
    status: Literal["VERIFIED", "REJECTED"]
    rejection_reason: str | None = None


@router.get("/instructions")
def payment_instructions() -> dict[str, str]:
    return {
        "vodafone_cash": "01140225360",
        "instapay": "ahmed_morsi2672@instapay",
    }


@router.post(
    "/submit",
    response_model=PaymentResponse,
    status_code=201,
)
def submit_payment(
    track_id: Annotated[int, Form()],
    payment_method: Annotated[str, Form()],
    receipt: Annotated[UploadFile, File()],
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Payment:
    track = session.get(Track, track_id)

    if not track:
        raise HTTPException(
            status_code=404,
            detail="Track not found.",
        )

    if not track.is_premium:
        raise HTTPException(
            status_code=400,
            detail="Payments can only be submitted for premium tracks.",
        )

    try:
        receipt_url = save_receipt(
            file=receipt.file,
            content_type=receipt.content_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    payment = Payment(
        user_id=current_user.id,
        track_id=track.id,
        amount=track.price,
        currency=track.currency,
        status="PENDING_VERIFICATION",
        payment_method=payment_method,
        receipt_url=receipt_url,
    )

    try:
        session.add(payment)
        session.commit()
        session.refresh(payment)
    except Exception:
        session.rollback()
        delete_receipt(receipt_url)
        raise

    return payment


@router.get(
    "/me",
    response_model=list[PaymentResponse],
)
def read_my_payments(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[Payment]:
    statement = (
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
    )
    return list(session.execute(statement).scalars().all())


@router.get(
    "",
    response_model=list[PaymentResponse],
)
def read_all_payments(
    session: SessionDep,
    current_user: CurrentSuperuserDep,
    payment_status: Annotated[
        str | None,
        Query(alias="status"),
    ] = None,
) -> list[Payment]:
    del current_user

    allowed_statuses = {
        "PENDING_VERIFICATION",
        "VERIFIED",
        "REJECTED",
    }

    if payment_status is not None and payment_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment status filter.",
        )

    statement = select(Payment).order_by(
        Payment.created_at.desc(),
        Payment.id.desc(),
    )

    if payment_status is not None:
        statement = statement.where(Payment.status == payment_status)

    return list(session.execute(statement).scalars().all())


@router.patch(
    "/{payment_id}/verify",
    response_model=PaymentResponse,
)
def verify_payment(
    payment_id: int,
    verification: PaymentVerificationRequest,
    session: SessionDep,
    current_user: CurrentSuperuserDep,
) -> Payment:
    del current_user

    payment = session.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found.",
        )

    if payment.status != "PENDING_VERIFICATION":
        raise HTTPException(
            status_code=400,
            detail="Only pending payments can be verified or rejected.",
        )

    payment.status = verification.status
    payment.rejection_reason = (
        verification.rejection_reason
        if verification.status == "REJECTED"
        else None
    )

    if verification.status == "VERIFIED":
        enrollment = session.execute(
            select(Enrollment)
            .where(
                Enrollment.user_id == payment.user_id,
                Enrollment.track_id == payment.track_id,
                Enrollment.status == "pending_payment",
            )
            .limit(1)
        ).scalar_one_or_none()

        if enrollment is not None:
            enrollment.status = "active"

    session.commit()
    session.refresh(payment)

    return payment
