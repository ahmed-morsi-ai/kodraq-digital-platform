from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.admin_identity import PLATFORM_ADMIN_EMAIL
from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalar_one_or_none()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        is_designated_admin = obj_in.email.casefold() == PLATFORM_ADMIN_EMAIL
        if is_designated_admin:
            role_name = "admin"
            role = db.scalar(select(Role).where(func.lower(Role.name) == role_name))
        else:
            role_name = obj_in.role
            if role_name.casefold() == "admin" or obj_in.is_superuser:
                raise ValueError(
                    f"Only {PLATFORM_ADMIN_EMAIL} can have admin privileges"
                )
            role = (
                db.get(Role, obj_in.role_id)
                if obj_in.role_id is not None
                else db.scalar(select(Role).where(Role.name == role_name))
            )
        if role is None:
            if obj_in.role_id is not None:
                raise ValueError(f"Role {obj_in.role_id} does not exist")
            role = Role(name=role_name)
            db.add(role)
            db.flush()
        if not is_designated_admin and role.name.casefold() == "admin":
            raise ValueError(f"Only {PLATFORM_ADMIN_EMAIL} can have the admin role")

        db_obj = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=get_password_hash(obj_in.password),
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser or is_designated_admin,
            role_id=role.id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def ensure_designated_admin(self, db: Session, user_obj: User) -> bool:
        role_name = user_obj.role_rel.name.casefold() if user_obj.role_rel else ""
        if user_obj.email.casefold() == PLATFORM_ADMIN_EMAIL:
            role = db.scalar(select(Role).where(func.lower(Role.name) == "admin"))
            if role is None:
                role = Role(name="admin", description="Platform administrator")
                db.add(role)
                db.flush()
            changed = user_obj.role_id != role.id or not user_obj.is_superuser
            user_obj.role_rel = role
            user_obj.is_superuser = True
        elif user_obj.is_superuser or role_name == "admin":
            role = db.scalar(select(Role).where(func.lower(Role.name) == "student"))
            if role is None:
                role = Role(name="student", description="Standard learner")
                db.add(role)
                db.flush()
            changed = user_obj.role_id != role.id or user_obj.is_superuser
            user_obj.role_rel = role
            user_obj.is_superuser = False
        else:
            return False
        if changed:
            db.flush()
        return changed

    def update(
        self, db: Session, *, db_obj: User, obj_in: UserUpdate | dict[str, Any]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True, exclude_none=True)

        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password

        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def authenticate(
        self, db: Session, *, email: str, password: str
    ) -> User | None:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        return user.is_superuser


user = CRUDUser(User)
