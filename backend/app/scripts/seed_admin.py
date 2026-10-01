from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.admin_identity import PLATFORM_ADMIN_EMAIL
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User

ADMIN_EMAIL = PLATFORM_ADMIN_EMAIL
ADMIN_NAME = "Ahmed Morsi"


def seed_admin(session: Session, *, password: str) -> tuple[User, bool]:
    existing_user = session.scalar(
        select(User).where(User.email == ADMIN_EMAIL)
    )
    if existing_user is not None:
        admin_role = session.scalar(select(Role).where(Role.name == "admin"))
        if admin_role is None:
            admin_role = Role(name="admin", description="Platform administrator")
            session.add(admin_role)
            session.flush()
        existing_user.role_id = admin_role.id
        existing_user.is_superuser = True
        existing_user.is_active = True
        return existing_user, False

    admin_role = session.scalar(select(Role).where(Role.name == "admin"))
    if admin_role is None:
        admin_role = Role(name="admin", description="Platform administrator")
        session.add(admin_role)
        session.flush()

    admin = User(
        email=ADMIN_EMAIL,
        full_name=ADMIN_NAME,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=True,
        role_id=admin_role.id,
    )
    session.add(admin)
    session.flush()
    return admin, True


def main() -> None:
    password = os.environ.get("SEED_ADMIN_PASSWORD")
    if not password:
        raise RuntimeError("Set SEED_ADMIN_PASSWORD before running this script")

    with SessionLocal() as session:
        try:
            admin, created = seed_admin(session, password=password)
            session.commit()
            admin_email = admin.email
            admin_active = admin.is_active
            role_name = session.scalar(
                select(Role.name).where(Role.id == admin.role_id)
            ) or "unassigned"
        except Exception:
            session.rollback()
            raise

    action = "Created" if created else "Already exists"
    print(
        f"{action} admin account {admin_email}; "
        f"role={role_name}; active={admin_active}."
    )


if __name__ == "__main__":
    main()