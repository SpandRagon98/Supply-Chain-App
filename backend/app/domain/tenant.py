"""Explicit organization and actor context for tenant-scoped operations."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import RoleKey


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Authenticated tenant boundary passed into repositories and services."""

    organization_id: UUID
    user_id: UUID | None
    roles: frozenset[RoleKey] = frozenset()

    def has_role(self, *roles: RoleKey) -> bool:
        """Return whether the actor has any requested role."""

        return bool(self.roles.intersection(roles))
