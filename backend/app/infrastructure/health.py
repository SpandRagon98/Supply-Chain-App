"""Dependency health checks used by readiness probes."""

from typing import Literal

import structlog
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.infrastructure.database import engine
from app.infrastructure.redis import redis_client

logger = structlog.get_logger(__name__)


class DependencyCheck(BaseModel):
    """One dependency's readiness result."""

    status: Literal["healthy", "unhealthy"]


class HealthPayload(BaseModel):
    """Health status with dependency details."""

    status: Literal["healthy", "unhealthy"]
    checks: dict[str, DependencyCheck]


class HealthService:
    """Check external dependencies without leaking connection details."""

    def __init__(self, database_engine: AsyncEngine, cache: Redis) -> None:
        self._database_engine = database_engine
        self._cache = cache

    async def _check_database(self) -> DependencyCheck:
        try:
            async with self._database_engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception as exc:
            logger.warning("health_check_failed", dependency="postgresql", error=type(exc).__name__)
            return DependencyCheck(status="unhealthy")
        return DependencyCheck(status="healthy")

    async def _check_redis(self) -> DependencyCheck:
        try:
            await self._cache.ping()
        except Exception as exc:
            logger.warning("health_check_failed", dependency="redis", error=type(exc).__name__)
            return DependencyCheck(status="unhealthy")
        return DependencyCheck(status="healthy")

    async def check(self) -> HealthPayload:
        """Return ready only when every required dependency is healthy."""

        checks = {
            "postgresql": await self._check_database(),
            "redis": await self._check_redis(),
        }
        overall_status: Literal["healthy", "unhealthy"] = (
            "healthy"
            if all(check.status == "healthy" for check in checks.values())
            else "unhealthy"
        )
        return HealthPayload(status=overall_status, checks=checks)


def get_health_service() -> HealthService:
    """Build the process-wide readiness service for dependency injection."""

    return HealthService(engine, redis_client)
