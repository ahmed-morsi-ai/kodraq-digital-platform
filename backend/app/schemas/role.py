from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# Shared properties
class RoleBase(BaseModel):
    name: str | None = None
    description: str | None = None


# Properties to receive on Role creation
class RoleCreate(RoleBase):
    name: str


# Properties to receive on Role update
class RoleUpdate(RoleBase):
    pass


# Properties shared by models stored in DB
class RoleInDBBase(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


# Properties to return to client
class Role(RoleInDBBase):
    pass
