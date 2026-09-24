from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import (
    SessionDep,
    get_current_active_assignment_manager,
    get_current_active_user,
)
from app.models.certificate import Certificate
from app.models.user import User as UserModel
from app.services.graduation import (
    get_certificate,
    issue_certificate,
    list_student_certificates,
)

router = APIRouter(prefix="/certificates", tags=["certificates"])

CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]
CurrentStaffDep = Annotated[
    UserModel,
    Depends(get_current_active_assignment_manager),
]


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
