"""Readiness endpoint and dependency-check tests."""

from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.infrastructure.health import (
    DependencyCheck,
    HealthPayload,
    HealthService,
    get_health_service,
)


class StubHealthService:
    def __init__(self, payload: HealthPayload) -> None:
        self.payload = payload

    async def check(self) -> HealthPayload:
        return self.payload


def test_readiness_reports_healthy_dependencies(app: FastAPI) -> None:
    payload = HealthPayload(
        status="healthy",
        checks={
            "postgresql": DependencyCheck(status="healthy"),
            "redis": DependencyCheck(status="healthy"),
        },
    )
    app.dependency_overrides[get_health_service] = lambda: StubHealthService(payload)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["data"] == payload.model_dump(mode="json")


def test_readiness_returns_503_when_a_dependency_fails(app: FastAPI) -> None:
    payload = HealthPayload(
        status="unhealthy",
        checks={
            "postgresql": DependencyCheck(status="healthy"),
            "redis": DependencyCheck(status="unhealthy"),
        },
    )
    app.dependency_overrides[get_health_service] = lambda: StubHealthService(payload)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["data"]["status"] == "unhealthy"


class FakeConnection:
    async def execute(self, _statement: object) -> None:
        return None


class FakeConnectionContext:
    async def __aenter__(self) -> FakeConnection:
        return FakeConnection()

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeEngine:
    def connect(self) -> FakeConnectionContext:
        return FakeConnectionContext()


class FailingConnectionContext:
    async def __aenter__(self) -> FakeConnection:
        raise ConnectionError("unavailable")

    async def __aexit__(self, *_args: object) -> None:
        return None


class FailingEngine:
    def connect(self) -> FailingConnectionContext:
        return FailingConnectionContext()


class FakeRedis:
    async def ping(self) -> bool:
        return True


class FailingRedis:
    async def ping(self) -> bool:
        raise ConnectionError("unavailable")


async def test_health_service_reports_all_dependencies_healthy() -> None:
    service = HealthService(
        cast(AsyncEngine, FakeEngine()),
        cast(Redis, FakeRedis()),
    )

    result = await service.check()

    assert result.status == "healthy"
    assert all(check.status == "healthy" for check in result.checks.values())


async def test_health_service_reports_database_failure() -> None:
    service = HealthService(
        cast(AsyncEngine, FailingEngine()),
        cast(Redis, FakeRedis()),
    )

    result = await service.check()

    assert result.status == "unhealthy"
    assert result.checks["postgresql"].status == "unhealthy"


async def test_health_service_reports_redis_failure() -> None:
    service = HealthService(
        cast(AsyncEngine, FakeEngine()),
        cast(Redis, FailingRedis()),
    )

    result = await service.check()

    assert result.status == "unhealthy"
    assert result.checks["redis"].status == "unhealthy"
