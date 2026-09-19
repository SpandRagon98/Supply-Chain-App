"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.control_plane import router as control_plane_router
from app.api.v1.health import router as health_router
from app.api.v1.operations import router as operations_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(operations_router)
api_router.include_router(control_plane_router)
