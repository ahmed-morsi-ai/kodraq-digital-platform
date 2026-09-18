from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String

from app.crud.base import CRUDBase
from app.models.base import Base


# Create a lightweight dummy model and schemas for testing CRUDBase directly
class DummyModel(Base):
    __tablename__ = "dummy_models"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)


class DummyCreate(BaseModel):
    name: str


class DummyUpdate(BaseModel):
    name: str | None = None


def test_crud_base_operations(db_session):
    # Ensure dummy table exists in test DB for this test session
    DummyModel.__table__.create(bind=db_session.bind, checkfirst=True)

    crud = CRUDBase(DummyModel)

    # 1. Create
    obj_in = DummyCreate(name="Test Item")
    created = crud.create(db_session, obj_in=obj_in)
    assert created.id is not None
    assert created.name == "Test Item"

    # 2. Get by ID
    fetched = crud.get(db_session, id=created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Test Item"

    # 3. Get Multi
    items = crud.get_multi(db_session)
    assert len(items) >= 1

    # 4. Update
    update_in = DummyUpdate(name="Updated Item")
    updated = crud.update(db_session, db_obj=created, obj_in=update_in)
    assert updated.name == "Updated Item"

    # 5. Remove
    removed = crud.remove(db_session, id=created.id)
    assert removed is not None
    assert crud.get(db_session, id=created.id) is None

    # Cleanup table
    DummyModel.__table__.drop(bind=db_session.bind, checkfirst=True)
