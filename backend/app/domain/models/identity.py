"""Organization, user, and role models."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import EntityBase, TenantEntity
from app.domain.enums import RoleKey


class Organization(EntityBase):
    """Top-level tenant boundary."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    default_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    default_timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(TenantEntity):
    """Human or service identity owned by one organization."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_subject: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_service_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Role(TenantEntity):
    """Tenant role assignment target with a stable RBAC key."""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("organization_id", "key"),)

    key: Mapped[RoleKey] = mapped_column(Enum(RoleKey, native_enum=False, length=40))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserRole(TenantEntity):
    """Auditable many-to-many assignment between users and roles."""

    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "role_id"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
