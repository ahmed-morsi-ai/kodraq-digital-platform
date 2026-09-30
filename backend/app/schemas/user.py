from __future__ import annotations

from typing import Literal

from pydantic import AliasPath, BaseModel, ConfigDict, Field


# Shared properties for trusted CRUD operations
class UserBase(BaseModel):
    email: str | None = None
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    role_id: int | None = None


class UserCreate(UserBase):
    email: str
    full_name: str
    password: str
    role: str = "student"


class UserRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    full_name: str
    password: str
    role: Literal["student", "client"] = "student"


# Properties to receive on User update
class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    password: str | None = None


# Properties shared by models stored in DB
class UserInDBBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    role_id: int | None = None
    role_name: str | None = Field(
        default=None,
        validation_alias=AliasPath("role_rel", "name"),
    )


# Properties to return to client
class User(UserInDBBase):
    pass


# Properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str
