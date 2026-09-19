"""Operational health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.schemas import ResponseEnvelope, ResponseMeta
from app.infrastructure.health import HealthPayload, HealthService, get_health_service

router = APIRouter(prefix="/health", tags=["health"])


def _envelope(request: Request, payload: HealthPayload) -> ResponseEnvelope[HealthPayload]:
    return ResponseEnvelope(
        data=payload,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/live", response_model=ResponseEnvelope[HealthPayload])
async def liveness(request: Request) -> ResponseEnvelope[HealthPayload]:
    """Report whether the API process can serve requests."""

    return _envelope(request, HealthPayload(status="healthy", checks={}))


@router.get(
    "/ready",
    response_model=ResponseEnvelope[HealthPayload],
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Dependency unavailable"}},
)
async def readiness(
    request: Request,
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> ResponseEnvelope[HealthPayload] | JSONResponse:
    """Report whether PostgreSQL and Redis are available."""

    payload = await health_service.check()
    response = _envelope(request, payload)
    if payload.status == "healthy":
        return response

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(mode="json"),
    )
