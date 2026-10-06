from sqlalchemy import CheckConstraint, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('assigned_stores', 'all_tenant_stores')",
            name="ck_role_permissions_scope",
        ),
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id"), primary_key=True
    )
    scope: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="assigned_stores",
        server_default=text("'assigned_stores'"),
    )