from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# Shared properties
class UserBase(BaseModel):
    email: str | None = None
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    role_id: int | None = None


# Properties to receive on User creation
class UserCreate(UserBase):
    email: str
    full_name: str
    password: str


# Properties to receive on User update
class UserUpdate(UserBase):
    password: str | None = None


# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str


# Properties to return to client
class User(UserInDBBase):
    pass


# Properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str
