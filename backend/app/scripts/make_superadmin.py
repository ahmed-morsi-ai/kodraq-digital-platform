from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.core.admin_identity import PLATFORM_ADMIN_EMAIL
from app.models.role import Role
from app.models.user import User

ADMIN_EMAIL = PLATFORM_ADMIN_EMAIL


def main() -> None:
    with SessionLocal() as session:
        with session.begin():
            user = session.scalar(
                select(User)
                .where(func.lower(User.email) == ADMIN_EMAIL)
            )
            student_role = session.scalar(
                select(Role).where(func.lower(Role.name) == "student")
            )
            if student_role is None:
                student_role = Role(name="student", description="Standard learner")
                session.add(student_role)
                session.flush()
            other_admins = list(
                session.scalars(
                    select(User)
                    .join(Role, User.role_id == Role.id)
                    .where(
                        func.lower(Role.name) == "admin",
                        func.lower(User.email) != ADMIN_EMAIL,
                    )
                )
            )
            other_superusers = list(
                session.scalars(
                    select(User).where(
                        User.is_superuser.is_(True),
                        func.lower(User.email) != ADMIN_EMAIL,
                    )
                )
            )
            for other_user in {u.id: u for u in other_admins + other_superusers}.values():
                other_user.role_id = student_role.id
                other_user.is_superuser = False

            if user is None:
                print(
                    f"No account found for {ADMIN_EMAIL}. Register this email first, then rerun the script."
                )
                return

            role = session.scalar(select(Role).where(func.lower(Role.name) == "admin"))
            if role is None:
                role = Role(name="admin", description="Platform administrator")
                session.add(role)
                session.flush()
            user.role_rel = role
            user.is_superuser = True
            user.is_active = True

    print(f"Promoted {ADMIN_EMAIL} to active admin/superuser.")


if __name__ == "__main__":
    main()