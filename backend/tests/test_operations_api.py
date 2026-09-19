"""Tenant-safe operational API helper tests."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1.operations import _incident, _limit, get_tenant_context
from app.core.config import Environment


class EmptySession:
    async def scalar(self, _statement: object) -> None:
        return None


def request_with_headers(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request({"type": "http", "headers": headers})


def test_operational_list_limits_are_bounded() -> None:
    assert _limit(-2) == 1
    assert _limit(12) == 12
    assert _limit(1000) == 100


def test_incident_serializer_keeps_stable_operational_fields() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        incident_number="INC-42",
        title="Typhoon",
        incident_type=SimpleNamespace(value="WEATHER_DISRUPTION"),
        severity=SimpleNamespace(value="HIGH"),
        confidence=Decimal(".96"),
        status=SimpleNamespace(value="ACTIVE"),
        started_at=datetime(2026, 9, 19, tzinfo=UTC),
    )
    assert _incident(row) == {
        "id": str(row.id),
        "incident_number": "INC-42",
        "title": "Typhoon",
        "incident_type": "WEATHER_DISRUPTION",
        "severity": "HIGH",
        "confidence": "0.96",
        "status": "ACTIVE",
        "started_at": "2026-09-19T00:00:00+00:00",
    }


async def test_production_tenant_context_never_uses_demo_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.v1.operations.get_settings",
        lambda: SimpleNamespace(is_production=True, environment=Environment.PRODUCTION),
    )
    with pytest.raises(HTTPException, match="Authentication") as error:
        await get_tenant_context(request_with_headers([]), EmptySession())
    assert error.value.status_code == 401
