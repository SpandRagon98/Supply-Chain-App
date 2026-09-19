"""Organization isolation tests for persistence and services."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import TenantIsolationError
from app.domain.enums import RoleKey
from app.domain.models import Supplier
from app.domain.tenant import TenantContext
from app.repositories.suppliers import SupplierRepository
from app.services.suppliers import SupplierService


def _session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


def test_scoped_statement_always_contains_organization_predicate() -> None:
    organization_id = uuid4()
    repository = SupplierRepository(
        _session(),
        TenantContext(organization_id=organization_id, user_id=uuid4()),
    )

    compiled = str(
        repository.scoped_select().compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "suppliers.organization_id" in compiled
    assert str(organization_id) in compiled


async def test_repository_never_returns_cross_tenant_entity() -> None:
    session = _session()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    repository = SupplierRepository(
        session,
        TenantContext(organization_id=uuid4(), user_id=uuid4()),
    )

    assert await repository.get(uuid4()) is None
    statement = session.execute.await_args.args[0]
    assert "organization_id" in str(statement)


async def test_repository_rejects_cross_tenant_insert() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=uuid4())
    repository = SupplierRepository(_session(), tenant)
    foreign_supplier = Supplier(
        organization_id=uuid4(),
        code="FOREIGN",
        name="Foreign Supplier",
        country_code="US",
    )

    with pytest.raises(TenantIsolationError) as error:
        await repository.add(foreign_supplier)

    assert error.value.code == "tenant_isolation_violation"


async def test_repository_rejects_cross_tenant_delete() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=uuid4())
    session = _session()
    repository = SupplierRepository(session, tenant)
    foreign_supplier = Supplier(
        organization_id=uuid4(),
        code="FOREIGN",
        name="Foreign Supplier",
        country_code="US",
    )

    with pytest.raises(TenantIsolationError):
        await repository.delete(foreign_supplier)

    session.delete.assert_not_awaited()


async def test_supplier_service_stamps_active_organization() -> None:
    tenant = TenantContext(
        organization_id=uuid4(),
        user_id=uuid4(),
        roles=frozenset({RoleKey.ADMIN}),
    )
    session = _session()
    repository = SupplierRepository(session, tenant)
    service = SupplierService(repository, tenant)

    supplier = await service.create(
        code="SUP-001",
        name="Nova Components",
        country_code="IN",
    )

    assert supplier.organization_id == tenant.organization_id
    assert tenant.has_role(RoleKey.ADMIN)
    session.add.assert_called_once_with(supplier)
    session.flush.assert_awaited_once()


def test_service_rejects_repository_from_another_tenant() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=uuid4())
    other_tenant = TenantContext(organization_id=uuid4(), user_id=uuid4())
    repository = SupplierRepository(_session(), other_tenant)

    with pytest.raises(ValueError, match="tenant contexts must match"):
        SupplierService(repository, tenant)
