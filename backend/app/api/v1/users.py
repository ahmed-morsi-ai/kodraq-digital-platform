from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    SessionDep,
    get_current_active_superuser,
    get_current_active_user,
)
from app.crud.crud_user import user as crud_user
from app.models.user import User as UserModel
from app.schemas.user import User, UserCreate, UserUpdate

router = APIRouter()

CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_active_user),
]

CurrentSuperuserDep = Annotated[
    UserModel,
    Depends(get_current_active_superuser),
]


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
    session: SessionDep,
    user_in: UserCreate,
) -> Any:
    """Create a new user."""
    existing_user = crud_user.get_by_email(
        session,
        email=user_in.email,
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in the system.",
        )

    return crud_user.create(
        session,
        obj_in=user_in,
    )


@router.get("/me", response_model=User)
def read_user_me(
    current_user: CurrentUserDep,
) -> UserModel:
    """Get the current active user profile."""
    return current_user


@router.put("/me", response_model=User)
def update_user_me(
    session: SessionDep,
    user_in: UserUpdate,
    current_user: CurrentUserDep,
) -> UserModel:
    """Update the current user's own profile."""
    return crud_user.update(
        session,
        db_obj=current_user,
        obj_in=user_in,
    )


@router.get("", response_model=list[User])
def read_users(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    current_user: CurrentSuperuserDep = None,
) -> list[UserModel]:
    """Retrieve users for superusers."""
    del current_user

    users = crud_user.get_multi(
        session,
        skip=skip,
        limit=limit,
    )
    return list(users)
