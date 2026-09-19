"""Tenant-safe persistence repositories."""

from app.repositories.base import TenantRepository
from app.repositories.suppliers import SupplierRepository

__all__ = ["SupplierRepository", "TenantRepository"]
